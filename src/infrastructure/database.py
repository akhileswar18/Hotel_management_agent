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

    def backup(self, backup_path: str = None) -> str:
        """
        Create a backup of the database.

        Args:
            backup_path: Optional path for backup file. If None, auto-generates.

        Returns:
            Path to the backup file.
        """
        from pathlib import Path

        if self._connection is None:
            raise RuntimeError("Database not initialized")

        # Get current db path
        config = DatabaseConfig()
        source_path = config.db_path

        if backup_path is None:
            backup_dir = Path("backups")
            backup_dir.mkdir(exist_ok=True)
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            backup_path = str(backup_dir / f"hms_backup_{timestamp}.db")

        # Checkpoint WAL to ensure consistency
        self._connection.execute("PRAGMA wal_checkpoint(FULL)")

        # Use SQLite backup API
        backup_conn = sqlite3.connect(backup_path)
        self._connection.backup(backup_conn)
        backup_conn.close()

        return backup_path

    def restore(self, backup_path: str) -> None:
        """
        Restore database from a backup file.

        Args:
            backup_path: Path to the backup file.
        """
        import shutil
        from pathlib import Path

        if not Path(backup_path).exists():
            raise FileNotFoundError(f"Backup file not found: {backup_path}")

        config = DatabaseConfig()
        target_path = config.db_path

        # Close current connection
        if self._connection:
            self._connection.close()
            self._connection = None

        # Copy backup over current DB
        shutil.copy2(backup_path, target_path)

        # Remove WAL and SHM files if they exist
        for ext in ["-wal", "-shm"]:
            wal_path = Path(target_path + ext)
            if wal_path.exists():
                wal_path.unlink()

        # Reset singleton and reinitialize
        Database._instance = None
        Database._connection = None

    def vacuum(self) -> None:
        """Run VACUUM to reclaim space and optimize the database."""
        if self._connection is None:
            raise RuntimeError("Database not initialized")
        self._connection.execute("VACUUM")

    def get_db_size(self) -> dict:
        """Get database file size info."""
        from pathlib import Path
        config = DatabaseConfig()
        db_path = Path(config.db_path)
        size_bytes = db_path.stat().st_size if db_path.exists() else 0
        wal_path = Path(config.db_path + "-wal")
        wal_size = wal_path.stat().st_size if wal_path.exists() else 0
        return {
            "db_size_bytes": size_bytes,
            "db_size_mb": round(size_bytes / (1024 * 1024), 2),
            "wal_size_bytes": wal_size,
            "total_mb": round((size_bytes + wal_size) / (1024 * 1024), 2),
        }

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
