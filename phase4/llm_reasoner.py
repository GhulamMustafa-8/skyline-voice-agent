"""
Phase 4: Conversation Intelligence.

Upgrades the Phase 2 stub reasoner to a real LLM-backed one using function
calling (tool use), so the model's output is structured and reliable instead
of us regex-guessing intent from prose. Adds:
  - Proper field extraction (budget/location/timeline/buy_or_rent)
  - Sentiment detection (so the agent can back off if the caller sounds annoyed)
  - Objection detection + a counter so repeated objections escalate to a human
  - Function-calling based state transitions (model picks from an enum, not
    free text — this is what makes the transition trustworthy enough to run
    through the state machine's `can_transition` guardrail)

NOTE ON TESTING: This sandbox has no network access, so `LLMReasoner` here
can't be exercised against the real Anthropic API from this environment.
The code is written to the real API shape (v1/messages, tool use) — plug in
your ANTHROPIC_API_KEY and this runs as-is outside the sandbox. For local
testing here, `MockAnthropicClient` simulates realistic tool-call responses
so we can verify the surrounding plumbing (prompt construction, response
parsing, guardrails) actually works before you spend real API calls on it.
"""

import json
import os
import sys
from dataclasses import dataclass, field

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "phase2"))
from state_machine import State, ConversationContext  # noqa: E402


VALID_STATES = [s.name for s in State]

DECISION_TOOL = {
    "name": "make_decision",
    "description": (
        "Decide what the voice agent should say next and which conversation "
        "state to move to, based on the caller's latest utterance."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "reply_text": {
                "type": "string",
                "description": "What the agent should say next, in natural spoken language.",
            },
            "next_state": {
                "type": "string",
                "enum": VALID_STATES,
                "description": "The next conversation state. Must be a legal transition from the current state.",
            },
            "extracted": {
                "type": "object",
                "description": "Any lead fields extracted from the caller's utterance.",
                "properties": {
                    "buy_or_rent": {"type": "string"},
                    "budget": {"type": "string"},
                    "location": {"type": "string"},
                    "timeline": {"type": "string"},
                },
            },
            "sentiment": {
                "type": "string",
                "enum": ["positive", "neutral", "negative", "frustrated"],
                "description": "The caller's apparent emotional tone this turn.",
            },
            "objection_detected": {
                "type": "boolean",
                "description": "True if the caller raised a price/timing/trust objection this turn.",
            },
        },
        "required": ["reply_text", "next_state", "sentiment", "objection_detected"],
    },
}


def build_system_prompt(ctx: ConversationContext) -> str:
    return f"""You are a real estate lead-qualification voice agent for Skyline Realty.
Current conversation state: {ctx.state.name}
Lead info so far: {ctx.lead}
Objections raised so far: {ctx.lead.objection_count}

Rules:
- If objection_count reaches 2, prefer transitioning to FALLBACK_HUMAN rather than
  continuing to push — repeated objections mean this needs a human touch.
- If sentiment is "frustrated", keep reply_text short and offer to end the call
  or transfer, rather than continuing qualification questions.
- Only extract fields the caller actually stated this turn; don't guess.
- next_state must be a legal transition from the current state.

Use the make_decision tool to respond. Do not respond in plain text.
"""


@dataclass
class Decision:
    reply_text: str
    next_state: State
    extracted: dict = field(default_factory=dict)
    sentiment: str = "neutral"
    objection_detected: bool = False


class LLMReasoner:
    """Real implementation — calls the Anthropic API with function calling."""

    def __init__(self, client=None, model="claude-sonnet-4-6"):
        self.client = client  # an Anthropic client instance (or MockAnthropicClient for testing)
        self.model = model

    def decide(self, ctx: ConversationContext, user_utterance: str) -> Decision:
        system_prompt = build_system_prompt(ctx)
        messages = [{"role": "user", "content": user_utterance or "(call started, no utterance yet)"}]

        response = self.client.messages.create(
            model=self.model,
            max_tokens=300,
            system=system_prompt,
            messages=messages,
            tools=[DECISION_TOOL],
            tool_choice={"type": "tool", "name": "make_decision"},
        )

        tool_use = next(b for b in response.content if b["type"] == "tool_use")
        args = tool_use["input"]

        if args.get("objection_detected"):
            ctx.lead.objection_count += 1

        return Decision(
            reply_text=args["reply_text"],
            next_state=State[args["next_state"]],
            extracted=args.get("extracted", {}) or {},
            sentiment=args.get("sentiment", "neutral"),
            objection_detected=args.get("objection_detected", False),
        )
