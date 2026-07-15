"""Engineering King - ♠ King of Spades."""

from .base import BaseKing
from ...core.models import Suit


class EngineeringKing(BaseKing):
    """♠ King - Engineering Division Director.
    
    Personality: Perfectionist, strict, code quality focused.
    Responsible for: Software development, architecture, testing, deployment.
    """
    
    def __init__(self):
        super().__init__(suit=Suit.SPADES)
    
    @property
    def name(self) -> str:
        return "Engineering King"
    
    @property
    def title(self) -> str:
        return "Director of Engineering"
    
    @property
    def personality(self) -> str:
        return (
            "Perfectionist and strict. "
            "Obsessed with code quality, testing, and clean architecture. "
            "Will not approve work that doesn't meet high standards."
        )
