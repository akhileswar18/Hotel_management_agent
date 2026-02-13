"""
AuthAgent — Handles auth.login, auth.logout, auth.validate.

Delegates to AuthService for actual authentication.
"""

from typing import Optional
from src.agents.base import BaseAgent
from src.events.event import Event
from src.application import AuthService


class AuthAgent(BaseAgent):
    """Authentication agent delegating to AuthService."""

    name = "AuthAgent"
    subscribes_to = ["auth.login", "auth.logout", "auth.validate"]
    publishes = ["auth.logged_in", "auth.logged_out", "auth.validated", "auth.error"]
    writes_to_db = True
    uses_llm = False

    def __init__(self):
        self.auth_service = AuthService()

    def handle(self, event: Event) -> Optional[Event]:
        """Route auth events to handlers."""
        handlers = {
            "auth.login": self._handle_login,
            "auth.logout": self._handle_logout,
            "auth.validate": self._handle_validate,
        }
        handler = handlers.get(event.type)
        if handler:
            try:
                return handler(event)
            except Exception as e:
                return Event.create(
                    type="auth.error",
                    source=self.name,
                    correlation_id=event.correlation_id,
                    payload={
                        "error_code": type(e).__name__,
                        "message": str(e),
                    },
                    user_id=event.user_id,
                )
        return None

    def _handle_login(self, event: Event) -> Event:
        """Call AuthService.login and return auth.logged_in with user info."""
        payload = event.payload or {}
        username = payload.get("username", "").strip()
        pin = payload.get("pin", "")
        if not username:
            raise ValueError("Username is required")
        user, session_token = self.auth_service.login(username, pin)
        return Event.create(
            type="auth.logged_in",
            source=self.name,
            correlation_id=event.correlation_id,
            payload={
                "user_id": str(user.id),
                "username": user.username,
                "role": user.role.value,
                "token": session_token,
            },
            user_id=str(user.id),
        )

    def _handle_logout(self, event: Event) -> Event:
        """Call AuthService.logout and return auth.logged_out."""
        payload = event.payload or {}
        user_id = payload.get("user_id") or ""
        session_token = payload.get("session_token") or payload.get("token") or ""
        self.auth_service.logout(user_id=user_id, session_token=session_token)
        return Event.create(
            type="auth.logged_out",
            source=self.name,
            correlation_id=event.correlation_id,
            payload={"user_id": user_id},
            user_id=user_id or event.user_id,
        )

    def _handle_validate(self, event: Event) -> Event:
        """Validate session and return auth.validated."""
        payload = event.payload or {}
        session_token = payload.get("session_token") or payload.get("token") or ""
        if not session_token:
            raise ValueError("Session token is required")
        user = self.auth_service.validate_session(session_token)
        if not user:
            raise ValueError("Invalid or expired session")
        return Event.create(
            type="auth.validated",
            source=self.name,
            correlation_id=event.correlation_id,
            payload={
                "user_id": str(user.id),
                "username": user.username,
                "role": user.role.value,
            },
            user_id=str(user.id),
        )
