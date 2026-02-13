"""
Text-to-Speech — Offline using pyttsx3.

Fails silently if TTS is unavailable.
"""


class TextToSpeech:
    """Offline Text-to-Speech using pyttsx3."""

    def __init__(self):
        self._engine = None

    def speak(self, text: str) -> None:
        """Speak text aloud. Fails silently if TTS unavailable."""
        try:
            if self._engine is None:
                import pyttsx3
                self._engine = pyttsx3.init()
            self._engine.say(text)
            self._engine.runAndWait()
        except Exception:
            pass  # TTS failure is non-critical

    def available(self) -> bool:
        try:
            import pyttsx3
            return True
        except ImportError:
            return False
