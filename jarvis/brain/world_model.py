"""World Model - Tracks the user's computing environment."""

import asyncio
import os
import time
import shutil
import socket
from pathlib import Path
from typing import Optional


CACHE_TTL = 60  # seconds


class WorldModel:
    """Tracks projects, repos, devices, servers, git status, and system health."""

    def __init__(self):
        self._cache: Optional[dict] = None
        self._cache_ts: float = 0
        self._home = Path("/Users/brianyang")

    def _is_cache_valid(self) -> bool:
        return self._cache is not None and (time.time() - self._cache_ts) < CACHE_TTL

    async def _run(self, cmd: str, timeout: int = 10) -> str:
        try:
            proc = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            return stdout.decode().strip()
        except Exception:
            return ""

    async def get_system_info(self) -> dict:
        hostname = socket.gethostname()
        try:
            uname = os.uname()
            os_name = f"{uname.sysname} {uname.release}"
            machine = uname.machine
        except Exception:
            os_name = "unknown"
            machine = "unknown"

        disk = shutil.disk_usage("/")
        disk_total_gb = round(disk.total / (1024 ** 3), 1)
        disk_used_gb = round(disk.used / (1024 ** 3), 1)
        disk_free_gb = round(disk.free / (1024 ** 3), 1)
        disk_pct = round(disk.used / disk.total * 100, 1) if disk.total else 0

        python_ver, node_ver, git_ver = await asyncio.gather(
            self._run("python3 --version"),
            self._run("node --version"),
            self._run("git --version"),
        )

        return {
            "hostname": hostname,
            "os": os_name,
            "machine": machine,
            "python": python_ver,
            "node": node_ver,
            "git": git_ver,
            "disk": {
                "total_gb": disk_total_gb,
                "used_gb": disk_used_gb,
                "free_gb": disk_free_gb,
                "percent": disk_pct,
            },
        }

    async def scan_git_repos(self) -> list[dict]:
        """Find git repos under /Users/brianyang up to 4 levels deep."""
        repos = []
        try:
            find_cmd = (
                f"find {self._home} -maxdepth 4 -name .git -type d "
                f"2>/dev/null"
            )
            raw = await self._run(find_cmd, timeout=15)
            if not raw:
                return repos

            git_dirs = [d.strip() for d in raw.splitlines() if d.strip()]

            # Limit concurrent git checks to avoid overwhelming the system
            async def check_repo(git_dir: str) -> Optional[dict]:
                repo_path = str(Path(git_dir).parent)
                return await self.get_project_status(repo_path)

            # Process repos in batches of 5
            for i in range(0, len(git_dirs), 5):
                batch = git_dirs[i:i+5]
                results = await asyncio.gather(
                    *[check_repo(d) for d in batch],
                    return_exceptions=True,
                )
                for r in results:
                    if isinstance(r, dict):
                        repos.append(r)
        except Exception:
            pass
        return repos

    async def get_project_status(self, path: str) -> dict:
        """Check git status: branch, dirty files, last commit."""
        info: dict = {
            "path": path,
            "name": Path(path).name,
            "branch": "",
            "dirty": False,
            "dirty_files": [],
            "ahead_behind": "",
            "last_commit": "",
            "has_remote": False,
            "error": None,
        }
        try:
            branch, status, ahead, last_commit, remote = await asyncio.gather(
                self._run(f"git -C {path} branch --show-current"),
                self._run(f"git -C {path} status --porcelain"),
                self._run(f"git -C {path} rev-list --left-right --count '@{{u}}' 2>/dev/null"),
                self._run(f"git -C {path} log -1 --format=%h,%s,%ar"),
                self._run(f"git -C {path} remote get-url origin 2>/dev/null"),
            )
            info["branch"] = branch
            if status:
                info["dirty"] = True
                info["dirty_files"] = [f.strip() for f in status.splitlines() if f.strip()]
            if ahead:
                info["ahead_behind"] = ahead
            info["last_commit"] = last_commit
            info["has_remote"] = bool(remote)
        except Exception as e:
            info["error"] = str(e)
        return info

    async def get_active_servers(self) -> list[dict]:
        """List listening TCP ports."""
        servers = []
        try:
            raw = await self._run("lsof -iTCP -sTCP:LISTEN -P -n 2>/dev/null", timeout=10)
            if not raw:
                return servers
            lines = raw.splitlines()
            for line in lines[1:]:  # skip header
                parts = line.split()
                if len(parts) < 9:
                    continue
                name = parts[0]
                pid = parts[1]
                addr = parts[8] if len(parts) > 8 else ""
                port = addr.rsplit(":", 1)[-1] if ":" in addr else ""
                servers.append({
                    "name": name,
                    "pid": pid,
                    "address": addr,
                    "port": port,
                })
        except Exception:
            pass
        return servers

    async def scan_environment(self) -> dict:
        """Scan the full environment. Cached for 60s."""
        if self._is_cache_valid():
            return self._cache

        system, projects, servers = await asyncio.gather(
            self.get_system_info(),
            self.scan_git_repos(),
            self.get_active_servers(),
        )

        self._cache = {
            "timestamp": time.time(),
            "system": system,
            "projects": projects,
            "servers": servers,
        }
        self._cache_ts = time.time()
        return self._cache

    async def force_scan(self) -> dict:
        """Force a rescan (bypass cache)."""
        self._cache = None
        self._cache_ts = 0
        return await self.scan_environment()

    async def to_dict(self) -> dict:
        return await self.scan_environment()


world_model = WorldModel()
