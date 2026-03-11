"""
Text-to-Speech — Offline using pyttsx3.

Fails silently if TTS is unavailable.
"""

from typing import Optional

from src.config import settings


class TextToSpeech:
    """Offline Text-to-Speech using pyttsx3."""

    def __init__(self, preferred_language: Optional[str] = None):
        self._engine = None
        self.language = preferred_language or settings.voice_primary_language

    def speak(self, text: str, language: Optional[str] = None) -> None:
        """Speak text aloud. Fails silently if TTS unavailable."""
        try:
            if self._engine is None:
                import pyttsx3

                self._engine = pyttsx3.init()
                self._apply_voice(language or self.language)
            elif language and language != self.language:
                self._apply_voice(language)
            self._engine.say(text)
            self._engine.runAndWait()
        except Exception:
            pass  # TTS failure is non-critical

    def available(self) -> bool:
        try:
            import pyttsx3  # noqa: F401

            return True
        except ImportError:
            return False

    def _apply_voice(self, language: str) -> None:
        """Select pyttsx3 voice matching the requested language."""
        if not self._engine:
            return
        target_voice = settings.tts_voice_ids.get(language)
        if not target_voice:
            return
        try:
            for voice in self._engine.getProperty("voices"):
                if target_voice.lower() in voice.name.lower():
                    self._engine.setProperty("voice", voice.id)
                    self.language = language
                    return
        except Exception:
            pass
