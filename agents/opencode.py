import subprocess
import json
from typing import Optional
from pathlib import Path

from ..config import get_config
from ..tasks.manager import Task, TaskStatus


class OpenCodeAgent:
    """OpenCode worker agent for coding tasks."""
    
    def __init__(self):
        config = get_config()
        self.command = config.opencode_command
        self.workspace = config.workspace_path
    
    def execute_task(self, task: Task) -> dict:
        """Execute a task using OpenCode."""
        prompt = self._build_prompt(task)
        
        result = self._run_opencode(prompt)
        
        return {
            "task_id": task.id,
            "success": result["returncode"] == 0,
            "output": result.get("stdout", ""),
            "error": result.get("stderr", ""),
        }
    
    def _build_prompt(self, task: Task) -> str:
        """Build a prompt for OpenCode based on the task."""
        return f"""Execute the following task:

Task: {task.name}
Description: {task.description}
Type: {task.type.value}

Please complete this task and report back with:
1. What was done
2. Any files modified
3. Any issues encountered
4. Whether the task was completed successfully"""
    
    def _run_opencode(self, prompt: str) -> dict:
        """Run OpenCode with the given prompt."""
        try:
            result = subprocess.run(
                [self.command, prompt],
                cwd=str(self.workspace),
                capture_output=True,
                text=True,
                timeout=300,
            )
            
            return {
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
        except subprocess.TimeoutExpired:
            return {
                "returncode": -1,
                "stdout": "",
                "error": "OpenCode execution timed out",
            }
        except FileNotFoundError:
            return {
                "returncode": -1,
                "stdout": "",
                "error": f"OpenCode command not found: {self.command}",
            }
        except Exception as e:
            return {
                "returncode": -1,
                "stdout": "",
                "error": str(e),
            }
    
    def read_file(self, file_path: str) -> Optional[str]:
        """Read a file using OpenCode."""
        prompt = f"Read and display the contents of: {file_path}"
        result = self._run_opencode(prompt)
        
        if result["returncode"] == 0:
            return result["stdout"]
        return None
    
    def modify_file(self, file_path: str, changes: str) -> dict:
        """Modify a file using OpenCode."""
        prompt = f"""Modify the file: {file_path}

Changes to make:
{changes}

Please make these changes and confirm they were applied."""
        
        return self._run_opencode(prompt)
    
    def run_command(self, command: str) -> dict:
        """Run a shell command using OpenCode."""
        prompt = f"Run the following command and report the output:\n{command}"
        return self._run_opencode(prompt)
    
    def search_code(self, query: str, file_pattern: str = "*.py") -> dict:
        """Search for code using OpenCode."""
        prompt = f"""Search for the following pattern:
Query: {query}
File pattern: {file_pattern}

Report all matches with file paths and line numbers."""
        
        return self._run_opencode(prompt)
    
    def create_release(
        self,
        project_path: str,
        version: str,
        release_notes: str,
    ) -> dict:
        """Create a release using OpenCode."""
        prompt = f"""Create a release for the project at {project_path}

Version: {version}
Release Notes:
{release_notes}

Please:
1. Update version numbers
2. Create git tags
3. Update CHANGELOG if it exists
4. Prepare for release"""
        
        return self._run_opencode(prompt)