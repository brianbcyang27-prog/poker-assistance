"""Security API endpoints for the dashboard."""

import time
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/security", tags=["security"])


class VaultCreateRequest(BaseModel):
    password: str
    secrets: dict = {}

class VaultUnlockRequest(BaseModel):
    password: str

class VaultPasswordChangeRequest(BaseModel):
    old_password: str
    new_password: str

class SecretSetRequest(BaseModel):
    key: str
    value: str


@router.get("/status")
async def security_status():
    """Get security system status."""
    from ...security import get_manager
    from ...security.vault import EncryptedVault
    from ...security.audit import AuditLog

    mgr = get_manager()
    vault = mgr.vault
    audit = AuditLog()

    return {
        "vault_exists": vault.exists,
        "vault_unlocked": vault.is_unlocked,
        "secret_count": vault.secret_count if vault.is_unlocked else 0,
        "encryption": "AES-256-GCM",
        "kdf": "PBKDF2-HMAC-SHA256",
        "iterations": 600_000,
        "providers": [{"name": p.name, "priority": p.priority} for p in mgr.providers],
        "audit_stats": audit.get_stats(),
    }


@router.post("/vault/create")
async def vault_create(req: VaultCreateRequest):
    """Create a new encrypted vault."""
    from ...security import get_manager

    mgr = get_manager()
    try:
        mgr.vault.create(req.password, req.secrets)
        return {"ok": True, "message": "Vault created", "secret_count": len(req.secrets)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/vault/unlock")
async def vault_unlock(req: VaultUnlockRequest):
    """Unlock the vault with a password."""
    from ...security import get_manager

    mgr = get_manager()
    try:
        mgr.vault.unlock(req.password)
        return {"ok": True, "message": "Vault unlocked"}
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.post("/vault/lock")
async def vault_lock():
    """Lock the vault."""
    from ...security import get_manager
    mgr = get_manager()
    mgr.vault.lock()
    return {"ok": True, "message": "Vault locked"}


@router.post("/vault/password")
async def vault_change_password(req: VaultPasswordChangeRequest):
    """Change vault password."""
    from ...security import get_manager
    mgr = get_manager()
    try:
        mgr.vault.change_password(req.old_password, req.new_password)
        return {"ok": True, "message": "Password changed"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/secrets")
async def list_secrets():
    """List all secrets (masked)."""
    from ...security import get_manager
    mgr = get_manager()
    if not mgr.is_vault_ready:
        return {"secrets": {}, "vault_ready": False}
    try:
        return {"secrets": mgr.list_all(), "vault_ready": True}
    except Exception:
        return {"secrets": {}, "vault_ready": False}


@router.post("/secrets")
async def set_secret(req: SecretSetRequest):
    """Set a secret in the vault."""
    from ...security import get_manager
    mgr = get_manager()
    try:
        mgr.set(req.key, req.value)
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/secrets/{key}")
async def delete_secret(key: str):
    """Delete a secret from the vault."""
    from ...security import get_manager
    mgr = get_manager()
    mgr.delete(key)
    return {"ok": True}


@router.get("/scan")
async def scan_repository():
    """Scan repository for secrets."""
    from ...security.scanner import SecretScanner
    scanner = SecretScanner()
    findings = scanner.scan()
    report = scanner.generate_report(findings)
    return {"findings": findings, "count": len(findings), "report": report}


@router.get("/scan/report")
async def scan_report_file():
    """Run scan and save security_report.md."""
    from ...security.scanner import SecretScanner
    scanner = SecretScanner()
    path = scanner.scan_and_save()
    return {"ok": True, "path": path}


@router.get("/audit")
async def audit_log(limit: int = 100):
    """Get audit log entries."""
    from ...security.audit import AuditLog
    audit = AuditLog()
    return {"entries": audit.get_entries(limit), "stats": audit.get_stats()}


@router.get("/providers")
async def list_providers():
    """List all secret providers and their status."""
    from ...security import get_manager
    mgr = get_manager()
    health = mgr.health_check()
    return {"providers": health}


@router.get("/git-protection")
async def git_protection_status():
    """Get git protection status."""
    from ...security.git_protection import GitProtection
    gp = GitProtection()
    return gp.get_status()


@router.post("/git-protection/install")
async def install_git_protection():
    """Install .gitignore entries and pre-commit hook."""
    from ...security.git_protection import GitProtection
    gp = GitProtection()
    gp.setup_gitignore()
    gp.install_pre_commit_hook()
    return {"ok": True, "status": gp.get_status()}


@router.post("/redact")
async def redact_text(text: str):
    """Redact secrets from text."""
    from ...security.redactor import redact
    return {"redacted": redact(text)}
