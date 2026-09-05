"""
Verifies llm_reasoner.py's plumbing (prompt building, tool-call parsing,
objection counting, sentiment handling) using the mock client — no real API
key needed.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "phase2"))

from state_machine import ConversationContext, State, can_transition
from llm_reasoner import LLMReasoner
from mock_anthropic_client import MockAnthropicClient


def run_conversation(name, user_turns):
    print(f"\n=== Conversation: {name} ===")
    ctx = ConversationContext()
    reasoner = LLMReasoner(client=MockAnthropicClient())

    # kick off greeting
    decision = reasoner.decide(ctx, "")
    print(f"[AGENT]: {decision.reply_text}")
    assert can_transition(ctx.state, decision.next_state), "illegal transition!"
    ctx.state = decision.next_state

    for turn in user_turns:
        print(f"[USER]: {turn}")
        decision = reasoner.decide(ctx, turn)
        assert can_transition(ctx.state, decision.next_state) or decision.next_state == ctx.state, \
            f"illegal transition {ctx.state} -> {decision.next_state}"
        for k, v in decision.extracted.items():
            if hasattr(ctx.lead, k):
                setattr(ctx.lead, k, v)
        ctx.state = decision.next_state
        print(f"[AGENT]: {decision.reply_text}  (sentiment={decision.sentiment}, "
              f"objection={decision.objection_detected}, objection_count={ctx.lead.objection_count})")
        if ctx.state in (State.END, State.FALLBACK_HUMAN):
            break

    print(f"--- Final state: {ctx.state.name} | Lead: {ctx.lead} ---")


if __name__ == "__main__":
    # Scenario 1: normal hot lead, no objections
    run_conversation("Hot Lead (no objections)", [
        "yes speaking",
        "still looking actually",
        "I want to buy",
        "budget around 80 lakh",
        "Bahria Town",
    ])

    # Scenario 2: repeated objections should escalate to a human
    run_conversation("Escalates after repeated objections", [
        "yes speaking",
        "still looking",
        "honestly it's too expensive for me right now",
        "I need to think about it, call me later maybe",
    ])

    # Scenario 3: caller gets frustrated -> immediate handoff, no more pushing
    run_conversation("Frustrated caller", [
        "yes that's me",
        "I already told you I'm not interested, stop calling me, this is annoying",
    ])
