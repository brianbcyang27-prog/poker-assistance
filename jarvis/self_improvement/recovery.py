"""Auto-recovery — diagnose errors, apply fixes, and manage dependencies."""
import logging
import os
import shutil
import subprocess
import time
from typing import Any, Dict, List, Optional

from .error_memory import ErrorMemory
from .models import ErrorRecord, RecoveryPlan, RecoveryAction

logger = logging.getLogger(__name__)


class AutoRecovery:
    """Automatic error diagnosis and recovery engine."""

    known_solutions: Dict[str, Dict[str, Any]] = {
        "ModuleNotFoundError": {
            "action": RecoveryAction.FIX_DEPENDENCY.value,
            "description": "Install the missing Python package",
            "confidence": 0.9,
        },
        "ImportError": {
            "action": RecoveryAction.FIX_DEPENDENCY.value,
            "description": "Check and install the required package",
            "confidence": 0.85,
        },
        "FileNotFoundError": {
            "action": RecoveryAction.RETRY.value,
            "description": "Check file path and create directory if needed",
            "confidence": 0.8,
        },
        "PermissionError": {
            "action": RecoveryAction.ASK_USER.value,
            "description": "Requires elevated permissions",
            "confidence": 0.7,
        },
        "ConnectionError": {
            "action": RecoveryAction.RETRY.value,
            "description": "Network issue — retry after delay",
            "confidence": 0.75,
        },
        "TimeoutError": {
            "action": RecoveryAction.RETRY.value,
            "description": "Operation timed out — retry",
            "confidence": 0.7,
        },
        "JSONDecodeError": {
            "action": RecoveryAction.ALTERNATIVE_APPROACH.value,
            "description": "Corrupt data — attempt to load backup or reset",
            "confidence": 0.8,
        },
        "KeyError": {
            "action": RecoveryAction.ALTERNATIVE_APPROACH.value,
            "description": "Missing key — check data structure",
            "confidence": 0.85,
        },
        "ValueError": {
            "action": RecoveryAction.ALTERNATIVE_APPROACH.value,
            "description": "Invalid value — validate input",
            "confidence": 0.8,
        },
        "TypeError": {
            "action": RecoveryAction.ALTERNATIVE_APPROACH.value,
            "description": "Type mismatch — check argument types",
            "confidence": 0.8,
        },
        "OSError": {
            "action": RecoveryAction.RETRY.value,
            "description": "OS-level error — check permissions and paths",
            "confidence": 0.6,
        },
    }

    dependency_checks: Dict[str, str] = {
        "python": "python3 --version",
        "pip": "pip --version",
        "node": "node --version",
        "npm": "npm --version",
        "git": "git --version",
        "ffmpeg": "ffmpeg -version",
        "docker": "docker --version",
        "brew": "brew --version",
        "ruff": "ruff --version",
        "pytest": "pytest --version",
    }

    def __init__(self, error_memory: ErrorMemory) -> None:
        self._error_memory = error_memory
        self._recovery_history: List[Dict[str, Any]] = []

    async def diagnose(self, error: ErrorRecord) -> RecoveryPlan:
        """Analyze an error and produce a recovery plan."""
        plan = RecoveryPlan(error_id=error.id)

        known = self.known_solutions.get(error.error_type, {})
        if known:
            action_type = known.get("action", RecoveryAction.RETRY.value)
            plan.actions.append({
                "type": action_type,
                "description": known.get("description", ""),
                "target": error.module,
            })
            plan.confidence = known.get("confidence", 0.5)
            plan.requires_permission = action_type in (
                RecoveryAction.FIX_DEPENDENCY.value,
                RecoveryAction.ASK_USER.value,
                RecoveryAction.ESCALATE.value,
            )
        else:
            past_solutions = await self._error_memory.get_solutions(error.error_type)
            if past_solutions:
                plan.actions.append({
                    "type": RecoveryAction.ALTERNATIVE_APPROACH.value,
                    "description": f"Try previous solution: {past_solutions[0]}",
                    "target": error.module,
                })
                plan.confidence = 0.6
            else:
                plan.actions.append({
                    "type": RecoveryAction.SKIP.value,
                    "description": "No known solution — skip and log",
                    "target": error.module,
                })
                plan.confidence = 0.3

        if not plan.actions:
            plan.actions.append({
                "type": RecoveryAction.ESCALATE.value,
                "description": "Unable to diagnose — escalate to user",
                "target": error.module,
            })
            plan.fallback = "Ask user for guidance"

        plan.estimated_time = "instant" if plan.confidence > 0.7 else "unknown"
        return plan

    async def attempt_fix(self, plan: RecoveryPlan) -> Dict[str, Any]:
        """Try to execute the recovery plan."""
        result: Dict[str, Any] = {
            "plan": plan.to_dict(),
            "attempts": [],
            "success": False,
        }

        for action in plan.actions:
            action_type = action.get("type", "")
            attempt: Dict[str, Any] = {
                "action": action_type,
                "description": action.get("description", ""),
                "success": False,
            }

            if action_type == RecoveryAction.FIX_DEPENDENCY.value:
                pkg = action.get("target", "")
                if pkg:
                    install_result = await self.install_dependency(pkg)
                    attempt["install_result"] = install_result
                    attempt["success"] = install_result.get("ok", False)

            elif action_type == RecoveryAction.RETRY.value:
                attempt["success"] = True
                attempt["note"] = "Retry recommended — re-run the operation"

            elif action_type == RecoveryAction.ALTERNATIVE_APPROACH.value:
                attempt["success"] = True
                attempt["note"] = "Alternative approach identified"

            elif action_type == RecoveryAction.SKIP.value:
                attempt["success"] = True
                attempt["note"] = "Skipped — no action taken"

            else:
                attempt["success"] = False
                attempt["note"] = f"Action type '{action_type}' requires manual intervention"

            result["attempts"].append(attempt)
            if attempt["success"]:
                result["success"] = True
                break

        self._recovery_history.append({
            "plan": plan.to_dict(),
            "result": result,
            "timestamp": time.time(),
        })
        return result

    async def suggest_alternative(self, error: ErrorRecord) -> str:
        """Suggest an alternative approach for a given error."""
        known = self.known_solutions.get(error.error_type, {})
        if known:
            return known.get("description", "No alternative available.")

        past_solutions = await self._error_memory.get_solutions(error.error_type)
        if past_solutions:
            return f"Previous solutions: {'; '.join(past_solutions[:3])}"

        if "import" in error.message.lower() or "module" in error.message.lower():
            pkg = error.message.split("'")[1] if "'" in error.message else ""
            if pkg:
                return f"Try: pip install {pkg}"

        if "permission" in error.message.lower():
            return "Try running with appropriate permissions or check file ownership."

        if "connection" in error.message.lower() or "network" in error.message.lower():
            return "Check network connectivity and try again."

        if "timeout" in error.message.lower():
            return "Increase timeout or retry after a delay."

        return "No specific alternative found. Review error context and try a different approach."

    async def check_dependency(self, name: str) -> Dict[str, Any]:
        """Check if a tool or package is available on the system."""
        cmd = self.dependency_checks.get(name)
        if not cmd:
            cmd = f"{name} --version"

        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=10,
            )
            available = result.returncode == 0
            return {
                "name": name,
                "available": available,
                "version": result.stdout.strip() if available else "",
                "error": result.stderr.strip() if not available else "",
            }
        except subprocess.TimeoutExpired:
            return {
                "name": name,
                "available": False,
                "version": "",
                "error": "Timed out",
            }
        except Exception as exc:
            return {
                "name": name,
                "available": False,
                "version": "",
                "error": str(exc),
            }

    async def install_dependency(self, name: str) -> Dict[str, Any]:
        """Attempt to install a missing dependency."""
        try:
            pip = shutil.which("pip3") or shutil.which("pip") or "pip"
            result = subprocess.run(
                [pip, "install", name],
                capture_output=True,
                text=True,
                timeout=120,
            )
            success = result.returncode == 0
            return {
                "ok": success,
                "package": name,
                "output": result.stdout[-500:] if result.stdout else "",
                "error": result.stderr[-500:] if not success and result.stderr else "",
            }
        except subprocess.TimeoutExpired:
            return {
                "ok": False,
                "package": name,
                "error": "Installation timed out",
            }
        except Exception as exc:
            return {
                "ok": False,
                "package": name,
                "error": str(exc),
            }

    def get_recovery_history(self) -> List[Dict[str, Any]]:
        """Return the full recovery attempt history."""
        return list(self._recovery_history)
