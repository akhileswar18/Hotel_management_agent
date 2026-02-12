"""
HMS Unified Launcher

Starts both the FastAPI backend server and Flet UI in a single process.
Used by PyInstaller to create a standalone Windows executable.

Architecture:
  - FastAPI runs in a background daemon thread (port 8000)
  - Flet UI runs in the main thread (port 8080, opens browser)
  - On exit, the daemon thread is automatically cleaned up
"""

import sys
import os
import time
import threading
from pathlib import Path

# Ensure project root is on sys.path for imports
_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)


def _start_api_server() -> None:
    """Start FastAPI backend in background thread."""
    import uvicorn
    from src.api.app import app

    host = os.getenv("API_HOST", "127.0.0.1")
    port = int(os.getenv("API_PORT", "8000"))

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="warning",  # Reduce noise when running alongside UI
    )


def _wait_for_api(host: str = "127.0.0.1", port: int = 8000, timeout: float = 15.0) -> bool:
    """Wait for the API server to become responsive."""
    import socket

    start = time.monotonic()
    while time.monotonic() - start < timeout:
        try:
            with socket.create_connection((host, port), timeout=1.0):
                return True
        except OSError:
            time.sleep(0.25)
    return False


def main() -> None:
    """
    Launch HMS application (API + UI).

    1. Initialize database
    2. Start FastAPI in a daemon thread
    3. Wait for API readiness
    4. Start Flet UI (blocks until window closed)
    """
    from datetime import datetime

    print("=" * 60)
    print("  Hotel Management System v1.0")
    print("=" * 60)
    print(f"  Started at {datetime.utcnow().isoformat()}Z")
    print()

    # --- Step 1: Initialize database ---
    print("[1/4] Initializing database...")
    try:
        from src.infrastructure.database import Database
        db = Database()
        print("      [OK] Database ready")
    except Exception as e:
        print(f"      [FAIL] {e}")
        sys.exit(1)

    # --- Step 2: Start API server in background ---
    print("[2/4] Starting API server...")
    api_thread = threading.Thread(target=_start_api_server, daemon=True)
    api_thread.start()

    # --- Step 3: Wait for API ---
    host = os.getenv("API_HOST", "127.0.0.1")
    port = int(os.getenv("API_PORT", "8000"))
    print(f"[3/4] Waiting for API on {host}:{port}...")

    if _wait_for_api(host, port):
        print(f"      [OK] API ready at http://{host}:{port}")
    else:
        print("      [WARN] API not responding yet — UI will retry connections")

    # --- Step 4: Start Flet UI (blocks) ---
    print("[4/4] Starting UI...")
    print()
    try:
        from src.ui.app import main as flet_main
        flet_main()
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"UI error: {e}")
        sys.exit(1)

    print("HMS shut down cleanly.")


if __name__ == "__main__":
    main()
