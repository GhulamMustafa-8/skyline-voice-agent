"""
Phase 6: Compliance & Safety.

Three things get enforced here, all pulled forward from the compliance notes
in Phase 1's script design rather than being an afterthought:

1. AI disclosure — already baked into the greeting line since Phase 1
   ("this is an AI assistant calling on behalf of..."). This module doesn't
   need to re-do that; it just documents that it's a hard requirement, not
   an optional script flourish, so nobody "optimizes" it away later.

2. Do-not-call enforcement — checked BEFORE any outbound dial, and updated
   the moment a caller opts out mid-conversation (not just from a separate
   admin action).

3. Calling-hours enforcement — outbound calls are blocked outside a
   configurable allowed window, regardless of what a lead list contains.

This module is deliberately a gate that OTHER code calls through — it holds
no state of its own beyond what's already in the CRM, so there's exactly one
place that decides "are we allowed to call this number right now."
"""

import sys
import os
from datetime import datetime, time as dt_time

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "phase5"))
import crm  # noqa: E402


# Configurable per deployment — default to a conservative 9am-7pm local window.
CALLING_HOURS_START = dt_time(9, 0)
CALLING_HOURS_END = dt_time(19, 0)

OPT_OUT_PHRASES = [
    "don't call me again", "do not call me again", "stop calling",
    "remove me from your list", "take me off your list", "never call me again",
]


class ComplianceBlock(Exception):
    """Raised when an outbound call is blocked by a compliance rule."""
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


def is_within_calling_hours(now: datetime = None) -> bool:
    now = now or datetime.now()
    return CALLING_HOURS_START <= now.time() <= CALLING_HOURS_END


def check_can_call(phone_number: str, now: datetime = None, db_path: str = crm.DB_PATH) -> None:
    """Raises ComplianceBlock if this number should NOT be called right now.
    Call this immediately before every outbound dial — no exceptions."""
    if crm.is_do_not_call(phone_number, db_path=db_path):
        raise ComplianceBlock(f"{phone_number} is on the do-not-call list")

    if not is_within_calling_hours(now):
        raise ComplianceBlock(
            f"Current time is outside allowed calling hours "
            f"({CALLING_HOURS_START}–{CALLING_HOURS_END})"
        )


def detect_opt_out(user_utterance: str) -> bool:
    """Checks the caller's utterance for an explicit opt-out request.
    Distinct from a plain 'not interested' — this specifically means
    'don't contact me again', which must be honored permanently."""
    text = user_utterance.lower()
    return any(phrase in text for phrase in OPT_OUT_PHRASES)


def handle_utterance_for_compliance(phone_number: str, user_utterance: str, db_path: str = crm.DB_PATH) -> bool:
    """Call this on every turn of a live conversation. If the caller opts out,
    marks it permanently in the CRM and returns True (caller code should end
    the call gracefully). Returns False otherwise."""
    if detect_opt_out(user_utterance):
        crm.mark_do_not_call(phone_number, db_path=db_path)
        return True
    return False


def log_consent(phone_number: str, disclosed_ai: bool, db_path: str = crm.DB_PATH) -> None:
    """
    Real deployments should keep an explicit, timestamped audit record that
    the AI-disclosure line was actually spoken on a given call (not just
    that the script contains it). For this project's scope, the call_logs
    transcript already captures the full utterance sequence including the
    disclosure line, which serves as that record — this function is a named
    hook so a dedicated consent table is a one-line addition if a real
    deployment needs stronger audit guarantees than "read it from the transcript."
    """
    pass
