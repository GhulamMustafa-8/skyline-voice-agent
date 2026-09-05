"""
Simulates the sequence of HTTP requests Twilio would send during a real call,
using Flask's test client — no real phone call, no Twilio account needed.
"""

from webhook_server import app


def simulate_call(call_sid, user_turns):
    client = app.test_client()
    print(f"\n=== Simulated call: {call_sid} ===")

    resp = client.post("/voice", data={"CallSid": call_sid})
    print("Twilio -> /voice")
    print(resp.data.decode())

    for turn in user_turns:
        print(f"\n[Caller says]: {turn}")
        resp = client.post("/gather", data={"CallSid": call_sid, "SpeechResult": turn})
        body = resp.data.decode()
        print(body)
        # Only stop if the call actually ended (no <Gather> means no more listening)
        if "<Gather" not in body:
            break


if __name__ == "__main__":
    simulate_call("CA_hotlead001", [
        "yes speaking",
        "yeah still looking actually",
        "I want to buy",
        "budget is around 80 lakh",
        "focused on Bahria Town",
        "immediate, this month",
    ])

    simulate_call("CA_notinterested001", [
        "yes that's me",
        "not interested, please stop calling",
    ])
