"""
Call Manager: keeps one VoiceAgentPipeline instance alive per active Twilio
call (keyed by CallSid), since Twilio webhooks are stateless HTTP requests —
each turn of the conversation is a separate POST request, so we need
somewhere to keep the conversation state between requests.

Also handles retry logic for no-answer/busy outcomes, per Phase 1's
compliance notes (respect reasonable hours, don't hammer the same number).
"""

import sys
import os
import time

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "phase2"))
from pipeline import build_local_pipeline  # noqa: E402


class CallManager:
    def __init__(self, max_retries: int = 2, retry_delay_seconds: int = 3600):
        self._active_calls = {}      # call_sid -> VoiceAgentPipeline
        self._retry_counts = {}      # phone_number -> attempts
        self._do_not_call = set()    # phone_number set, permanent opt-outs
        self.max_retries = max_retries
        self.retry_delay_seconds = retry_delay_seconds

    def start_call(self, call_sid: str) -> "VoiceAgentPipeline":
        pipeline = build_local_pipeline()  # swap for real STT/LLM/TTS in production
        self._active_calls[call_sid] = pipeline
        return pipeline

    def get_pipeline(self, call_sid: str):
        return self._active_calls.get(call_sid)

    def end_call(self, call_sid: str):
        self._active_calls.pop(call_sid, None)

    def is_do_not_call(self, phone_number: str) -> bool:
        return phone_number in self._do_not_call

    def mark_do_not_call(self, phone_number: str):
        self._do_not_call.add(phone_number)

    def handle_call_status(self, phone_number: str, status: str) -> dict:
        """
        Called from Twilio's status-callback webhook.
        status: one of 'completed', 'no-answer', 'busy', 'failed'.
        Returns a dict describing what to do next (for logging/scheduling).
        """
        if status == "completed":
            self._retry_counts.pop(phone_number, None)
            return {"action": "none"}

        if self.is_do_not_call(phone_number):
            return {"action": "none", "reason": "do_not_call_list"}

        attempts = self._retry_counts.get(phone_number, 0) + 1
        self._retry_counts[phone_number] = attempts

        if attempts > self.max_retries:
            return {"action": "give_up", "attempts": attempts}

        return {
            "action": "retry",
            "attempts": attempts,
            "retry_after_seconds": self.retry_delay_seconds,
        }


# One shared instance for the Flask app to use
call_manager = CallManager()
