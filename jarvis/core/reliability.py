"""Centralized retry, timeout, circuit-breaker, and error handling for JARVIS.

Replaces 100+ hardcoded timeout/retry values scattered across the codebase
with a single configurable module.

Usage:
    from jarvis.core.reliability import (
        config, retry_with_backoff, timeout_guard, safe_execute,
        circuit_breaker,
    )

    # Adjust at runtime
    config.llm_timeout = 90.0

    # Retry decorator
    @retry_with_backoff(max_retries=3, backoff_factor=2.0, exceptions=(ConnectionError,))
    async def fetch_data():
        ...

    # Timeout context manager
    async with timeout_guard(config.llm_timeout, "LLM call"):
        result = await llm.complete(prompt)

    # Safe execution (never raises)
    result = await safe_execute(some_coroutine(), default=None, timeout=30.0)

    # Circuit breaker
    cb = circuit_breaker("llm", failure_threshold=5, recovery_timeout=30.0)
    async with cb:
        result = await llm.complete(prompt)
"""

import asyncio
import functools
import time
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from jarvis.core.logging import get_logger

log = get_logger("jarvis.reliability")


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class ReliabilityConfig:
    """Central configuration for all retry, timeout, and concurrency settings."""

    # Timeouts
    llm_timeout: float = 60.0
    http_timeout: float = 30.0
    task_timeout: float = 300.0
    sandbox_timeout: float = 30.0
    browser_timeout: float = 30.0
    ws_timeout: float = 5.0
    worker_timeout: float = 300.0
    king_timeout: float = 600.0
    health_check_timeout: float = 10.0
    dead_client_timeout: float = 30.0

    # Retry
    max_retries: int = 3
    retry_base_delay: float = 1.0
    retry_max_delay: float = 30.0
    retry_backoff_factor: float = 2.0

    # Circuit breaker
    cb_failure_threshold: int = 5
    cb_recovery_timeout: float = 30.0
    cb_half_open_max_calls: int = 1

    # Concurrency
    max_concurrent_tasks: int = 10
    max_tool_iterations: int = 5
    event_history_size: int = 200
    max_handlers_per_event: int = 50


config = ReliabilityConfig()


