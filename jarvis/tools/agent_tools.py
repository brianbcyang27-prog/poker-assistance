"""Real file system tools for JARVIS - actual implementation for agents."""

import asyncio
import os
from pathlib import Path
from typing import Any

import aiofiles


class FileSystemTools:
    """Real file system operations that agents can use."""

    def __init__(self, workspace_root: str = None):
        self.workspace_root = Path(workspace_root or os.getcwd()).resolve()
        self.workspace_root.mkdir(parents=True, exist_ok=True)

    def _resolve_path(self, path: str) -> Path:
        """Resolve path relative to workspace root, preventing directory traversal."""
        p = Path(path)
        if not p.is_absolute():
            p = self.workspace_root / p
        try:
            p = p.resolve()
            # Security: ensure path is within workspace
            if not str(p).startswith(str(self.workspace_root)):
                raise ValueError(f"Path {path} is outside workspace")
        except Exception:
            raise ValueError(f"Invalid path: {path}")
        return p

    async def read_file(self, path: str, encoding: str = "utf-8") -> dict[str, Any]:
        """Read a file's contents."""
        try:
            p = self._resolve_path(path)
            if not p.exists():
                return {"ok": False, "error": f"File not found: {path}", "path": str(p)}
            if not p.is_file():
                return {"ok": False, "error": f"Not a file: {path}", "path": str(p)}

            async with aiofiles.open(p, encoding=encoding) as f:
                content = await f.read()

            return {
                "ok": True,
                "content": content,
                "path": str(p),
                "size": len(content),
                "lines": content.count("\n") + 1,
            }
        except Exception as e:
            return {"ok": False, "error": str(e), "path": path}

    async def write_file(self, path: str, content: str, encoding: str = "utf-8") -> dict[str, Any]:
        """Write content to a file, creating directories as needed."""
        try:
            p = self._resolve_path(path)
            p.parent.mkdir(parents=True, exist_ok=True)

            async with aiofiles.open(p, "w", encoding=encoding) as f:
                await f.write(content)

            return {
                "ok": True,
                "path": str(p),
                "size": len(content),
                "lines": content.count("\n") + 1,
            }
        except Exception as e:
            return {"ok": False, "error": str(e), "path": path}

    async def edit_file(self, path: str, old_text: str, new_text: str) -> dict[str, Any]:
        """Replace text in a file."""
        try:
            result = await self.read_file(path)
            if not result["ok"]:
                return result

            content = result["content"]
            if old_text not in content:
                return {"ok": False, "error": "Old text not found in file", "path": path}

            new_content = content.replace(old_text, new_text)
            return await self.write_file(path, new_content)
        except Exception as e:
            return {"ok": False, "error": str(e), "path": path}

    async def list_files(
        self, path: str = ".", pattern: str = "*", recursive: bool = False
    ) -> dict[str, Any]:
        """List files matching pattern."""
        try:
            p = self._resolve_path(path)
            if not p.exists():
                return {"ok": False, "error": f"Path not found: {path}", "path": str(p)}

            files = []
            if recursive:
                matches = p.rglob(pattern)
            else:
                matches = p.glob(pattern)

            for f in matches:
                try:
                    stat = f.stat()
                    files.append(
                        {
                            "path": str(f.relative_to(self.workspace_root)),
                            "absolute": str(f),
                            "name": f.name,
                            "is_file": f.is_file(),
                            "is_dir": f.is_dir(),
                            "size": stat.st_size,
                            "modified": stat.st_mtime,
                        }
                    )
                except Exception:
                    continue

            return {"ok": True, "files": files, "count": len(files)}
        except Exception as e:
            return {"ok": False, "error": str(e), "path": path}

    async def glob_files(self, pattern: str) -> dict[str, Any]:
        """Find files matching glob pattern."""
        return await self.list_files(".", pattern, recursive=True)

    async def delete_file(self, path: str) -> dict[str, Any]:
        """Delete a file or directory."""
        try:
            p = self._resolve_path(path)
            if not p.exists():
                return {"ok": False, "error": "Not found", "path": path}

            if p.is_dir():
                import shutil

                shutil.rmtree(p)
            else:
                p.unlink()

            return {"ok": True, "path": str(p)}
        except Exception as e:
            return {"ok": False, "error": str(e), "path": path}

    async def file_info(self, path: str) -> dict[str, Any]:
        """Get file metadata."""
        try:
            p = self._resolve_path(path)
            if not p.exists():
                return {"ok": False, "error": "Not found", "path": path}

            stat = p.stat()
            return {
                "ok": True,
                "path": str(p),
                "relative": str(p.relative_to(self.workspace_root)),
                "name": p.name,
                "is_file": p.is_file(),
                "is_dir": p.is_dir(),
                "size": stat.st_size,
                "modified": stat.st_mtime,
                "created": stat.st_ctime,
                "extension": p.suffix,
            }
        except Exception as e:
            return {"ok": False, "error": str(e), "path": path}


