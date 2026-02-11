"""
Infrastructure Layer: Database Connection & Configuration

Manages SQLite database initialization and connection pooling.
Single source of truth for DB configuration.
"""

import sqlite3
import os
from pathlib import Path
from contextlib import contextmanager
from typing import Generator, Optional
from datetime import datetime

from migrations.runner import init_db


class DatabaseConfig:
    """Database configuration from environment."""

    def __init__(self) -> None:
        """Initialize config from .env or defaults."""
        self.db_path = os.getenv("DATABASE_URL", "sqlite:///./hms.db")
        # Convert SQLite URL to file path
        if self.db_path.startswith("sqlite:////"):
            self.db_path = self.db_path.replace("sqlite:////", "")
        elif self.db_path.startswith("sqlite:///"):
            self.db_path = self.db_path[10:]

        # Ensure directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    def __repr__(self) -> str:
        return f"DatabaseConfig(db_path={self.db_path})"


class Database:
    """
    Database manager: connection pooling and lifecycle.

    Maintains single SQLite connection (thread-safe with check_same_thread=False).
    Initializes schema on first use.
    """

    _instance: Optional["Database"] = None
    _connection: Optional[sqlite3.Connection] = None

    def __new__(cls) -> "Database":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Initialize database singleton."""
        if self._connection is None:
            config = DatabaseConfig()
            self._connection = init_db(config.db_path)
            # Set up connection parameters
            self._connection.row_factory = sqlite3.Row
            self._setup_pragmas()

    def _setup_pragmas(self) -> None:
        """Configure SQLite pragmas for data integrity."""
        if self._connection is None:
            return

        # Enable foreign key constraints
        self._connection.execute("PRAGMA foreign_keys = ON")

        # WAL mode for better concurrency
        self._connection.execute("PRAGMA journal_mode = WAL")

        # Set timeout for busy databases
        self._connection.execute("PRAGMA busy_timeout = 5000")

    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """
        Get database connection (context manager).

        Usage:
            with db.get_connection() as conn:
                cursor = conn.execute("SELECT ...")
        """
        if self._connection is None:
            raise RuntimeError("Database not initialized")
        try:
            yield self._connection
        except Exception as e:
            self._connection.rollback()
            raise RuntimeError(f"Database error: {e}") from e

    def execute(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        """
        Execute query directly.

        Use with caution; prefer repositories for model operations.
        """
        if self._connection is None:
            raise RuntimeError("Database not initialized")
        return self._connection.execute(query, params)

    def executemany(self, query: str, params_list: list) -> None:
        """Execute multiple queries with parameter sets."""
        if self._connection is None:
            raise RuntimeError("Database not initialized")
        self._connection.executemany(query, params_list)
        self._connection.commit()

    def commit(self) -> None:
        """Commit current transaction."""
        if self._connection is not None:
            self._connection.commit()

    def rollback(self) -> None:
        """Rollback current transaction."""
        if self._connection is not None:
            self._connection.rollback()

    def close(self) -> None:
        """Close database connection."""
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    @staticmethod
    def get_utc_now_str() -> str:
        """Get current UTC timestamp as ISO 8601 string."""
        return datetime.utcnow().isoformat() + "Z"


# Singleton instance
_db_instance = Database()


def get_db() -> sqlite3.Connection:
    """
    Get database connection for dependency injection.

    Usage in services:
        def __init__(self):
            self.db = get_db()
    """
    db = Database()
    if db._connection is None:
        raise RuntimeError("Database not initialized")
    return db._connection


# TODO: Implement connection pooling for multi-threaded scenarios
# TODO: Add database health check endpoint
# TODO: Add database backup/restore functionality
