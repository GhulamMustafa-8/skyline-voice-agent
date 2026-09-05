"""
Phase 8: Edge case testing across the whole stack (webhook + reasoner +
compliance + state machine guardrails). These are the inputs that don't show
up in a happy-path demo but WILL show up on a real call within the first day.
"""

import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "phase3"))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "phase5"))

import crm
from webhook_server import app

TEST_DB = "test_edge_cases.db"


def fresh_client():
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    crm.init_db(TEST_DB)
    crm.DB_PATH_OVERRIDE = TEST_DB  # not used by webhook_server directly; see note below
    return app.test_client()


def test_empty_speech_result():
    """Twilio sends an empty SpeechResult when it heard silence (dead air,
    caller muted, or caller just didn't say anything). The call must not
    crash or loop forever — it should re-prompt or gracefully end."""
    client = fresh_client()
    call_sid = "CA_silence"
    client.post("/voice", data={"CallSid": call_sid, "From": "+923010000001"})
    resp = client.post("/gather", data={"CallSid": call_sid, "From": "+923010000001", "SpeechResult": ""})
    body = resp.data.decode()
    ok = resp.status_code == 200 and ("<Gather" in body or "<Hangup" in body)
    print(f"{'PASS' if ok else 'FAIL'}: empty speech result handled without crashing (status={resp.status_code})")


def test_gibberish_input():
    """Unrecognizable transcription (noisy line, unrelated background
    speech). Should not crash, and definitely should not silently assign it
    as a valid budget/location/timeline field."""
    client = fresh_client()
    call_sid = "CA_gibberish"
    client.post("/voice", data={"CallSid": call_sid, "From": "+923010000002"})
    client.post("/gather", data={"CallSid": call_sid, "From": "+923010000002", "SpeechResult": "yes speaking"})
    resp = client.post("/gather", data={
        "CallSid": call_sid, "From": "+923010000002",
        "SpeechResult": "asdkjf mumble mumble truck noise wwzzz",
    })
    ok = resp.status_code == 200
    print(f"{'PASS' if ok else 'FAIL'}: gibberish input handled without crashing (status={resp.status_code})")


def test_very_long_rambling_utterance():
    """Callers ramble. A 300-word answer to a yes/no question shouldn't
    break field extraction or blow up the reply."""
    client = fresh_client()
    call_sid = "CA_rambling"
    client.post("/voice", data={"CallSid": call_sid, "From": "+923010000003"})
    long_text = (
        "well actually yes so basically me and my wife have been talking about this "
        "for a few months now and we're not totally sure but we did see a place near "
        "Bahria Town that we liked and honestly the budget is kind of flexible maybe "
        "eighty to ninety lakh depending on financing and we're also considering renting "
        "for a year first before we commit " * 2
    )
    resp = client.post("/gather", data={"CallSid": call_sid, "From": "+923010000003", "SpeechResult": long_text})
    ok = resp.status_code == 200
    print(f"{'PASS' if ok else 'FAIL'}: long rambling utterance handled without crashing (status={resp.status_code})")


def test_repeated_identical_utterance_does_not_infinite_loop():
    """If the caller (or a flaky speech recognizer) sends the exact same
    utterance repeatedly, the call must still terminate within a bounded
    number of turns rather than looping forever."""
    client = fresh_client()
    call_sid = "CA_loop"
    phone = "+923010000004"
    client.post("/voice", data={"CallSid": call_sid, "From": phone})
    max_turns = 25
    turns_taken = 0
    for _ in range(max_turns):
        resp = client.post("/gather", data={"CallSid": call_sid, "From": phone, "SpeechResult": "hmm"})
        turns_taken += 1
        if "<Gather" not in resp.data.decode():
            break
    ok = turns_taken < max_turns
    print(f"{'PASS' if ok else 'FAIL'}: repeated identical input terminated within {turns_taken} turns "
          f"(bound was {max_turns})")


def test_unknown_call_sid_on_gather():
    """Twilio retries or network hiccups can cause a /gather POST for a
    CallSid the server never saw a /voice for (e.g. server restarted mid-call).
    Must fail gracefully, not 500."""
    client = fresh_client()
    resp = client.post("/gather", data={"CallSid": "CA_never_started", "From": "+923010000005", "SpeechResult": "hello"})
    ok = resp.status_code == 200 and "<Hangup" in resp.data.decode()
    print(f"{'PASS' if ok else 'FAIL'}: unknown CallSid handled gracefully (status={resp.status_code})")


def test_code_switched_urdu_english_input():
    """Real Pakistani callers mix Urdu and English mid-sentence. The system
    doesn't need full Urdu NLU for this MVP, but it must not crash on
    non-ASCII text, and this documents it as a known accuracy limitation
    rather than an untested blind spot."""
    client = fresh_client()
    call_sid = "CA_codeswitch"
    client.post("/voice", data={"CallSid": call_sid, "From": "+923010000006"})
    resp = client.post("/gather", data={
        "CallSid": call_sid, "From": "+923010000006",
        "SpeechResult": "ji haan mujhe ek ghar chahiye buy karne ke liye, budget hai around 60 lakh",
    })
    ok = resp.status_code == 200
    print(f"{'PASS' if ok else 'FAIL'}: code-switched Urdu/English input handled without crashing "
          f"(status={resp.status_code}) — NOTE: field extraction accuracy on Urdu text is a known "
          f"limitation of the current keyword-based stub; real deployment should use an LLM with "
          f"multilingual extraction, see README.")


if __name__ == "__main__":
    test_empty_speech_result()
    test_gibberish_input()
    test_very_long_rambling_utterance()
    test_repeated_identical_utterance_does_not_infinite_loop()
    test_unknown_call_sid_on_gather()
    test_code_switched_urdu_english_input()
