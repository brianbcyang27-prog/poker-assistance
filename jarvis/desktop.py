"""Desktop app bootstrap — fullscreen golden core via pywebview."""

import sys
import threading
import time
import webbrowser

from jarvis.launcher import is_server_running, start_server, wait_for_server


class CoreBridge:
    """JS bridge exposed to the core page."""

    def quit(self):
        import webview

        webview.windows[0].destroy()

    def open_browser(self):
        webbrowser.open("http://127.0.0.1:8000")

    def report_error(self, message: str) -> None:
        print(f"[core-js] {message}", file=sys.stderr, flush=True)

    def core_ready(self, payload: str) -> None:
        print(f"[core-ready] {payload}", file=sys.stderr, flush=True)


def _ensure_server(port: int = 8000) -> bool:
    if is_server_running(port):
        return True
    proc = start_server(port)
    threading.Thread(target=proc.wait, daemon=True).start()
    return wait_for_server(port, timeout=30.0)


def _force_fullscreen(window) -> bool:
    """Enter native macOS fullscreen with verification and retry.

    pywebview's ``toggle_fullscreen`` flips an internal flag even when the OS
    rejects the transition, so we drive AppKit directly and confirm the real
    window mask actually contains ``NSFullScreenWindowMask``.
    """
    import AppKit
    from PyObjCTools.AppHelper import callAfter

    native = window.native
    mask = AppKit.NSFullScreenWindowMask
    enter = lambda: (  # noqa: E731
        native.setCollectionBehavior_(1 << 7),
        native.toggleFullScreen_(None),
    )
    for _ in range(3):
        callAfter(enter)
        for _ in range(20):
            time.sleep(0.25)
            if native.styleMask() & mask:
                return True
    return False


def launch_desktop(port: int = 8000) -> None:
    """Launch JARVIS as a fullscreen desktop app."""
    if not _ensure_server(port):
        raise RuntimeError(f"JARVIS server failed to start on port {port}")

    import webview

    screen = webview.screens[0]
    window = webview.create_window(
        "JARVIS",
        f"http://127.0.0.1:{port}/core",
        frameless=True,
        x=screen.x,
        y=screen.y,
        width=screen.width,
        height=screen.height,
        js_api=CoreBridge(),
        background_color="#000000",
    )

    def _fullscreen_after_load():
        window.events.loaded.wait()
        window.show()
        time.sleep(0.75)
        if not _force_fullscreen(window):
            window.toggle_fullscreen()
            time.sleep(1.5)

    threading.Thread(target=_fullscreen_after_load, daemon=True).start()
    webview.start()


if __name__ == "__main__":
    launch_desktop()
