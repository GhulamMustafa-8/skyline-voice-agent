"""
Runs a handful of simulated calls through the Phase 4 reasoner and logs each
one into the Phase 5 CRM — verifying leads get upserted, call_logs get
written, and the dashboard aggregation query returns sensible numbers.
"""

import sys
import os
from datetime import datetime, timezone

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "phase2"))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "phase4"))

from state_machine import ConversationContext, State, can_transition, score_lead
from llm_reasoner import LLMReasoner
from mock_anthropic_client import MockAnthropicClient
import crm

TEST_DB = "test_crm.db"
AUTO_STATES = {State.SCORING, State.CLOSING}


def run_and_log_call(call_sid, phone_number, user_turns):
    ctx = ConversationContext()
    reasoner = LLMReasoner(client=MockAnthropicClient())
    started_at = datetime.now(timezone.utc).isoformat()

    decision = reasoner.decide(ctx, "")
    ctx.state = decision.next_state

    for turn in user_turns:
        decision = reasoner.decide(ctx, turn)
        if not (can_transition(ctx.state, decision.next_state) or decision.next_state == ctx.state):
            break
        for k, v in decision.extracted.items():
            if hasattr(ctx.lead, k):
                setattr(ctx.lead, k, v)
        ctx.state = decision.next_state

        # Auto-advance through states that don't need new caller input
        safety_limit = 5
        while ctx.state in AUTO_STATES and safety_limit > 0:
            if ctx.state == State.SCORING:
                ctx.lead.score = score_lead(ctx.lead)
            next_decision = reasoner.decide(ctx, "")
            ctx.state = next_decision.next_state
            safety_limit -= 1

        if ctx.state in (State.END, State.FALLBACK_HUMAN):
            ctx.lead.outcome = ctx.lead.outcome or ctx.state.name.lower()
            break

    ended_at = datetime.now(timezone.utc).isoformat()
    crm.upsert_lead(phone_number, ctx.lead, db_path=TEST_DB)
    crm.log_call(
        call_sid=call_sid, phone_number=phone_number, started_at=started_at,
        ended_at=ended_at, final_state=ctx.state.name, score=ctx.lead.score,
        outcome=ctx.lead.outcome, objection_count=ctx.lead.objection_count,
        transcript=ctx.history, db_path=TEST_DB,
    )
    print(f"Logged call {call_sid} for {phone_number}: state={ctx.state.name}, "
          f"score={ctx.lead.score}, outcome={ctx.lead.outcome}")


if __name__ == "__main__":
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    crm.init_db(TEST_DB)

    run_and_log_call("CA001", "+923001234567", [
        "yes speaking", "still looking", "I want to buy",
        "budget around 80 lakh", "Bahria Town", "immediate, this month",
    ])
    run_and_log_call("CA002", "+923007654321", [
        "yes that's me", "not interested",
    ])
    run_and_log_call("CA003", "+923009999999", [
        "yes speaking", "still looking", "too expensive honestly",
        "let me think about it, call later",
    ])
    run_and_log_call("CA004", "+923005555555", [
        "yes speaking", "still looking", "I want to rent",
        "around 40k per month", "Clifton", "just exploring for now",
    ])

    print("\n--- Dashboard stats ---")
    stats = crm.get_dashboard_stats(TEST_DB)
    for k, v in stats.items():
        print(f"{k}: {v}")

    print("\n--- Leads table ---")
    with crm.get_conn(TEST_DB) as conn:
        for row in conn.execute("SELECT phone_number, buy_or_rent, budget, location, score, last_outcome FROM leads"):
            print(dict(row))
