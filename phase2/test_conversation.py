"""
Simulates full conversations through the pipeline to verify the state machine
+ reasoning + scoring logic all work together correctly, offline.
"""

from pipeline import build_local_pipeline


def run_conversation(name, user_turns):
    print(f"\n=== Conversation: {name} ===")
    pipeline = build_local_pipeline()
    pipeline.step(b"")  # kick off greeting (agent speaks first, no user input yet)

    for turn in user_turns:
        print(f"[USER]: {turn}")
        pipeline.step(turn.encode("utf-8"))
        if pipeline.is_done():
            break

    print(f"--- Final state: {pipeline.ctx.state.name} ---")
    print(f"--- Lead info: {pipeline.ctx.lead} ---")


if __name__ == "__main__":
    # Scenario 1: a hot lead who goes all the way through qualification
    run_conversation("Hot Lead", [
        "yes speaking",
        "yeah still looking actually",
        "I want to buy",
        "budget is around 80 lakh",
        "DHA Phase 6",
        "immediate, want to move in this month",
    ])

    # Scenario 2: not interested, should end early
    run_conversation("Not Interested", [
        "yes that's me",
        "not interested anymore, please stop calling",
    ])

    # Scenario 3: wrong number, should end immediately
    run_conversation("Wrong Number", [
        "no wrong number sorry",
    ])
