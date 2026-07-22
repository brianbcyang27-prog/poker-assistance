#!/usr/bin/env python3
"""JARVIS Launcher — validates API key, then starts the server."""

import os
import sys
import subprocess
import urllib.request


def test_nvidia_key(key: str) -> bool:
    """Test if an NVIDIA API key is valid."""
    try:
        req = urllib.request.Request(
            "https://integrate.api.nvidia.com/v1/models",
            headers={"Authorization": f"Bearer {key}"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception:
        return False


def save_key_to_env(key: str):
    """Save a new key to .env file."""
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    lines = []
    found = False
    if os.path.exists(env_path):
        for line in open(env_path):
            if line.startswith("NVIDIA_API_KEY="):
                lines.append(f"NVIDIA_API_KEY={key}\n")
                found = True
            else:
                lines.append(line)
    if not found:
        lines.insert(0, f"NVIDIA_API_KEY={key}\n")
    with open(env_path, "w") as f:
        f.writelines(lines)


def load_current_key() -> str:
    """Load the current NVIDIA API key from .env."""
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_path):
        for line in open(env_path):
            if line.startswith("NVIDIA_API_KEY="):
                return line.split("=", 1)[1].strip()
    return ""


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    current_key = load_current_key()

    if current_key:
        print(f"Testing current API key: {current_key[:12]}...")
        if test_nvidia_key(current_key):
            print("API key is valid!")
        else:
            print("API key is expired or invalid.")
            new_key = input("Enter new NVIDIA API key (or press Enter to skip): ").strip()
            if new_key:
                save_key_to_env(new_key)
                if test_nvidia_key(new_key):
                    print("New key validated and saved!")
                else:
                    print("New key also invalid. Server may not work.")
            else:
                print("No key set. Server may not work.")
    else:
        print("No NVIDIA API key found.")
        new_key = input("Enter your NVIDIA API key: ").strip()
        if new_key:
            save_key_to_env(new_key)
            if test_nvidia_key(new_key):
                print("Key validated and saved!")
            else:
                print("Key saved but could not validate.")
        else:
            print("No key provided. Server may not work.")

    print("\nStarting JARVIS server at http://127.0.0.1:8000 ...\n")
    subprocess.run([
        sys.executable, "-m", "uvicorn", "jarvis.web.main:app",
        "--host", "127.0.0.1", "--port", "8000"
    ])


if __name__ == "__main__":
    main()
