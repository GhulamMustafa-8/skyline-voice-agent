"""
Text-to-Speech wrapper. Same pluggable pattern as stt.py.
"""

from abc import ABC, abstractmethod


class TTS(ABC):
    @abstractmethod
    def speak(self, text: str) -> bytes:
        ...


class TextStub(TTS):
    """For local testing: just prints what the agent 'says' instead of
    generating real audio."""
    def speak(self, text: str) -> bytes:
        print(f"[AGENT VOICE]: {text}")
        return b""


class ElevenLabsTTS(TTS):
    """
    Real implementation slot.

        from elevenlabs import generate
        audio = generate(text=text, voice=VOICE_ID, api_key=ELEVENLABS_API_KEY)

    Use streaming generation (not full-clip generation) once on real calls,
    so the agent starts speaking before the whole sentence is synthesized.
    """
    def __init__(self, api_key: str, voice_id: str):
        self.api_key = api_key
        self.voice_id = voice_id

    def speak(self, text: str) -> bytes:
        raise NotImplementedError("Plug in ElevenLabs client here (needs API key + network).")
