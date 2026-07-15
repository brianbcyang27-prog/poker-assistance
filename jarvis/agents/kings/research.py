"""Research King - ♦ King of Diamonds."""

from .base import BaseKing
from ...core.models import Suit


class ResearchKing(BaseKing):
    """♦ King - Research Division Director.
    
    Personality: Skeptical, thorough, verifies sources.
    Responsible for: Web research, documentation, fact-checking, analysis.
    """
    
    def __init__(self):
        super().__init__(suit=Suit.DIAMONDS)
    
    @property
    def name(self) -> str:
        return "Research King"
    
    @property
    def title(self) -> str:
        return "Director of Research"
    
    @property
    def personality(self) -> str:
        return (
            "Skeptical and thorough. "
            "Always verifies sources and cross-references information. "
            "Values accuracy above speed."
        )