class retry_with_backoff:  # noqa: N801 (decorator API — used as @retry_with_backoff(...))
    """Async decorator that retries a function with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts (default from config).
        backoff_factor: Multiplier for exponential delay (default from config).
        exceptions: Tuple of exception types to catch (default: (Exception,)).
        base_delay: Initial delay in seconds (default from config).
        max_delay: Maximum delay cap in seconds (default from config).

    Example:
        @retry_with_backoff(max_retries=3, exceptions=(ConnectionError,))
        async def fetch():
            ...
    """

    def __init__(
        self,
        max_retries: int | None = None,
        backoff_factor: float | None = None,
        exceptions: tuple[type[Exception], ...] | None = None,
        base_delay: float | None = None,
        max_delay: float | None = None,
    ) -> None:
        self.max_retries = max_retries if max_retries is not None else config.max_retries
        self.backoff_factor = (
            backoff_factor if backoff_factor is not None else config.retry_backoff_factor
        )
        self.exceptions = exceptions or (Exception,)
        self.base_delay = base_delay if base_delay is not None else config.retry_base_delay
        self.max_delay = max_delay if max_delay is not None else config.retry_max_delay

    def __call__(
        self, func: Callable[..., Coroutine[Any, Any, Any]]
    ) -> Callable[..., Coroutine[Any, Any, Any]]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception: Exception | None = None
            for attempt in range(self.max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except self.exceptions as e:
                    last_exception = e
                    if attempt < self.max_retries:
                        delay = min(
                            self.base_delay * (self.backoff_factor**attempt),
                            self.max_delay,
                        )
                        log.warning(
                            f"Attempt {attempt + 1}/{self.max_retries + 1} for "
                            f"{func.__qualname__} failed: {e}. "
                            f"Retrying in {delay:.1f}s..."
                        )
                        await asyncio.sleep(delay)
                    else:
                        log.error(
                            f"{func.__qualname__} failed after {self.max_retries + 1} attempts: {e}"
                        )
            raise last_exception  # type: ignore[misc]

        return wrapper


class timeout_guard:  # noqa: N801 (decorator API — used as @timeout_guard(...))
    """Async context manager that enforces a timeout with descriptive errors.

    Cancels the current task if the body does not complete within `timeout` seconds,
    raising TimeoutError with a descriptive message.

    Args:
        timeout: Maximum seconds to allow.
        operation: Human-readable name for the operation (for logging/error messages).

    Example:
        async with timeout_guard(30.0, "LLM call"):
            result = await llm.complete(prompt)
    """

    def __init__(self, timeout: float, operation: str = "operation") -> None:
        self.timeout = timeout
        self.operation = operation
        self._start: float = 0.0
        self._timeout_handle: asyncio.TimerHandle | None = None

    async def __aenter__(self) -> "timeout_guard":
        self._start = time.monotonic()
        loop = asyncio.get_running_loop()
        current_task = asyncio.current_task()
        if current_task is not None:
            self._timeout_handle = loop.call_later(self.timeout, self._cancel_task, current_task)
        return self

    def _cancel_task(self, task: asyncio.Task) -> None:
        if not task.done():
            task.cancel()

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        if self._timeout_handle is not None:
            self._timeout_handle.cancel()
            self._timeout_handle = None
        elapsed = time.monotonic() - self._start
        if isinstance(exc_val, asyncio.CancelledError):
            raise TimeoutError(
                f"{self.operation} timed out after {elapsed:.1f}s (limit: {self.timeout}s)"
            )
        if elapsed > self.timeout * 0.8:
            log.warning(f"{self.operation} took {elapsed:.1f}s (timeout: {self.timeout}s)")


async def timeout_guard_wait(
    coro: Coroutine[Any, Any, Any], timeout: float, operation: str = "operation"
) -> Any:
    """Run a coroutine with a timeout, raising TimeoutError on expiry.

    This is the function-call form of timeout_guard (for cases where a
    context manager is awkward).

    Args:
        coro: The coroutine to run.
        timeout: Maximum seconds to allow.
        operation: Human-readable name for the error message.

    Returns:
        The result of the coroutine.

    Raises:
        TimeoutError: If the coroutine does not complete in time.
    """
    start = time.monotonic()
    try:
        result = await asyncio.wait_for(coro, timeout=timeout)
    except TimeoutError:
        elapsed = time.monotonic() - start
        raise TimeoutError(f"{operation} timed out after {elapsed:.1f}s (limit: {timeout}s)")
    elapsed = time.monotonic() - start
    if elapsed > timeout * 0.8:
        log.warning(f"{operation} took {elapsed:.1f}s (timeout: {timeout}s)")
    return result


async def safe_execute(
    coro: Coroutine[Any, Any, Any],
    default: Any = None,
    timeout: float | None = None,
) -> Any:
    """Execute a coroutine safely, returning a default on any failure.

    Never raises — catches all exceptions, logs them, and returns `default`.

    Args:
        coro: The coroutine to run.
        default: Value to return on error (default: None).
        timeout: Optional timeout in seconds.

    Returns:
        The coroutine result, or `default` on failure.

    Example:
        result = await safe_execute(llm.complete(prompt), default="", timeout=30.0)
    """
    try:
        if timeout is not None:
            return await asyncio.wait_for(coro, timeout=timeout)
        return await coro
    except TimeoutError:
        log.error(f"safe_execute timed out after {timeout}s")
        return default
    except Exception as e:
        log.error(f"safe_execute caught error: {e}", exc_info=True)
        return default


class CircuitBreakerOpenError(Exception):
    """Raised when a circuit breaker is OPEN and rejects a call."""


class circuit_breaker:  # noqa: N801 (decorator API — used as @circuit_breaker(...) / async with)
    """Async context manager that implements the Circuit Breaker pattern.

    Three states:
        CLOSED    — normal operation, calls pass through
        OPEN      — failures exceeded threshold; calls fail fast
        HALF_OPEN — recovery timeout elapsed; one probe call allowed

    If the probe succeeds the circuit resets to CLOSED.
    If it fails the circuit returns to OPEN for another recovery_timeout.

    Usage:
        cb = circuit_breaker("llm", failure_threshold=5, recovery_timeout=30.0)
        async with cb:
            result = await llm.complete(prompt)
    """

    _registry: dict[str, "circuit_breaker"] = {}

    def __new__(
        cls,
        name: str,
        failure_threshold: int | None = None,
        recovery_timeout: float | None = None,
    ) -> "circuit_breaker":
        existing = cls._registry.get(name)
        if existing is not None:
            return existing
        instance = super().__new__(cls)
        cls._registry[name] = instance
        return instance

    def __init__(
        self,
        name: str,
        failure_threshold: int | None = None,
        recovery_timeout: float | None = None,
    ) -> None:
        # Skip re-init if already registered (__new__ returned existing instance)
        if hasattr(self, "_initialized") and self._initialized:
            return
        self.name = name
        self._failure_threshold = failure_threshold or config.cb_failure_threshold
        self._recovery_timeout = recovery_timeout or config.cb_recovery_timeout
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time = 0.0
        self._half_open_calls = 0
        self._max_half_open_calls = config.cb_half_open_max_calls
        self._total_calls = 0
        self._total_failures = 0
        self._total_rejections = 0
        self._lock = asyncio.Lock()
        self._initialized = True

    @property
    def state(self) -> str:
        return self._state.value

    @property
    def failure_count(self) -> int:
        return self._failure_count

    def stats(self) -> dict:
        return {
            "name": self.name,
            "state": self._state.value,
            "failure_count": self._failure_count,
            "failure_threshold": self._failure_threshold,
            "total_calls": self._total_calls,
            "total_failures": self._total_failures,
            "total_rejections": self._total_rejections,
        }

    async def __aenter__(self) -> "circuit_breaker":
        await self._check_state()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> bool | None:
        if exc_type is not None:
            await self._on_failure()
        else:
            await self._on_success()
        return None  # do not suppress exceptions

    async def _check_state(self) -> None:
        async with self._lock:
            if self._state == CircuitState.CLOSED:
                self._total_calls += 1
                return

            if self._state == CircuitState.OPEN:
                elapsed = time.monotonic() - self._last_failure_time
                if elapsed >= self._recovery_timeout:
                    self._state = CircuitState.HALF_OPEN
                    self._half_open_calls = 0
                    log.info("Circuit %s transitioning to HALF_OPEN for probe", self.name)
                else:
                    self._total_rejections += 1
                    remaining = self._recovery_timeout - elapsed
                    raise CircuitBreakerOpenError(
                        f"Circuit {self.name!r} is OPEN. "
                        f"Retry in {remaining:.0f}s "
                        f"(failures: {self._failure_count}/{self._failure_threshold})"
                    )

            if self._state == CircuitState.HALF_OPEN:
                if self._half_open_calls >= self._max_half_open_calls:
                    self._total_rejections += 1
                    raise CircuitBreakerOpenError(
                        f"Circuit {self.name!r} is HALF_OPEN and probe is already in flight"
                    )
                self._half_open_calls += 1
                self._total_calls += 1

    async def _on_success(self) -> None:
        async with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                log.info("Circuit %s probe succeeded, resetting to CLOSED", self.name)
                self._state = CircuitState.CLOSED
                self._failure_count = 0
                self._half_open_calls = 0
            elif self._state == CircuitState.CLOSED:
                self._failure_count = max(0, self._failure_count - 1)

    async def _on_failure(self) -> None:
        async with self._lock:
            self._total_failures += 1
            self._failure_count += 1
            self._last_failure_time = time.monotonic()

            if self._state == CircuitState.HALF_OPEN:
                log.warning("Circuit %s probe failed, returning to OPEN", self.name)
                self._state = CircuitState.OPEN
                self._half_open_calls = 0
            elif (
                self._state == CircuitState.CLOSED
                and self._failure_count >= self._failure_threshold
            ):
                log.warning(
                    "Circuit %s OPEN after %d failures",
                    self.name,
                    self._failure_count,
                )
                self._state = CircuitState.OPEN

    @classmethod
    def get(cls, name: str) -> Optional["circuit_breaker"]:
        return cls._registry.get(name)

    @classmethod
    def all_stats(cls) -> dict[str, dict]:
        return {name: cb.stats() for name, cb in cls._registry.items()}


async def with_circuit_breaker(
    name: str,
    coro: Coroutine[Any, Any, Any],
    default: Any = None,
    failure_threshold: int | None = None,
    recovery_timeout: float | None = None,
) -> Any:
    """Execute a coroutine protected by a circuit breaker.

    If the circuit is OPEN and rejects the call, returns *default* instead
    of raising CircuitBreakerOpenError.

    Usage:
        result = await with_circuit_breaker("llm", llm.complete(prompt), default="")
    """
    cb = circuit_breaker(
        name,
        failure_threshold=failure_threshold,
        recovery_timeout=recovery_timeout,
    )
    try:
        async with cb:
            return await coro
    except CircuitBreakerOpenError:
        log.warning("Circuit %s open, returning default", name)
        return default
