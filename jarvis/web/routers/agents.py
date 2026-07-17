"""Agents router - Agent status and hierarchy."""

from fastapi import APIRouter

import jarvis.web.main as web_main

router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.get("")
async def get_agents():
    """Get all agents and their status."""
    if not web_main.jarvis:
        return {"error": "JARVIS not initialized"}
    
    return web_main.jarvis.get_status()


@router.get("/hierarchy")
async def get_hierarchy():
    """Get agent hierarchy for visualization."""
    if not web_main.jarvis:
        return {"error": "JARVIS not initialized"}
    
    hierarchy = {
        "jarvis": {
            "card_id": "J",
            "name": "JARVIS",
            "state": web_main.jarvis.state.value,
        },
        "kings": []
    }
    
    for king in web_main.jarvis.get_all_kings():
        king_data = {
            "card_id": king.card_id,
            "name": king.name,
            "suit": king.suit.value if king.suit else None,
            "state": king.state.value,
            "workers": []
        }
        
        for worker in king.get_all_workers():
            king_data["workers"].append({
                "card_id": worker.card_id,
                "name": worker.name,
                "state": worker.state.value,
            })
        
        hierarchy["kings"].append(king_data)
    
    return hierarchy


@router.get("/{card_id}")
async def get_agent(card_id: str):
    """Get a specific agent by card_id."""
    if not web_main.jarvis:
        return {"error": "JARVIS not initialized"}
    
    # Check if it's JARVIS
    if card_id == "J":
        return web_main.jarvis.to_dict()
    
    # Check Kings
    king = web_main.jarvis.get_king(card_id)
    if king:
        return king.to_dict()
    
    # Check workers
    for king in web_main.jarvis.get_all_kings():
        worker = king.get_worker(card_id)
        if worker:
            return worker.to_dict()
    
    return {"error": f"Agent {card_id} not found"}