class CodeExecutionTools:
    """Safe code execution for agents."""

    def __init__(self, workspace_root: str = None):
        self.workspace_root = Path(workspace_root or os.getcwd()).resolve()

    async def run_python(
        self, code: str, timeout: int = 30, capture_output: bool = True
    ) -> dict[str, Any]:
        """Execute Python code in a subprocess."""
        try:
            # Write to temp file
            import tempfile

            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".py", delete=False, dir=self.workspace_root
            ) as f:
                f.write(code)
                temp_path = f.name

            # Run with timeout
            proc = await asyncio.create_subprocess_exec(
                "python3",
                temp_path,
                stdout=asyncio.subprocess.PIPE if capture_output else None,
                stderr=asyncio.subprocess.PIPE if capture_output else None,
                cwd=str(self.workspace_root),
            )

            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            except TimeoutError:
                proc.kill()
                await proc.communicate()
                return {"ok": False, "error": f"Timeout after {timeout}s", "timeout": True}

            return {
                "ok": proc.returncode == 0,
                "returncode": proc.returncode,
                "stdout": stdout.decode() if stdout else "",
                "stderr": stderr.decode() if stderr else "",
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}
        finally:
            try:
                os.unlink(temp_path)
            except OSError:
                pass

    async def run_command(self, command: str, timeout: int = 60, cwd: str = None) -> dict[str, Any]:
        """Run a shell command."""
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.workspace_root) if cwd is None else cwd,
            )

            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            except TimeoutError:
                proc.kill()
                await proc.communicate()
                return {"ok": False, "error": f"Timeout after {timeout}s", "timeout": True}

            return {
                "ok": proc.returncode == 0,
                "returncode": proc.returncode,
                "stdout": stdout.decode() if stdout else "",
                "stderr": stderr.decode() if stderr else "",
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}


class WebTools:
    """Web search and fetch tools."""

    def __init__(self):
        pass

    async def search_web(self, query: str, limit: int = 10) -> dict[str, Any]:
        """Search the web using DuckDuckGo."""
        try:
            import urllib.parse

            import httpx

            encoded_query = urllib.parse.quote(query)
            url = f"https://api.duckduckgo.com/?q={encoded_query}&format=json&no_html=1&skip_disambig=1"

            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url)
                data = resp.json()

            results = []
            # Get abstract
            if data.get("Abstract"):
                results.append(
                    {
                        "title": "DuckDuckGo Abstract",
                        "url": data.get("AbstractURL", ""),
                        "snippet": data["Abstract"],
                        "source": "duckduckgo",
                    }
                )

            # Get related topics
            for topic in data.get("RelatedTopics", [])[:limit]:
                if isinstance(topic, dict) and topic.get("Text"):
                    results.append(
                        {
                            "title": topic.get("Text", "")[:100],
                            "url": topic.get("FirstURL", ""),
                            "snippet": topic.get("Text", "")[:300],
                            "source": "duckduckgo",
                        }
                    )

            return {"ok": True, "query": query, "results": results[:limit]}
        except Exception as e:
            return {"ok": False, "error": str(e), "query": query}

    async def fetch_url(self, url: str) -> dict[str, Any]:
        """Fetch content from a URL."""
        try:
            import httpx
            from bs4 import BeautifulSoup

            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                resp = await client.get(url)
                resp.raise_for_status()

                content_type = resp.headers.get("content-type", "")

                if "text/html" in content_type:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    # Remove scripts and styles
                    for tag in soup(["script", "style", "noscript"]):
                        tag.decompose()
                    text = soup.get_text(separator="\n", strip=True)
                    return {"ok": True, "url": url, "content": text, "type": "html"}
                else:
                    return {"ok": True, "url": url, "content": resp.text, "type": content_type}
        except Exception as e:
            return {"ok": False, "error": str(e), "url": url}


