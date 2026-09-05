import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "phase3"))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "phase5"))

import crm
from webhook_server import app

TEST_DB_NOTE = "Uses phase5/crm.db (default path) since webhook_server imports crm directly."


def test_mid_call_opt_out_ends_call_and_marks_dnc():
    client = app.test_client()
    call_sid = "CA_optout_test"
    phone = "+923008888888"

    resp = client.post("/voice", data={"CallSid": call_sid, "From": phone})
    print("Greeting:", "<Gather" in resp.data.decode())

    resp = client.post("/gather", data={
        "CallSid": call_sid, "From": phone, "SpeechResult": "please don't call me again"
    })
    body = resp.data.decode()
    print(body)
    ended_call = "<Gather" not in body and "<Hangup" in body
    is_dnc = crm.is_do_not_call(phone)
    print(f"PASS: call ended immediately and {phone} marked do-not-call" if (ended_call and is_dnc)
          else f"FAIL: ended_call={ended_call}, is_dnc={is_dnc}")


def test_outbound_call_blocked_for_dnc_number():
    client = app.test_client()
    phone = "+923008888888"  # already marked DNC by the previous test
    resp = client.post("/outbound-call", data={"to": phone})
    print("outbound-call response:", resp.status_code, resp.get_json())
    if resp.status_code == 403:
        print("PASS: outbound dial correctly blocked for DNC number")
    else:
        print("FAIL: expected 403 block")


if __name__ == "__main__":
    crm.init_db()  # ensure schema exists in the default crm.db before first use
    test_mid_call_opt_out_ends_call_and_marks_dnc()
    test_outbound_call_blocked_for_dnc_number()
