"""
LLM reasoning layer.

Responsibility: given the current state, conversation history, and the user's
latest utterance, decide:
  1. What the agent should SAY next (natural language)
  2. What STATE the conversation should move to
  3. Any structured fields extracted from the user's utterance (budget, timeline, etc.)

This is deliberately pluggable:
  - `StubReasoner` is a rule-based/keyword-matching fake, used for local testing
    of the pipeline without needing an API key or network.
  - `LLMReasoner` is the real implementation slot — swap in an Anthropic/OpenAI
    call here once you have API keys and are running outside this sandbox.

Keeping these behind the same interface (`Reasoner.decide(...)`) means the rest
of the pipeline never needs to change when you swap stub -> real LLM.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from state_machine import State, ConversationContext, can_transition


@dataclass
class Decision:
    reply_text: str
    next_state: State
    extracted: dict  # e.g. {"budget": "50 lakh"} to merge into LeadInfo


class Reasoner(ABC):
    @abstractmethod
    def decide(self, ctx: ConversationContext, user_utterance: str) -> Decision:
        ...


class StubReasoner(Reasoner):
    """Rule-based reasoner for local testing — no API calls, fully offline."""

    def decide(self, ctx: ConversationContext, user_utterance: str) -> Decision:
        text = user_utterance.lower()
        state = ctx.state

        if state == State.GREETING:
            return Decision(
                "Hi, this is an AI assistant calling on behalf of Skyline Realty. "
                "Am I speaking with the right person?",
                State.CONFIRM_IDENTITY, {}
            )

        if state == State.CONFIRM_IDENTITY:
            if any(w in text for w in ["no", "wrong"]):
                return Decision("Apologies for the confusion, have a good day!", State.END, {})
            return Decision(
                "Great — you'd enquired about properties a while back. Still looking?",
                State.INTENT_CHECK, {}
            )

        if state == State.INTENT_CHECK:
            if any(w in text for w in ["not interested", "no thanks", "stop"]):
                return Decision(
                    "Understood, thanks for your time. We won't reach out again.",
                    State.END, {"outcome": "not_interested"}
                )
            if any(w in text for w in ["busy", "later", "call back"]):
                return Decision(
                    "No problem — when's a better time to call back?",
                    State.END, {"outcome": "callback_scheduled"}
                )
            return Decision(
                "Great! Are you looking to buy or rent?",
                State.QUALIFICATION, {}
            )

        if state == State.QUALIFICATION:
            extracted = {}
            if "buy" in text or "rent" in text:
                extracted["buy_or_rent"] = "buy" if "buy" in text else "rent"
                reply = "Got it. What's your budget range?"
            elif any(ch.isdigit() for ch in text) or "lakh" in text or "budget" in text:
                extracted["budget"] = user_utterance
                reply = "Understood. Which area are you focused on?"
            elif "area" in text or "location" in text or ctx.lead.location == "":
                extracted["location"] = user_utterance
                reply = "And what's your timeline — immediate, 1-3 months, or just exploring?"
            else:
                extracted["timeline"] = user_utterance
                return Decision("Thanks, let me check that for you.", State.SCORING, extracted)
            return Decision(reply, State.QUALIFICATION, extracted)

        if state == State.SCORING:
            return Decision("", State.CLOSING, {})

        return Decision("Thanks for your time, goodbye!", State.END, {})


class LLMReasoner(Reasoner):
    """
    Real implementation slot. Fill this in once you have API access:

        response = anthropic_client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=300,
            system=SYSTEM_PROMPT_WITH_STATE_MACHINE_RULES,
            messages=[...ctx.history..., {"role": "user", "content": user_utterance}],
            tools=[TRANSITION_TOOL, EXTRACT_FIELDS_TOOL],  # function calling
        )
        # parse tool_use blocks into a Decision(...)

    Using function calling here (not free-text parsing) is important — it's what
    makes the "next_state" decision structured/reliable instead of regex-guessing
    from prose.
    """
    def decide(self, ctx: ConversationContext, user_utterance: str) -> Decision:
        raise NotImplementedError("Plug in real LLM API call here (needs API key + network).")
