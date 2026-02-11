"""
Migration Runner: Apply database migrations in order.

Handles schema versioning and tracks applied migrations in the database.
Idempotent: applying the same migration twice is safe.
"""

import sqlite3
from pathlib import Path
from datetime import datetime
from typing import List, Optional


class MigrationRunner:
    """Manages database schema migrations."""

    def __init__(self, db_path: str) -> None:
        """
        Initialize migration runner.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.migrations_dir = Path(__file__).parent

    def apply_migrations(self) -> None:
        """
        Apply all pending migrations in order.

        Migrations are applied in alphanumeric order (001_*, 002_*, etc).
        Stops on first error and reports which migration failed.
        """
        conn = sqlite3.connect(self.db_path)
        try:
            # Create migrations_applied table if not exists
            conn.execute("""
                CREATE TABLE IF NOT EXISTS migrations_applied (
                    migration_name TEXT PRIMARY KEY,
                    applied_at TEXT NOT NULL,
                    rolled_back_at TEXT
                )
            """)
            conn.commit()

            # Get all migration files
            migration_files = sorted(
                self.migrations_dir.glob("*.sql")
            )

            for migration_file in migration_files:
                migration_name = migration_file.name
                if self._is_migration_applied(conn, migration_name):
                    print(f"[SKIP] {migration_name} already applied")
                    continue

                try:
                    self._apply_migration(conn, migration_file)
                    self._record_migration(conn, migration_name)
                    print(f"[OK] Applied {migration_name}")
                except Exception as e:
                    print(f"[FAILED] Failed to apply {migration_name}: {e}")
                    conn.rollback()
                    raise

        finally:
            conn.close()

    def _is_migration_applied(self, conn: sqlite3.Connection, migration_name: str) -> bool:
        """Check if migration has been applied."""
        cursor = conn.execute(
            "SELECT 1 FROM migrations_applied WHERE migration_name = ? AND rolled_back_at IS NULL",
            (migration_name,),
        )
        return cursor.fetchone() is not None

    def _apply_migration(self, conn: sqlite3.Connection, migration_file: Path) -> None:
        """Execute SQL migration file."""
        sql = migration_file.read_text()
        cursor = conn.cursor()
        cursor.executescript(sql)
        conn.commit()

    def _record_migration(self, conn: sqlite3.Connection, migration_name: str) -> None:
        """Record migration as applied in database."""
        now = datetime.utcnow().isoformat() + "Z"
        conn.execute(
            "INSERT INTO migrations_applied (migration_name, applied_at) VALUES (?, ?)",
            (migration_name, now),
        )
        conn.commit()

    def get_applied_migrations(self) -> List[str]:
        """Get list of applied migrations."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute(
                "SELECT migration_name FROM migrations_applied WHERE rolled_back_at IS NULL"
            )
            return [row[0] for row in cursor.fetchall()]
        finally:
            conn.close()

    def rollback_last(self) -> None:
        """Mark last migration as rolled back (Phase 2+, for now just marks it)."""
        # TODO: Implement actual rollback logic
        print("Rollback not yet implemented")


def init_db(db_path: str) -> sqlite3.Connection:
    """
    Initialize database and run migrations.

    Creates database file if it doesn't exist, runs all pending migrations,
    and returns an active connection.

    Args:
        db_path: Path to SQLite database file

    Returns:
        sqlite3.Connection: Active database connection (thread-safe with check_same_thread=False)
    """
    # Create database file if doesn't exist
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    # Run migrations
    runner = MigrationRunner(db_path)
    runner.apply_migrations()

    # Return connection
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row  # Return rows as dict-like objects
    return conn


if __name__ == "__main__":
    # CLI interface: python -m migrations.runner
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m migrations.runner <apply|rollback>")
        sys.exit(1)

    command = sys.argv[1]
    db_path = sys.argv[2] if len(sys.argv) > 2 else "hms.db"

    runner = MigrationRunner(db_path)

    if command == "apply":
        runner.apply_migrations()
        print("[OK] All migrations applied")
    elif command == "status":
        applied = runner.get_applied_migrations()
        print(f"Applied migrations: {len(applied)}")
        for m in applied:
            print(f"  - {m}")
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
