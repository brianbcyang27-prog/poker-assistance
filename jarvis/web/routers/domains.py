"""Domains router - v10 domain registry API."""

from fastapi import APIRouter

import jarvis.web.main as web_main

router = APIRouter(prefix="/api/domains", tags=["domains"])


@router.get("")
async def get_domains():
    """Get all domains with their masters and members."""
    if not web_main.domain_registry:
        return {"error": "Domains not initialized"}

    return {
        "domains": [
            {
                "domain": master.domain.value,
                "label": master.domain.label,
                "master": master.get_status(),
            }
            for master in web_main.domain_registry.all()
        ]
    }


@router.get("/{domain_id}")
async def get_domain(domain_id: str):
    """Get a single domain's master and members by value or alias."""
    if not web_main.domain_registry:
        return {"error": "Domains not initialized"}

    master = web_main.domain_registry.get(domain_id)
    if master is None:
        return {"error": f"Domain '{domain_id}' not found"}
    return master.get_status()
