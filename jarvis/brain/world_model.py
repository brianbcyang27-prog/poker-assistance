"""World Model - Tracks the user's computing environment."""

import os
import time
import shutil
import socket
import subprocess
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

    def _run(self, cmd: str, timeout: int = 10) -> str:
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=timeout
            )
            return result.stdout.strip()
        except Exception:
            return ""

    def get_system_info(self) -> dict:
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

        return {
            "hostname": hostname,
            "os": os_name,
            "machine": machine,
            "python": self._run("python3 --version"),
            "node": self._run("node --version"),
            "git": self._run("git --version"),
            "disk": {
                "total_gb": disk_total_gb,
                "used_gb": disk_used_gb,
                "free_gb": disk_free_gb,
                "percent": disk_pct,
            },
        }

    def scan_git_repos(self) -> list[dict]:
        """Find git repos under /Users/brianyang up to 3 levels deep."""
        repos = []
        try:
            find_cmd = (
                f"find {self._home} -maxdepth 4 -name .git -type d "
                f"2>/dev/null"
            )
            raw = self._run(find_cmd, timeout=15)
            if not raw:
                return repos
            for git_dir in raw.splitlines():
                git_dir = git_dir.strip()
                if not git_dir:
                    continue
                repo_path = str(Path(git_dir).parent)
                repos.append(self.get_project_status(repo_path))
        except Exception:
            pass
        return repos

    def get_project_status(self, path: str) -> dict:
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
            info["branch"] = self._run(f"git -C {path} branch --show-current")
            status = self._run(f"git -C {path} status --porcelain")
            if status:
                info["dirty"] = True
                info["dirty_files"] = [
                    f.strip() for f in status.splitlines() if f.strip()
                ]
            ahead = self._run(
                f"git -C {path} rev-list --left-right --count '@{{u}}' 2>/dev/null"
            )
            if ahead:
                info["ahead_behind"] = ahead
            info["last_commit"] = self._run(
                f"git -C {path} log -1 --format=%h,%s,%ar"
            )
            info["has_remote"] = bool(
                self._run(f"git -C {path} remote get-url origin 2>/dev/null")
            )
        except Exception as e:
            info["error"] = str(e)
        return info

    def get_active_servers(self) -> list[dict]:
        """List listening TCP ports."""
        servers = []
        try:
            raw = self._run("lsof -iTCP -sTCP:LISTEN -P -n 2>/dev/null", timeout=10)
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
                # extract port from address like *:8000 or 127.0.0.1:8000
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

    def scan_environment(self) -> dict:
        """Scan the full environment. Cached for 60s."""
        if self._is_cache_valid():
            return self._cache

        self._cache = {
            "timestamp": time.time(),
            "system": self.get_system_info(),
            "projects": self.scan_git_repos(),
            "servers": self.get_active_servers(),
        }
        self._cache_ts = time.time()
        return self._cache

    def force_scan(self) -> dict:
        """Force a rescan (bypass cache)."""
        self._cache = None
        self._cache_ts = 0
        return self.scan_environment()

    def to_dict(self) -> dict:
        return self.scan_environment()


world_model = WorldModel()
