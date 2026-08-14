"""Entry point for the standalone IR Remote Wizard."""

import webbrowser
import threading
import uvicorn


def open_browser():
    """Open the wizard in the default browser after a short delay."""
    import time
    time.sleep(1.5)
    webbrowser.open(f"http://localhost:{PORT}")


PORT = int(__import__("os").environ.get("PORT", 8081))

if __name__ == "__main__":
    print("=" * 50)
    print("  IR Remote Wizard — Standalone")
    print(f"  http://localhost:{PORT}")
    print("=" * 50)

    threading.Thread(target=open_browser, daemon=True).start()

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=PORT,
        reload=False,
    )
