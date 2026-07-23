"""Computer Assistant Workflows — Predefined multi-step workflows.

These combine multiple tools into coherent assistant actions.
"""

import logging
from typing import Optional

log = logging.getLogger("jarvis.workflows")


class WorkflowResult:
    """Result of a workflow execution."""
    
    def __init__(self):
        self.steps: list[dict] = []
        self.success: bool = True
        self.error: Optional[str] = None
    
    def add_step(self, name: str, status: str, output: str = ""):
        self.steps.append({"name": name, "status": status, "output": output})
    
    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "steps": self.steps,
            "error": self.error,
        }


class ComputerWorkflows:
    """Predefined workflows for computer assistant tasks."""
    
    def __init__(self):
        self._workflows = {
            "scan_projects": self._scan_projects,
            "system_info": self._system_info,
            "find_files": self._find_files,
        }
    
    async def execute(self, workflow_name: str, **kwargs) -> WorkflowResult:
        """Execute a named workflow."""
        if workflow_name not in self._workflows:
            return WorkflowResult()
        
        try:
            return await self._workflows[workflow_name](**kwargs)
        except Exception as e:
            result = WorkflowResult()
            result.success = False
            result.error = str(e)
            return result
    
    async def _scan_projects(self, workspace: str = "/Users/brianyang") -> WorkflowResult:
        """Scan for projects in a workspace."""
        result = WorkflowResult()
        
        # Step 1: List directories
        result.add_step("list_dirs", "started")
        try:
            from jarvis.workers.files import FilesWorker
            worker = FilesWorker()
            dirs = await worker.list_directory(workspace)
            result.add_step("list_dirs", "completed", f"Found {len(dirs)} items")
        except Exception as e:
            result.add_step("list_dirs", "failed", str(e))
            return result
        
        # Step 2: Detect project markers
        result.add_step("detect_projects", "started")
        projects = []
        markers = ["package.json", "Cargo.toml", "pyproject.toml", "go.mod", "Makefile", ".git"]
        
        for item in dirs:
            if item.get("type") != "directory":
                continue
            name = item.get("name", "")
            path = item.get("path", "")
            
            # Check for project markers
            for marker in markers:
                try:
                    check_path = f"{path}/{marker}"
                    from jarvis.workers.files import FilesWorker
                    worker = FilesWorker()
                    exists = await worker.file_exists(check_path)
                    if exists:
                        projects.append({"name": name, "path": path, "marker": marker})
                        break
                except Exception:
                    pass
        
        result.add_step("detect_projects", "completed", f"Found {len(projects)} projects")
        
        # Step 3: Store in memory
        result.add_step("store_memory", "started")
        try:
            from jarvis.brain.memory.episodic import get_episodic_memory
            em = get_episodic_memory()
            await em.store(
                content=f"Scanned workspace {workspace} and found {len(projects)} projects: {', '.join(p['name'] for p in projects[:10])}",
                episode_type="learning",
                importance_score=60,
                metadata={"workflow": "scan_projects", "projects": projects},
            )
            result.add_step("store_memory", "completed")
        except Exception as e:
            result.add_step("store_memory", "failed", str(e))
        
        return result
    
    async def _system_info(self) -> WorkflowResult:
        """Gather system information."""
        result = WorkflowResult()
        
        # Step 1: Get disk space
        result.add_step("disk_space", "started")
        try:
            from jarvis.workers.files import FilesWorker
            worker = FilesWorker()
            info = await worker.get_disk_space()
            result.add_step("disk_space", "completed", str(info))
        except Exception as e:
            result.add_step("disk_space", "failed", str(e))
        
        # Step 2: Get running processes
        result.add_step("processes", "started")
        try:
            from jarvis.workers.system import SystemWorker
            worker = SystemWorker()
            procs = await worker.get_top_processes(limit=10)
            result.add_step("processes", "completed", f"Found {len(procs)} processes")
        except Exception as e:
            result.add_step("processes", "failed", str(e))
        
        return result
    
    async def _find_files(self, pattern: str, directory: str = "/Users/brianyang") -> WorkflowResult:
        """Find files matching a pattern."""
        result = WorkflowResult()
        
        result.add_step("search", "started")
        try:
            from jarvis.workers.files import FilesWorker
            worker = FilesWorker()
            files = await worker.find_files(pattern, directory)
            result.add_step("search", "completed", f"Found {len(files)} files")
        except Exception as e:
            result.add_step("search", "failed", str(e))
        
        return result
    
    def list_workflows(self) -> list[str]:
        """List available workflow names."""
        return list(self._workflows.keys())


# Module-level singleton
workflows = ComputerWorkflows()
