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
import socket
from pathlib import Path

# Ensure project root is on sys.path for imports
_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)


def _load_env_file() -> None:
    """Load .env into process environment (simple KEY=VALUE parser)."""
    env_path = Path(_project_root) / ".env"
    if not env_path.exists():
        return

    try:
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            if not key:
                continue
            # Strip matching single/double quote wrappers if present.
            if len(value) >= 2 and ((value[0] == value[-1]) and value[0] in ("'", '"')):
                value = value[1:-1]
            os.environ[key] = value
    except Exception:
        # Launcher should remain resilient even if .env has malformed lines.
        pass


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

    start = time.monotonic()
    while time.monotonic() - start < timeout:
        try:
            with socket.create_connection((host, port), timeout=1.0):
                return True
        except OSError:
            time.sleep(0.25)
    return False


def _is_port_open(host: str, port: int, timeout: float = 0.5) -> bool:
    """Check whether a TCP port is currently reachable."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
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

    _load_env_file()

    print("=" * 60)
    print("  Hotel Management System v1.0")
    print("=" * 60)
    print(f"  Started at {datetime.utcnow().isoformat()}Z")
    print()

    host = os.getenv("API_HOST", "127.0.0.1")
    api_port = int(os.getenv("API_PORT", "8000"))
    ui_host = os.getenv("UI_HOST", "127.0.0.1")
    ui_port = int(os.getenv("UI_PORT", "8080"))

    # Fast-path guard for duplicate launcher runs.
    api_already_running = _is_port_open(host, api_port)
    ui_already_running = _is_port_open(ui_host, ui_port)
    if api_already_running and ui_already_running:
        print("[0/5] Existing HMS instance detected.")
        print(f"      API: http://{host}:{api_port}")
        print(f"      UI:  http://{ui_host}:{ui_port}")
        print("      Launcher will exit to avoid duplicate bind conflicts.")
        return

    # --- Step 1: Initialize database ---
    print("[1/5] Initializing database...")
    try:
        from src.infrastructure.database import Database
        db = Database()
        print("      [OK] Database ready")
    except Exception as e:
        print(f"      [FAIL] {e}")
        sys.exit(1)

    # --- Step 2: Seed default users if none exist ---
    print("[2/5] Checking for default users...")
    try:
        from src.infrastructure import UserRepository
        from src.application import AuthService
        from src.domain import User, Role
        from uuid import uuid4
        from datetime import datetime

        user_repo = UserRepository()
        users = user_repo.list()
        if not users:
            auth_service = AuthService()
            for username, pin, role in [
                ("waiter", "1234", Role.WAITER),
                ("cashier", "1234", Role.CASHIER),
                ("manager", "1234", Role.MANAGER),
                ("clerk", "1234", Role.CLERK),
            ]:
                pin_hash = auth_service.hash_pin(pin)
                user = User(
                    id=uuid4(),
                    username=username,
                    role=role,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    created_by=None,
                    updated_by=None,
                )
                user_repo.create(user, pin_hash)
            print("      [OK] Created default users (e.g. cashier / 1234)")
        else:
            print("      [OK] Users already exist")
    except Exception as e:
        print(f"      [WARN] Could not seed users: {e}")

    # --- Step 3: Start API server in background ---
    if api_already_running:
        print(f"[3/5] Starting API server...")
        print(f"      [SKIP] API already running on {host}:{api_port}")
    else:
        print("[3/5] Starting API server...")
        api_thread = threading.Thread(target=_start_api_server, daemon=True)
        api_thread.start()

    # --- Step 4: Wait for API ---
    print(f"[4/5] Waiting for API on {host}:{api_port}...")

    if _wait_for_api(host, api_port):
        print(f"      [OK] API ready at http://{host}:{api_port}")
    else:
        print("      [WARN] API not responding yet — UI will retry connections")

    # --- Step 5: Start Flet UI (blocks) ---
    print("[5/5] Starting UI...")
    print()
    if ui_already_running:
        print(f"UI already running at http://{ui_host}:{ui_port}")
        print("Launcher will exit to avoid duplicate UI bind conflicts.")
        return

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