class BrowserAutomationTools:
    """Playwright-based browser automation."""

    def __init__(self, headless: bool = True):
        self.headless = headless
        self._browser = None
        self._context = None
        self._page = None

    async def _ensure_browser(self):
        if self._browser is None:
            from playwright.async_api import async_playwright

            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(headless=self.headless)
            self._context = await self._browser.new_context()
            self._page = await self._context.new_page()

    async def navigate(self, url: str) -> dict[str, Any]:
        try:
            await self._ensure_browser()
            await self._page.goto(url, wait_until="networkidle")
            return {"ok": True, "url": self._page.url}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def click(self, selector: str) -> dict[str, Any]:
        try:
            await self._ensure_browser()
            await self._page.click(selector)
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def type_text(self, selector: str, text: str) -> dict[str, Any]:
        try:
            await self._ensure_browser()
            await self._page.fill(selector, text)
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def get_text(self, selector: str = "body") -> dict[str, Any]:
        try:
            await self._ensure_browser()
            element = await self._page.query_selector(selector)
            if element:
                text = await element.inner_text()
            else:
                text = await self._page.inner_text("body")
            return {"ok": True, "text": text}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def screenshot(self, path: str = None) -> dict[str, Any]:
        try:
            await self._ensure_browser()
            if path is None:
                import tempfile

                path = tempfile.mktemp(suffix=".png")
            await self._page.screenshot(path=path)
            return {"ok": True, "path": path}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def evaluate(self, script: str) -> dict[str, Any]:
        try:
            await self._ensure_browser()
            result = await self._page.evaluate(script)
            return {"ok": True, "result": result}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def close(self):
        if self._browser:
            await self._browser.close()
        if hasattr(self, "_playwright"):
            await self._playwright.stop()


# Unified tools registry for agents
class AgentTools:
    """Unified toolset for agents - combines all tool categories."""

    def __init__(self, workspace_root: str = None):
        self.fs = FileSystemTools(workspace_root)
        self.code = CodeExecutionTools(workspace_root)
        self.web = WebTools()
        self.browser = BrowserAutomationTools()

    async def execute(self, tool_name: str, **kwargs) -> dict[str, Any]:
        """Execute a tool by name."""
        # Map tool names to methods
        tools = {
            # File system
            "read_file": self.fs.read_file,
            "write_file": self.fs.write_file,
            "edit_file": self.fs.edit_file,
            "list_files": self.fs.list_files,
            "glob_files": self.fs.glob_files,
            "delete_file": self.fs.delete_file,
            "file_info": self.fs.file_info,
            # Code execution
            "run_python": self.code.run_python,
            "run_command": self.code.run_command,
            # Web
            "search_web": self.web.search_web,
            "fetch_url": self.web.fetch_url,
            # Browser
            "browser_navigate": self.browser.navigate,
            "browser_click": self.browser.click,
            "browser_type": self.browser.type_text,
            "browser_get_text": self.browser.get_text,
            "browser_screenshot": self.browser.screenshot,
            "browser_evaluate": self.browser.evaluate,
        }

        if tool_name not in tools:
            return {"ok": False, "error": f"Unknown tool: {tool_name}"}

        try:
            return await tools[tool_name](**kwargs)
        except Exception as e:
            return {"ok": False, "error": str(e), "tool": tool_name}

    def list_tools(self) -> list[str]:
        """List all available tool names."""
        return [
            "read_file",
            "write_file",
            "edit_file",
            "list_files",
            "glob_files",
            "delete_file",
            "file_info",
            "run_python",
            "run_command",
            "search_web",
            "fetch_url",
            "browser_navigate",
            "browser_click",
            "browser_type",
            "browser_get_text",
            "browser_screenshot",
            "browser_evaluate",
        ]

    async def close(self):
        """Clean up resources."""
        await self.browser.close()


# Export main classes
__all__ = [
    "FileSystemTools",
    "CodeExecutionTools",
    "WebTools",
    "BrowserAutomationTools",
    "AgentTools",
]
