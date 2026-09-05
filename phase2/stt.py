"""
Speech-to-Text wrapper.

Pluggable interface so the pipeline doesn't care whether you're using
Deepgram, Whisper API, or a local Whisper model.

TextStub is used for local testing (text in -> text out, no audio needed).
DeepgramSTT is the real slot to fill in with your API key later.
"""

from abc import ABC, abstractmethod


class STT(ABC):
    @abstractmethod
    def transcribe(self, audio_chunk: bytes) -> str:
        ...


class TextStub(STT):
    """For local testing: pretend transcription just returns typed text.
    Lets us test the full pipeline logic without a microphone or API key."""
    def transcribe(self, audio_chunk: bytes) -> str:
        return audio_chunk.decode("utf-8") if isinstance(audio_chunk, bytes) else str(audio_chunk)


class DeepgramSTT(STT):
    """
    Real implementation slot.

        from deepgram import DeepgramClient
        client = DeepgramClient(api_key=DEEPGRAM_API_KEY)
        # use streaming websocket for real-time, not batch transcribe,
        # or latency will be too high for a live phone call.

    Real-time streaming (not request/response per utterance) is what keeps
    latency low enough that the call doesn't feel robotic.
    """
    def __init__(self, api_key: str):
        self.api_key = api_key

    def transcribe(self, audio_chunk: bytes) -> str:
        raise NotImplementedError("Plug in Deepgram streaming client here (needs API key + network).")
