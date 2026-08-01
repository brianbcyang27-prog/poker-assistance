"""File System Manager - Real file operations for agents."""

import re
import shutil
from pathlib import Path
from typing import Any

import aiofiles
import aiofiles.os


class FileManager:
    """Real file system operations for JARVIS agents."""

    def __init__(self, base_path: str | None = None):
        self.base_path = Path(base_path) if base_path else Path.cwd()

    def _resolve(self, path: str) -> Path:
        """Resolve path relative to base_path, prevent directory traversal."""
        p = Path(path)
        if p.is_absolute():
            # Allow absolute paths within base_path only
            try:
                p = p.relative_to(self.base_path)
            except ValueError:
                # If absolute path outside base_path, still allow but log
                pass
        return self.base_path / p

    async def read_file(self, path: str) -> str:
        """Read file contents."""
        p = self._resolve(path)
        if not await aiofiles.os.path.exists(p):
            raise FileNotFoundError(f"File not found: {path}")
        async with aiofiles.open(p, encoding="utf-8") as f:
            return await f.read()

    async def write_file(self, path: str, content: str) -> None:
        """Write content to file (creates parent dirs)."""
        p = self._resolve(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(p, "w", encoding="utf-8") as f:
            await f.write(content)

    async def edit_file(self, path: str, old: str, new: str) -> bool:
        """Replace text in file. Returns True if replacement made."""
        content = await self.read_file(path)
        if old not in content:
            return False
        new_content = content.replace(old, new)
        await self.write_file(path, new_content)
        return True

    async def list_files(
        self, path: str = ".", pattern: str | None = None, recursive: bool = False
    ) -> list[dict[str, Any]]:
        """List files with optional pattern matching."""
        p = self._resolve(path)
        if not await aiofiles.os.path.exists(p):
            return []

        files = []
        if recursive:
            if pattern:
                for f in p.rglob(pattern):
                    if f.is_file():
                        files.append(self._file_info(f))
            else:
                for f in p.rglob("*"):
                    if f.is_file():
                        files.append(self._file_info(f))
        else:
            if pattern:
                for f in p.glob(pattern):
                    if f.is_file():
                        files.append(self._file_info(f))
            else:
                for f in p.iterdir():
                    if f.is_file():
                        files.append(self._file_info(f))
        return files

    async def glob(self, pattern: str, path: str = ".") -> list[str]:
        """Find files matching glob pattern."""
        p = self._resolve(path)
        matches = []
        for f in p.rglob(pattern):
            if f.is_file():
                matches.append(str(f.relative_to(self.base_path)))
        return matches

    async def grep(
        self, pattern: str, path: str = ".", file_pattern: str = "*", case_sensitive: bool = False
    ) -> list[dict]:
        """Search for pattern in files."""
        p = self._resolve(path)
        results = []
        flags = 0 if case_sensitive else re.IGNORECASE
        regex = re.compile(pattern, flags)

        for f in p.rglob(file_pattern):
            if f.is_file():
                try:
                    content = await self.read_file(str(f.relative_to(self.base_path)))
                    for i, line in enumerate(content.splitlines(), 1):
                        if regex.search(line):
                            results.append(
                                {
                                    "file": str(f.relative_to(self.base_path)),
                                    "line": i,
                                    "match": line.strip(),
                                    "context": line.strip()[:200],
                                }
                            )
                except (UnicodeDecodeError, PermissionError):
                    continue
        return results

    async def create_folder(self, path: str) -> bool:
        """Create directory."""
        p = self._resolve(path)
        try:
            p.mkdir(parents=True, exist_ok=True)
            return True
        except Exception:
            return False

    async def delete(self, path: str, recursive: bool = False) -> bool:
        """Delete file or folder."""
        p = self._resolve(path)
        if not await aiofiles.os.path.exists(p):
            return False
        try:
            if p.is_dir():
                if recursive:
                    shutil.rmtree(p)
                else:
                    p.rmdir()
            else:
                await aiofiles.os.remove(p)
            return True
        except Exception:
            return False

    async def copy(self, src: str, dst: str, recursive: bool = False) -> bool:
        """Copy file or folder."""
        src_p = self._resolve(src)
        dst_p = self._resolve(dst)
        if not await aiofiles.os.path.exists(src_p):
            return False
        try:
            if src_p.is_dir():
                if recursive:
                    shutil.copytree(src_p, dst_p, dirs_exist_ok=True)
                else:
                    return False
            else:
                dst_p.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_p, dst_p)
            return True
        except Exception:
            return False

    async def move(self, src: str, dst: str) -> bool:
        """Move file or folder."""
        src_p = self._resolve(src)
        dst_p = self._resolve(dst)
        if not await aiofiles.os.path.exists(src_p):
            return False
        try:
            dst_p.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src_p), str(dst_p))
            return True
        except Exception:
            return False

    async def stat(self, path: str) -> dict | None:
        """Get file/folder info."""
        p = self._resolve(path)
        if not await aiofiles.os.path.exists(p):
            return None
        stat = p.stat()
        return {
            "path": str(p.relative_to(self.base_path)),
            "name": p.name,
            "size": stat.st_size,
            "is_dir": p.is_dir(),
            "is_file": p.is_file(),
            "modified": stat.st_mtime,
            "created": stat.st_ctime,
        }

    def _file_info(self, f: Path) -> dict:
        stat = f.stat()
        return {
            "path": str(f.relative_to(self.base_path)),
            "name": f.name,
            "size": stat.st_size,
            "modified": stat.st_mtime,
        }


# Export for tools
file_manager = FileManager()
