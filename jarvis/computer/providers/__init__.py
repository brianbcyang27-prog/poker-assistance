"""Platform providers for computer control.

Each platform (macOS, Windows, Linux) implements the same interface
so JARVIS can operate cross-platform.
"""

from .macos import MacOSProvider

# Default provider based on current platform
import sys
if sys.platform == "darwin":
    platform_provider = MacOSProvider()
elif sys.platform == "win32":
    # WindowsProvider placeholder
    platform_provider = None
else:
    # LinuxProvider placeholder
    platform_provider = None
