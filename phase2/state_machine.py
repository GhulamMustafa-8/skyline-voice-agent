"""
Conversation State Machine for the Real Estate Lead-Gen Voice Agent.

This encodes the flow designed in Phase 1 (scope_and_script.md) as executable
states + transitions. The LLM layer (llm_agent.py) decides WHICH transition to
take based on what the user said; this module just defines what states/
transitions are legal, so the agent can't wander into undefined behavior.
"""

from enum import Enum, auto
from dataclasses import dataclass, field


class State(Enum):
    GREETING = auto()
    CONFIRM_IDENTITY = auto()
    INTENT_CHECK = auto()
    QUALIFICATION = auto()
    OBJECTION_HANDLING = auto()
    SCORING = auto()
    CLOSING = auto()
    FALLBACK_HUMAN = auto()
    END = auto()


@dataclass
class LeadInfo:
    name: str = ""
    buy_or_rent: str = ""
    budget: str = ""
    location: str = ""
    timeline: str = ""
    score: str = ""          # Hot / Warm / Cold
    outcome: str = ""        # e.g. callback_scheduled, not_interested, wrong_number
    objection_count: int = 0


@dataclass
class ConversationContext:
    state: State = State.GREETING
    lead: LeadInfo = field(default_factory=LeadInfo)
    history: list = field(default_factory=list)  # list of (speaker, text)

    def log(self, speaker: str, text: str):
        self.history.append((speaker, text))


def score_lead(lead: LeadInfo) -> str:
    """Rule-based scoring per the table defined in Phase 1."""
    points = 0
    if lead.budget and lead.budget.lower() not in ("", "not sure", "unsure"):
        points += 1
    if lead.timeline.lower() in ("immediate", "1 month", "asap"):
        points += 2
    elif lead.timeline.lower() in ("1-3 months", "few months"):
        points += 1
    if lead.location and lead.location.lower() not in ("", "not sure"):
        points += 1

    if points >= 3:
        return "Hot"
    elif points >= 1:
        return "Warm"
    return "Cold"


# Legal transitions — used to validate that the LLM's chosen next-state is allowed
# from the current state. Prevents the agent from "hallucinating" an illegal jump.
# Note: FALLBACK_HUMAN and END are reachable from almost every state on
# purpose — a frustrated or upset caller needs an immediate exit at ANY point
# in the conversation, not just after passing through OBJECTION_HANDLING.
# Forcing every escalation through one path is what caused the bug this
# transition table originally had (see test_llm_reasoner.py, "Frustrated
# caller" scenario).
ALLOWED_TRANSITIONS = {
    State.GREETING: {State.CONFIRM_IDENTITY, State.END},
    State.CONFIRM_IDENTITY: {State.INTENT_CHECK, State.END},
    State.INTENT_CHECK: {State.QUALIFICATION, State.OBJECTION_HANDLING, State.END, State.FALLBACK_HUMAN},
    State.QUALIFICATION: {State.QUALIFICATION, State.OBJECTION_HANDLING, State.SCORING, State.END, State.FALLBACK_HUMAN},
    State.OBJECTION_HANDLING: {State.QUALIFICATION, State.INTENT_CHECK, State.END, State.FALLBACK_HUMAN},
    State.SCORING: {State.CLOSING},
    State.CLOSING: {State.END},
    State.FALLBACK_HUMAN: {State.END},
    State.END: set(),
}


def can_transition(current: State, target: State) -> bool:
    return target in ALLOWED_TRANSITIONS.get(current, set())
