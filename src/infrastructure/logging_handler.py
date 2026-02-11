"""
Infrastructure Layer: Structured Logging

Logs to both SQLite database and rotating file logs.
All logs in JSON format for structured querying.
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Any, Dict

from src.infrastructure.database import Database


class StructuredLogger:
    """Structured logging to database and files."""

    def __init__(self, log_dir: str = "logs") -> None:
        """Initialize logger."""
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.db = Database()

    def log(
        self,
        level: str,
        category: str,
        message: str,
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log structured message to both DB and file.

        Args:
            level: DEBUG, INFO, WARN, ERROR
            category: Log category (sales.billing, inventory.stock, etc.)
            message: Human-readable message
            user_id: User performing action
            action: Specific action
            entity_type: Type of entity affected
            entity_id: ID of entity affected
            details: Additional details as dict
        """
        # Create log entry
        timestamp = datetime.utcnow().isoformat() + "Z"
        log_entry = {
            "timestamp": timestamp,
            "level": level,
            "category": category,
            "message": message,
            "user_id": user_id,
            "action": action,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "details": details or {},
        }

        # Log to database
        self._log_to_db(log_entry)

        # Log to file
        self._log_to_file(log_entry)

    def _log_to_db(self, entry: Dict[str, Any]) -> None:
        """Write log to database."""
        if self.db._connection is None:
            return

        query = """
            INSERT INTO system_log (
                id, level, category, user_id, action,
                entity_type, entity_id, timestamp, message, details
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        from uuid import uuid4
        params = (
            str(uuid4()),
            entry["level"],
            entry["category"],
            entry["user_id"],
            entry["action"],
            entry["entity_type"],
            entry["entity_id"],
            entry["timestamp"],
            entry["message"],
            json.dumps(entry["details"]),
        )
        try:
            self.db.execute(query, params)
            self.db.commit()
        except Exception as e:
            # Fail silently; don't crash app due to logging error
            print(f"Failed to log to database: {e}")

    def _log_to_file(self, entry: Dict[str, Any]) -> None:
        """Write log to rotating file."""
        today = datetime.utcnow().strftime("%Y-%m-%d")
        log_file = self.log_dir / f"hms-{today}.log"

        try:
            with open(log_file, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            # Fail silently
            print(f"Failed to log to file: {e}")


# Global logger instance
_logger: Optional[StructuredLogger] = None


def get_logger() -> StructuredLogger:
    """Get global logger instance."""
    global _logger
    if _logger is None:
        _logger = StructuredLogger()
    return _logger


def log_info(
    category: str,
    message: str,
    **kwargs,
) -> None:
    """Log INFO level message."""
    logger = get_logger()
    logger.log("INFO", category, message, **kwargs)


def log_error(
    category: str,
    message: str,
    **kwargs,
) -> None:
    """Log ERROR level message."""
    logger = get_logger()
    logger.log("ERROR", category, message, **kwargs)


def log_warning(
    category: str,
    message: str,
    **kwargs,
) -> None:
    """Log WARN level message."""
    logger = get_logger()
    logger.log("WARN", category, message, **kwargs)


def log_debug(
    category: str,
    message: str,
    **kwargs,
) -> None:
    """Log DEBUG level message."""
    logger = get_logger()
    logger.log("DEBUG", category, message, **kwargs)


# TODO: Implement log rotation
# TODO: Implement log cleanup (archive old logs)
# TODO: Add performance logging decorators
