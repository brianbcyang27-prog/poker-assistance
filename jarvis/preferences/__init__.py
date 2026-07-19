"""JARVIS Preference Learning — tracks user preferences with confidence scores.

Usage:
    engine = PreferenceEngine()
    await engine.bootstrap()
    pref = await engine.learn("coding", "language", "python")
    prefs = await engine.get_coding_preferences()
"""

from .engine import PreferenceEngine
from .models import Preference, PreferenceCategory, PreferenceProfile

__all__ = [
    "PreferenceEngine",
    "Preference",
    "PreferenceCategory",
    "PreferenceProfile",
]
