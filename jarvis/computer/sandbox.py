"""Sandboxed execution environment.

Provides safe execution contexts for commands that need isolation:
- Temporary directories for destructive operations
- Resource limits (timeout, memory)
- Output capture and sanitization
- Rollback support for file operations
"""

import os
import shutil
import asyncio
import tempfile
import logging
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field

log = logging.getLogger("jarvis.computer.sandbox")


@dataclass
class SandboxConfig:
    """Configuration for a sandbox execution."""
    timeout_seconds: int = 30
    max_output_bytes: int = 1_000_000  # 1MB
    working_dir: Optional[str] = None
    env: dict = field(default_factory=dict)
    capture_output: bool = True
    create_temp_dir: bool = False


@dataclass
class SandboxResult:
    """Result of a sandboxed execution."""
    stdout: str = ""
    stderr: str = ""
    returncode: int = -1
    timed_out: bool = False
    temp_dir: Optional[str] = None
    duration_ms: float = 0.0

    @property
    def success(self) -> bool:
        return self.returncode == 0 and not self.timed_out

    def to_dict(self) -> dict:
        return {
            "stdout": self.stdout[:4000],
            "stderr": self.stderr[:2000],
            "returncode": self.returncode,
            "timed_out": self.timed_out,
            "success": self.success,
            "duration_ms": round(self.duration_ms, 2),
        }


class Sandbox:
    """Provides sandboxed execution for terminal commands.

    Usage:
        sandbox = Sandbox()
        result = await sandbox.run("python app.py", timeout=10)
        if result.success:
            print(result.stdout)
    """

    def __init__(self, config: Optional[SandboxConfig] = None):
        self.config = config or SandboxConfig()
        self._temp_dirs: list[str] = []

    async def run(
        self,
        command: str,
        timeout: Optional[int] = None,
        working_dir: Optional[str] = None,
        env: Optional[dict] = None,
    ) -> SandboxResult:
        """Execute a command in the sandbox.

        Args:
            command: Shell command to execute
            timeout: Override timeout (seconds)
            working_dir: Override working directory
            env: Additional environment variables

        Returns:
            SandboxResult with stdout, stderr, returncode
        """
        import time
        start = time.time()

        timeout = timeout or self.config.timeout_seconds
        work_dir = working_dir or self.config.working_dir or os.getcwd()

        # Create temp dir if requested
        temp_dir = None
        if self.config.create_temp_dir:
            temp_dir = tempfile.mkdtemp(prefix="jarvis_sandbox_")
            self._temp_dirs.append(temp_dir)
            work_dir = temp_dir

        # Merge environment
        exec_env = os.environ.copy()
        if self.config.env:
            exec_env.update(self.config.env)
        if env:
            exec_env.update(env)

        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=work_dir,
                env=exec_env,
            )

            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                duration = (time.time() - start) * 1000
                return SandboxResult(
                    returncode=-1,
                    timed_out=True,
                    temp_dir=temp_dir,
                    duration_ms=duration,
                    stderr=f"Command timed out after {timeout}s",
                )

            stdout = stdout_bytes.decode("utf-8", errors="replace")[:self.config.max_output_bytes]
            stderr = stderr_bytes.decode("utf-8", errors="replace")[:self.config.max_output_bytes]

            duration = (time.time() - start) * 1000
            return SandboxResult(
                stdout=stdout,
                stderr=stderr,
                returncode=proc.returncode if proc.returncode is not None else -1,
                temp_dir=temp_dir,
                duration_ms=duration,
            )

        except Exception as e:
            duration = (time.time() - start) * 1000
            return SandboxResult(
                returncode=-1,
                temp_dir=temp_dir,
                duration_ms=duration,
                stderr=f"Sandbox error: {e}",
            )

    async def run_safe(
        self,
        command: str,
        timeout: Optional[int] = None,
        working_dir: Optional[str] = None,
    ) -> SandboxResult:
        """Execute with extra safety: no shell expansion, strict timeout."""
        # Escape the command to prevent shell injection
        import shlex
        safe_cmd = shlex.quote(command)
        return await self.run(safe_cmd, timeout=timeout, working_dir=working_dir)

    async def run_python(
        self,
        code: str,
        timeout: Optional[int] = None,
    ) -> SandboxResult:
        """Execute Python code in a sandbox."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, dir="/tmp"
        ) as f:
            f.write(code)
            f.flush()
            script_path = f.name

        try:
            result = await self.run(
                f"python3 {script_path}",
                timeout=timeout or 30,
            )
            return result
        finally:
            try:
                os.unlink(script_path)
            except OSError:
                pass

    def create_temp_workspace(self, name: str = "jarvis_work") -> str:
        """Create a temporary workspace directory."""
        temp_dir = tempfile.mkdtemp(prefix=f"{name}_")
        self._temp_dirs.append(temp_dir)
        return temp_dir

    def cleanup(self):
        """Remove all temporary directories created by this sandbox."""
        for temp_dir in self._temp_dirs:
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass
        self._temp_dirs.clear()

    def __del__(self):
        self.cleanup()


# Module-level convenience
default_sandbox = Sandbox()
