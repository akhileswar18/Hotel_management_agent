"""
Speech-to-Text — Offline-first using Whisper.

Lazy-loads the model; returns empty string on failure or if Whisper is not installed.
"""

from typing import Optional

from src.config import settings


class SpeechToText:
    """Offline-first Speech-to-Text using Whisper."""

    def __init__(self, model_size: str = "base", language_hint: Optional[str] = None):
        self.model_size = model_size
        self._model = None  # Lazy-loaded
        self.language_hint = language_hint or settings.whisper_language_hint

    def transcribe(self, audio_data: bytes) -> str:
        """Transcribe audio to text. Returns empty string on failure."""
        try:
            if self._model is None:
                self._load_model()
            if self._model is None:
                return ""
            import tempfile
            import os

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(audio_data)
                tmp_path = f.name
            try:
                kwargs = {}
                if self.language_hint:
                    kwargs["language"] = self.language_hint
                result = self._model.transcribe(tmp_path, **kwargs)
                return result.get("text", "").strip()
            finally:
                os.unlink(tmp_path)
        except Exception:
            return ""

    def _load_model(self) -> None:
        try:
            import whisper

            self._model = whisper.load_model(self.model_size)
        except ImportError:
            self._model = None  # Whisper not installed — graceful degradation
