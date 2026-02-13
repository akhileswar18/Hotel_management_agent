"""
Database Backup & Restore CLI

Usage:
    python scripts/backup.py backup [--path PATH]
    python scripts/backup.py restore --path PATH
    python scripts/backup.py list
    python scripts/backup.py vacuum
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def cmd_backup(backup_path=None):
    """Create database backup."""
    from src.infrastructure.database import Database
    db = Database()
    path = db.backup(backup_path)
    size_info = db.get_db_size()
    print(f"[OK] Backup created: {path}")
    print(f"     Database size: {size_info['db_size_mb']} MB")


def cmd_restore(backup_path):
    """Restore database from backup."""
    if not Path(backup_path).exists():
        print(f"[ERROR] File not found: {backup_path}")
        sys.exit(1)

    confirm = input(f"Restore from {backup_path}? This will overwrite the current database. (yes/no): ")
    if confirm.lower() != "yes":
        print("[CANCELLED] Restore aborted.")
        return

    from src.infrastructure.database import Database
    db = Database()
    db.restore(backup_path)
    print(f"[OK] Database restored from: {backup_path}")
    print("     Restart the application to use the restored data.")


def cmd_list():
    """List available backups."""
    backup_dir = Path("backups")
    if not backup_dir.exists():
        print("No backups directory found.")
        return

    backups = sorted(backup_dir.glob("*.db"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not backups:
        print("No backups found.")
        return

    print(f"\nAvailable backups ({len(backups)}):")
    print("-" * 60)
    for b in backups:
        size_mb = b.stat().st_size / (1024 * 1024)
        mod_time = datetime.fromtimestamp(b.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        print(f"  {b.name:<40} {size_mb:>6.2f} MB  {mod_time}")


def cmd_vacuum():
    """Vacuum the database to reclaim space."""
    from src.infrastructure.database import Database
    db = Database()
    before = db.get_db_size()
    db.vacuum()
    after = db.get_db_size()
    saved = before["db_size_bytes"] - after["db_size_bytes"]
    print(f"[OK] Database vacuumed.")
    print(f"     Before: {before['db_size_mb']} MB")
    print(f"     After:  {after['db_size_mb']} MB")
    print(f"     Saved:  {saved / 1024:.1f} KB")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == "backup":
        path = None
        if "--path" in sys.argv:
            idx = sys.argv.index("--path")
            if idx + 1 < len(sys.argv):
                path = sys.argv[idx + 1]
        cmd_backup(path)
    elif command == "restore":
        if "--path" not in sys.argv:
            print("[ERROR] --path required for restore")
            sys.exit(1)
        idx = sys.argv.index("--path")
        if idx + 1 >= len(sys.argv):
            print("[ERROR] --path value missing")
            sys.exit(1)
        cmd_restore(sys.argv[idx + 1])
    elif command == "list":
        cmd_list()
    elif command == "vacuum":
        cmd_vacuum()
    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
