"""Shared test configuration — ensures jarvis is importable."""
import sys
import os
import pytest

# Add project root to Python path at collection time
_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _root not in sys.path:
    sys.path.insert(0, _root)


@pytest.fixture(autouse=True)
def _ensure_jarvis_path():
    """Ensure project root is on sys.path during test execution."""
    if _root not in sys.path:
        sys.path.insert(0, _root)
    yield
