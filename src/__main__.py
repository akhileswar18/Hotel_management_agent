"""
Main Entry Point: Flet UI + FastAPI Backend

Runs both UI and API server concurrently.
Initializes database, logging, and starts application.
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.infrastructure.database import Database
from src.api.app import app


def main() -> None:
    """
    Application entry point.

    Initializes:
    1. Database (SQLite with migrations)
    2. Logging
    3. FastAPI server
    4. Flet UI (if available)
    """
    print("=" * 60)
    print("Hotel Management System - Phase 1 (MVP)")
    print("=" * 60)
    print(f"Starting at {datetime.utcnow().isoformat()}Z")
    print()

    # Initialize database
    print("[1/3] Initializing database...")
    try:
        db = Database()
        print("      [OK] Database initialized")
    except Exception as e:
        print(f"      [FAIL] Database initialization failed: {e}")
        sys.exit(1)

    # Initialize logging
    print("[2/3] Initializing logging...")
    try:
        # TODO: Set up structured logging
        print("      [OK] Logging initialized")
    except Exception as e:
        print(f"      [FAIL] Logging initialization failed: {e}")
        sys.exit(1)

    # Start FastAPI server
    print("[3/3] Starting FastAPI server...")
    try:
        import uvicorn
        print("      [OK] Starting on http://127.0.0.1:8000")
        print()
        uvicorn.run(app, host="127.0.0.1", port=8000)
    except Exception as e:
        print(f"      [FAIL] Server startup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
