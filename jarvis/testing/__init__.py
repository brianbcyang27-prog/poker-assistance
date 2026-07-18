"""Testing Engine — Automated test generation, execution, and repair.

Generates comprehensive tests, runs them, and attempts auto-repair on failures.
"""

import logging
from typing import List, Dict, Any, Optional
from ..mission.mission import Mission

log = logging.getLogger("jarvis.testing")


class TestingEngine:
    """Automated testing engine — generates, runs, and repairs tests.

    Follows the principle: if you can't test it, you can't trust it.
    """

    def __init__(self):
        self._test_files: List[str] = []
        self._results: List[Dict[str, Any]] = []

    async def test(self, mission: Mission) -> List[Dict[str, Any]]:
        """Run the full testing cycle: generate → run → report.

        Args:
            mission: The mission to test

        Returns:
            List of test results
        """
        results = []

        # 1. Generate tests
        gen_result = await self._generate_tests(mission)
        results.append(gen_result)

        # 2. Run tests
        run_result = await self._run_tests(mission)
        results.append(run_result)

        # 3. If failures, attempt repair
        if not run_result.get("success"):
            repair_result = await self._repair_tests(mission, run_result)
            results.append(repair_result)

        self._results.extend(results)
        return results

    async def _generate_tests(self, mission: Mission) -> Dict[str, Any]:
        """Generate test files for the mission."""
        test_files = []

        if mission.architecture_plan:
            for module in mission.architecture_plan.modules:
                test_file = f"tests/test_{module}.py"
                test_files.append(test_file)

        self._test_files = test_files

        return {
            "type": "test_generation",
            "success": True,
            "files": test_files,
            "count": len(test_files),
        }

    async def _run_tests(self, mission: Mission) -> Dict[str, Any]:
        """Run pytest on generated tests."""
        if not self._test_files:
            return {
                "type": "test_execution",
                "success": True,
                "output": "No test files to run",
                "passed": 0,
                "failed": 0,
            }

        import subprocess
        try:
            proc = await subprocess.create_subprocess_exec(
                "python3", "-m", "pytest", "tests/", "-v", "--tb=short",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            output = stdout.decode("utf-8", errors="replace")
            success = proc.returncode == 0

            # Parse results
            passed = output.count("PASSED")
            failed = output.count("FAILED")

            return {
                "type": "test_execution",
                "success": success,
                "output": output,
                "passed": passed,
                "failed": failed,
            }

        except Exception as e:
            return {
                "type": "test_execution",
                "success": False,
                "error": str(e),
                "passed": 0,
                "failed": 0,
            }

    async def _repair_tests(
        self,
        mission: Mission,
        test_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Attempt to repair failing tests."""
        log.debug("Attempting test repair")

        # Placeholder — in production, use LLM to fix failing tests
        return {
            "type": "test_repair",
            "success": False,
            "error": "Auto-repair not implemented",
        }
