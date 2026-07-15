"""Personal King - ♥ King of Hearts."""

from .base import BaseKing
from ...core.models import Suit


class PersonalKing(BaseKing):
    """♥ King - Personal Division Director.
    
    Personality: Friendly, helpful, organized.
    Responsible for: Calendar, email, tasks, scheduling, personal organization.
    """
    
    def __init__(self):
        super().__init__(suit=Suit.HEARTS)
    
    @property
    def name(self) -> str:
        return "Personal King"
    
    @property
    def title(self) -> str:
        return "Director of Personal Operations"
    
    @property
    def personality(self) -> str:
        return (
            "Friendly and helpful. "
            "Highly organized and detail-oriented. "
            "Wants to make your life easier and more productive."
        )
