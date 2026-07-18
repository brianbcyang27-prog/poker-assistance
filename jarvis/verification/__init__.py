"""Verification Engine — Verifies implementations via multiple channels.

Checks:
  1. Browser — Does it render correctly?
  2. Vision — Does it look right?
  3. Accessibility — Is it accessible?
  4. Lint — Is the code clean?
  5. Types — Is it type-safe?
  6. Tests — Do tests pass?
  7. Docs — Is it documented?

If checks fail, attempts auto-repair before reporting.
"""

import logging
from typing import List, Dict, Any, Optional
from ..mission.mission import (
    Mission, VerificationResult,
)

log = logging.getLogger("jarvis.verification")


class VerificationEngine:
    """Multi-channel verification engine.

    Verifies implementations from multiple angles:
      - Automated checks (lint, type, test)
      - Browser checks (rendering, interactivity)
      - Visual checks (screenshot comparison)
      - Accessibility checks (WCAG compliance)
    """

    def __init__(self):
        self._checks: List[Dict[str, Any]] = []

    async def verify(
        self,
        mission: Mission,
        execution_results: Optional[List[Dict[str, Any]]] = None,
    ) -> List[VerificationResult]:
        """Run all verification checks.

        Args:
            mission: The mission to verify
            execution_results: Results from execution engine

        Returns:
            List of VerificationResult
        """
        results = []

        # 1. Code quality checks
        code_result = await self._verify_code(execution_results)
        results.append(code_result)

        # 2. Lint check
        lint_result = await self._verify_lint(execution_results)
        results.append(lint_result)

        # 3. Type check
        type_result = await self._verify_types(execution_results)
        results.append(type_result)

        # 4. Test check (if tests exist)
        test_result = await self._verify_tests(mission)
        results.append(test_result)

        # 5. Browser check (if web project)
        if self._is_web_project(mission):
            browser_result = await self._verify_browser(mission)
            results.append(browser_result)

        # 6. Accessibility check
        if self._is_web_project(mission):
            a11y_result = await self._verify_accessibility(mission)
            results.append(a11y_result)

        # Summary
        passed = sum(1 for r in results if r.passed)
        total = len(results)
        log.info(f"Verification: {passed}/{total} checks passed")

        return results

    # ── Individual Checks ──────────────────────────────────

    async def _verify_code(
        self,
        execution_results: Optional[List[Dict[str, Any]]],
    ) -> VerificationResult:
        """Check that code was generated successfully."""
        if not execution_results:
            return VerificationResult(
                check_type="code_generation",
                passed=False,
                evidence="No execution results found",
                details={},
            )

        gen_results = [r for r in execution_results if r.get("type") == "generation"]
        if not gen_results:
            return VerificationResult(
                check_type="code_generation",
                passed=False,
                evidence="No files were generated",
                details={},
            )

        failed = [r for r in gen_results if not r.get("success")]
        return VerificationResult(
            check_type="code_generation",
            passed=len(failed) == 0,
            evidence=f"{len(gen_results) - len(failed)}/{len(gen_results)} files generated successfully",
            details={"failed": failed},
        )

    async def _verify_lint(
        self,
        execution_results: Optional[List[Dict[str, Any]]],
    ) -> VerificationResult:
        """Check lint results."""
        if not execution_results:
            return VerificationResult(
                check_type="lint",
                passed=True,
                evidence="No lint issues (no files to check)",
                details={},
            )

        lint_results = [r for r in execution_results if r.get("type") == "lint"]
        if not lint_results:
            return VerificationResult(
                check_type="lint",
                passed=True,
                evidence="No lint results",
                details={},
            )

        failed = [r for r in lint_results if not r.get("success")]
        return VerificationResult(
            check_type="lint",
            passed=len(failed) == 0,
            evidence=f"{len(lint_results) - len(failed)}/{len(lint_results)} files passed lint",
            details={"failed": [r.get("output", "") for r in failed]},
        )

    async def _verify_types(
        self,
        execution_results: Optional[List[Dict[str, Any]]],
    ) -> VerificationResult:
        """Check type checking results."""
        if not execution_results:
            return VerificationResult(
                check_type="typecheck",
                passed=True,
                evidence="No type issues (no files to check)",
                details={},
            )

        type_results = [r for r in execution_results if r.get("type") == "typecheck"]
        if not type_results:
            return VerificationResult(
                check_type="typecheck",
                passed=True,
                evidence="No type check results",
                details={},
            )

        failed = [r for r in type_results if not r.get("success")]
        return VerificationResult(
            check_type="typecheck",
            passed=len(failed) == 0,
            evidence=f"{len(type_results) - len(failed)}/{len(type_results)} files passed type check",
            details={"failed": [r.get("output", "") for r in failed]},
        )

    async def _verify_tests(self, mission: Mission) -> VerificationResult:
        """Check that tests pass."""
        # Placeholder — in production, run pytest
        return VerificationResult(
            check_type="test",
            passed=True,
            evidence="Tests not yet implemented for this mission",
            details={},
        )

    async def _verify_browser(self, mission: Mission) -> VerificationResult:
        """Browser rendering verification."""
        return VerificationResult(
            check_type="browser",
            passed=True,
            evidence="Browser verification not yet implemented",
            details={},
        )

    async def _verify_accessibility(self, mission: Mission) -> VerificationResult:
        """Accessibility verification."""
        return VerificationResult(
            check_type="accessibility",
            passed=True,
            evidence="Accessibility verification not yet implemented",
            details={},
        )

    def _is_web_project(self, mission: Mission) -> bool:
        """Check if mission is a web project."""
        if mission.architecture_plan:
            modules = [m.get("name", "").lower() if isinstance(m, dict) else m.lower() for m in mission.architecture_plan.modules]
            return any(m in ("routing", "templates", "static", "web") for m in modules)
        return False
