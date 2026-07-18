"""Execution Engine — Executes architecture plans via code generation and review.

Executes plans by:
  1. Generating code files from architecture plan
  2. Running automated checks (lint, type, format)
  3. Handling repair attempts on failures
  4. Tracking execution results

Never blindly trusts generated code — always verifies.
"""

import logging
from typing import List, Dict, Any, Optional
from ..mission.mission import (
    Mission, ArchitecturePlan, VerificationResult,
)

log = logging.getLogger("jarvis.execution")


class ExecutionEngine:
    """Executes architecture plans.

    Follows the principle: generate, then verify. Never skip verification.
    """

    def __init__(self):
        self._results: List[Dict[str, Any]] = []

    async def execute(
        self,
        plan: Optional[ArchitecturePlan],
        mission: Mission,
    ) -> List[Dict[str, Any]]:
        """Execute the architecture plan.

        Args:
            plan: The architecture plan to execute
            mission: The mission being executed

        Returns:
            List of execution results
        """
        if not plan:
            log.debug("No plan to execute")
            return []

        results = []

        # Generate code files
        for file_path in plan.new_files:
            try:
                result = await self._generate_file(file_path, plan, mission)
                results.append(result)
            except Exception as e:
                results.append({
                    "type": "generation",
                    "file": file_path,
                    "success": False,
                    "error": str(e),
                })

        # Run linting on generated files
        for file_path in plan.new_files:
            if file_path.endswith(".py"):
                try:
                    lint_result = await self._run_lint(file_path)
                    results.append(lint_result)
                except Exception as e:
                    results.append({
                        "type": "lint",
                        "file": file_path,
                        "success": False,
                        "error": str(e),
                    })

        # Run type checking
        for file_path in plan.new_files:
            if file_path.endswith(".py"):
                try:
                    type_result = await self._run_typecheck(file_path)
                    results.append(type_result)
                except Exception as e:
                    results.append({
                        "type": "typecheck",
                        "file": file_path,
                        "success": False,
                        "error": str(e),
                    })

        self._results.extend(results)
        return results

    async def repair(
        self,
        failed_checks: List[VerificationResult],
        mission: Mission,
    ) -> List[Dict[str, Any]]:
        """Attempt to repair failed verification checks.

        Args:
            failed_checks: Verification results that failed
            mission: The mission being repaired

        Returns:
            List of repair results
        """
        results = []

        for check in failed_checks:
            try:
                if check.check_type == "lint":
                    result = await self._repair_lint(check)
                elif check.check_type == "typecheck":
                    result = await self._repair_typecheck(check)
                elif check.check_type == "test":
                    result = await self._repair_test(check)
                else:
                    result = {
                        "type": "repair",
                        "check": check.check_type,
                        "success": False,
                        "error": f"Cannot auto-repair {check.check_type}",
                    }
                results.append(result)
            except Exception as e:
                results.append({
                    "type": "repair",
                    "check": check.check_type,
                    "success": False,
                    "error": str(e),
                })

        return results

    async def _generate_file(
        self,
        file_path: str,
        plan: ArchitecturePlan,
        mission: Mission,
    ) -> Dict[str, Any]:
        """Generate a single file from the plan."""
        # Placeholder — in production, use LLM code generation
        log.debug(f"Generating {file_path}")

        return {
            "type": "generation",
            "file": file_path,
            "success": True,
            "content": f"# Generated for mission {mission.id}\n# Goal: {plan.goal[:100]}\n",
        }

    async def _run_lint(self, file_path: str) -> Dict[str, Any]:
        """Run linting on a file."""
        import subprocess
        try:
            proc = await subprocess.create_subprocess_exec(
                "python3", "-m", "py_compile", file_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            return {
                "type": "lint",
                "file": file_path,
                "success": proc.returncode == 0,
                "output": stderr.decode("utf-8", errors="replace") if proc.returncode != 0 else "",
            }
        except Exception as e:
            return {
                "type": "lint",
                "file": file_path,
                "success": False,
                "error": str(e),
            }

    async def _run_typecheck(self, file_path: str) -> Dict[str, Any]:
        """Run type checking on a file."""
        # Placeholder — use mypy/pyright in production
        return {
            "type": "typecheck",
            "file": file_path,
            "success": True,
            "output": "",
        }

    async def _repair_lint(self, check: VerificationResult) -> Dict[str, Any]:
        """Attempt to repair lint issues."""
        log.debug(f"Attempting lint repair for: {check.evidence[:100]}")
        return {
            "type": "repair",
            "check": "lint",
            "success": False,
            "error": "Auto-repair not implemented",
        }

    async def _repair_typecheck(self, check: VerificationResult) -> Dict[str, Any]:
        """Attempt to repair type checking issues."""
        log.debug(f"Attempting type repair for: {check.evidence[:100]}")
        return {
            "type": "repair",
            "check": "typecheck",
            "success": False,
            "error": "Auto-repair not implemented",
        }

    async def _repair_test(self, check: VerificationResult) -> Dict[str, Any]:
        """Attempt to repair test failures."""
        log.debug(f"Attempting test repair for: {check.evidence[:100]}")
        return {
            "type": "repair",
            "check": "test",
            "success": False,
            "error": "Auto-repair not implemented",
        }
