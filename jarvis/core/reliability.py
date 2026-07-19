"""Centralized retry, timeout, and error handling for JARVIS.

Replaces 100+ hardcoded timeout/retry values scattered across the codebase
with a single configurable module.

Usage:
    from jarvis.core.reliability import config, retry_with_backoff, timeout_guard, safe_execute

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
"""

import asyncio
import functools
import logging
import time
from dataclasses import dataclass
from typing import Any, Callable, Coroutine, Optional, Tuple, Type

log = logging.getLogger("jarvis.reliability")


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

    # Concurrency
    max_concurrent_tasks: int = 10
    max_tool_iterations: int = 5
    event_history_size: int = 200
    max_handlers_per_event: int = 50


config = ReliabilityConfig()


class retry_with_backoff:
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
        max_retries: Optional[int] = None,
        backoff_factor: Optional[float] = None,
        exceptions: Optional[Tuple[Type[Exception], ...]] = None,
        base_delay: Optional[float] = None,
        max_delay: Optional[float] = None,
    ) -> None:
        self.max_retries = max_retries if max_retries is not None else config.max_retries
        self.backoff_factor = backoff_factor if backoff_factor is not None else config.retry_backoff_factor
        self.exceptions = exceptions or (Exception,)
        self.base_delay = base_delay if base_delay is not None else config.retry_base_delay
        self.max_delay = max_delay if max_delay is not None else config.retry_max_delay

    def __call__(self, func: Callable[..., Coroutine[Any, Any, Any]]) -> Callable[..., Coroutine[Any, Any, Any]]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception: Optional[Exception] = None
            for attempt in range(self.max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except self.exceptions as e:
                    last_exception = e
                    if attempt < self.max_retries:
                        delay = min(
                            self.base_delay * (self.backoff_factor ** attempt),
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


class timeout_guard:
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
        self._timeout_handle: Optional[asyncio.TimerHandle] = None

    async def __aenter__(self) -> "timeout_guard":
        self._start = time.monotonic()
        loop = asyncio.get_event_loop()
        current_task = asyncio.current_task()
        if current_task is not None:
            self._timeout_handle = loop.call_later(
                self.timeout, self._cancel_task, current_task
            )
        return self

    def _cancel_task(self, task: asyncio.Task) -> None:
        if not task.done():
            task.cancel()

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Any,
    ) -> None:
        if self._timeout_handle is not None:
            self._timeout_handle.cancel()
            self._timeout_handle = None
        elapsed = time.monotonic() - self._start
        if isinstance(exc_val, asyncio.CancelledError):
            raise TimeoutError(
                f"{self.operation} timed out after {elapsed:.1f}s "
                f"(limit: {self.timeout}s)"
            )
        if elapsed > self.timeout * 0.8:
            log.warning(
                f"{self.operation} took {elapsed:.1f}s (timeout: {self.timeout}s)"
            )


async def timeout_guard_wait(coro: Coroutine[Any, Any, Any], timeout: float, operation: str = "operation") -> Any:
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
    except asyncio.TimeoutError:
        elapsed = time.monotonic() - start
        raise TimeoutError(
            f"{operation} timed out after {elapsed:.1f}s (limit: {timeout}s)"
        )
    elapsed = time.monotonic() - start
    if elapsed > timeout * 0.8:
        log.warning(f"{operation} took {elapsed:.1f}s (timeout: {timeout}s)")
    return result


async def safe_execute(
    coro: Coroutine[Any, Any, Any],
    default: Any = None,
    timeout: Optional[float] = None,
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
    except asyncio.TimeoutError:
        log.error(f"safe_execute timed out after {timeout}s")
        return default
    except Exception as e:
        log.error(f"safe_execute caught error: {e}", exc_info=True)
        return default
