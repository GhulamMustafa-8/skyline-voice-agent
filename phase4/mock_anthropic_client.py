"""
Mock Anthropic client for offline testing of llm_reasoner.py's plumbing.

This is NOT meant to simulate real LLM intelligence — it's a slightly smarter
rule engine than Phase 2's stub, just good enough to exercise every branch of
LLMReasoner.decide() (tool-call parsing, objection counting, sentiment field,
extracted fields) so you can verify the surrounding code is correct before
spending real API calls on it.

Swap `client=MockAnthropicClient()` for `client=anthropic.Anthropic(api_key=...)`
once you're running this outside the sandbox with real credentials.
"""

import re
from state_machine import State


class _FakeToolUseBlock(dict):
    pass


class _FakeResponse:
    def __init__(self, content):
        self.content = content


class _FakeMessages:
    def create(self, model, max_tokens, system, messages, tools, tool_choice):
        user_text = messages[-1]["content"].lower()
        current_state = re.search(r"Current conversation state: (\w+)", system).group(1)
        objection_count = int(re.search(r"Objections raised so far: (\d+)", system).group(1))
        lead_match = re.search(r"Lead info so far: (LeadInfo\(.*?\))", system)
        lead_str = lead_match.group(1) if lead_match else ""

        args = self._decide(State[current_state], user_text, objection_count, lead_str)
        block = _FakeToolUseBlock(type="tool_use", name="make_decision", input=args)
        return _FakeResponse(content=[block])

    def _field_filled(self, lead_str, field_name):
        m = re.search(rf"{field_name}='([^']*)'", lead_str)
        return bool(m and m.group(1))

    def _decide(self, state, text, objection_count, lead_str=""):
        objection_words = ["expensive", "too high", "not sure", "think about it", "call me later"]
        frustrated_words = ["stop calling", "annoying", "leave me alone", "already told you"]

        is_objection = any(w in text for w in objection_words)
        is_frustrated = any(w in text for w in frustrated_words)
        sentiment = "frustrated" if is_frustrated else ("negative" if is_objection else "neutral")

        if is_frustrated or (is_objection and objection_count >= 1):
            return {
                "reply_text": "I understand — let me connect you with one of our specialists directly.",
                "next_state": "FALLBACK_HUMAN",
                "extracted": {},
                "sentiment": sentiment,
                "objection_detected": is_objection,
            }

        if state == State.GREETING:
            return {"reply_text": "Hi, this is an AI assistant from Skyline Realty — am I speaking with the right person?",
                    "next_state": "CONFIRM_IDENTITY", "extracted": {}, "sentiment": "neutral", "objection_detected": False}

        if state == State.CONFIRM_IDENTITY:
            return {"reply_text": "Great — you'd enquired about properties before. Still looking?",
                    "next_state": "INTENT_CHECK", "extracted": {}, "sentiment": "neutral", "objection_detected": False}

        if state == State.INTENT_CHECK:
            if "not interested" in text:
                return {"reply_text": "Understood, thanks for your time.", "next_state": "END",
                        "extracted": {}, "sentiment": "negative", "objection_detected": False}
            return {"reply_text": "Great! Are you looking to buy or rent?", "next_state": "QUALIFICATION",
                    "extracted": {}, "sentiment": "positive", "objection_detected": False}

        if state == State.QUALIFICATION:
            extracted = {}
            has_buy_or_rent = self._field_filled(lead_str, "buy_or_rent")
            has_budget = self._field_filled(lead_str, "budget")
            has_location = self._field_filled(lead_str, "location")

            if not has_buy_or_rent and ("buy" in text or "rent" in text):
                extracted["buy_or_rent"] = "buy" if "buy" in text else "rent"
                return {"reply_text": "Got it. What's your budget range?", "next_state": "QUALIFICATION",
                        "extracted": extracted, "sentiment": "neutral", "objection_detected": False}

            if is_objection and not has_budget:
                return {"reply_text": "No pressure at all — what budget were you hoping to stay within?",
                        "next_state": "OBJECTION_HANDLING", "extracted": {}, "sentiment": sentiment,
                        "objection_detected": True}

            if not has_budget:
                extracted["budget"] = text
                return {"reply_text": "Which area are you focused on?", "next_state": "QUALIFICATION",
                        "extracted": extracted, "sentiment": "neutral", "objection_detected": False}

            if not has_location:
                extracted["location"] = text
                return {"reply_text": "And what's your timeline — immediate, a few months, or just exploring?",
                        "next_state": "QUALIFICATION", "extracted": extracted, "sentiment": "neutral",
                        "objection_detected": False}

            # buy_or_rent, budget, and location are all filled — this turn is the timeline answer
            extracted["timeline"] = text
            return {"reply_text": "Thanks, let me check that for you.", "next_state": "SCORING",
                    "extracted": extracted, "sentiment": "neutral", "objection_detected": False}

        if state == State.OBJECTION_HANDLING:
            return {"reply_text": "Understood — let's continue. Which area are you focused on?",
                    "next_state": "QUALIFICATION", "extracted": {}, "sentiment": "neutral", "objection_detected": False}

        if state == State.SCORING:
            return {"reply_text": "", "next_state": "CLOSING", "extracted": {},
                    "sentiment": "neutral", "objection_detected": False}

        if state == State.CLOSING:
            return {"reply_text": "Great, I'll get one of our consultants to follow up with you shortly. Thanks for your time!",
                    "next_state": "END", "extracted": {}, "sentiment": "neutral", "objection_detected": False}

        return {"reply_text": "Thanks for your time, goodbye!", "next_state": "END",
                "extracted": {}, "sentiment": "neutral", "objection_detected": False}


class MockAnthropicClient:
    def __init__(self):
        self.messages = _FakeMessages()
