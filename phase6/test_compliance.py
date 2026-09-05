import sys
import os
from datetime import datetime

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "phase5"))
import crm
from compliance import check_can_call, ComplianceBlock, handle_utterance_for_compliance, is_within_calling_hours

TEST_DB = "test_compliance.db"


def reset_db():
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    crm.init_db(TEST_DB)


def test_do_not_call_blocks_dialing():
    reset_db()
    phone = "+923001111111"
    crm.mark_do_not_call(phone, db_path=TEST_DB)
    try:
        check_can_call(phone, now=datetime(2026, 1, 1, 12, 0), db_path=TEST_DB)
        print("FAIL: expected ComplianceBlock for do-not-call number")
    except ComplianceBlock as e:
        print(f"PASS: blocked as expected -> {e.reason}")


def test_calling_hours_block():
    reset_db()
    phone = "+923002222222"
    try:
        # 10pm — outside the 9am-7pm window
        check_can_call(phone, now=datetime(2026, 1, 1, 22, 0), db_path=TEST_DB)
        print("FAIL: expected ComplianceBlock for late-night call")
    except ComplianceBlock as e:
        print(f"PASS: blocked as expected -> {e.reason}")


def test_allowed_call_goes_through():
    reset_db()
    phone = "+923003333333"
    try:
        check_can_call(phone, now=datetime(2026, 1, 1, 14, 0), db_path=TEST_DB)
        print("PASS: call allowed during business hours for a number not on the DNC list")
    except ComplianceBlock as e:
        print(f"FAIL: unexpected block -> {e.reason}")


def test_mid_call_opt_out_marks_dnc():
    reset_db()
    phone = "+923004444444"
    opted_out = handle_utterance_for_compliance(phone, "please don't call me again", db_path=TEST_DB)
    print(f"opt-out detected this turn: {opted_out}")
    is_blocked_now = crm.is_do_not_call(phone, db_path=TEST_DB)
    print(f"PASS: now on DNC list -> {is_blocked_now}" if is_blocked_now else "FAIL: not marked DNC")

    # A future call attempt should now be blocked
    try:
        check_can_call(phone, now=datetime(2026, 1, 1, 14, 0), db_path=TEST_DB)
        print("FAIL: should have been blocked after opt-out")
    except ComplianceBlock as e:
        print(f"PASS: future call correctly blocked -> {e.reason}")


def test_plain_not_interested_does_not_trigger_dnc():
    """'not interested' alone shouldn't permanently blacklist — only an
    explicit 'don't contact me again' should. Distinguishing these matters:
    a cold lead today might be a warm one in six months."""
    reset_db()
    phone = "+923005555555"
    opted_out = handle_utterance_for_compliance(phone, "not interested right now, maybe later", db_path=TEST_DB)
    is_blocked = crm.is_do_not_call(phone, db_path=TEST_DB)
    if not opted_out and not is_blocked:
        print("PASS: plain 'not interested' did not trigger permanent DNC")
    else:
        print("FAIL: 'not interested' incorrectly triggered DNC")


if __name__ == "__main__":
    test_do_not_call_blocks_dialing()
    test_calling_hours_block()
    test_allowed_call_goes_through()
    test_mid_call_opt_out_marks_dnc()
    test_plain_not_interested_does_not_trigger_dnc()
