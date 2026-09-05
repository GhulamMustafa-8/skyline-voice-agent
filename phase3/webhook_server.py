"""
Flask webhook server — this is the HTTP endpoint Twilio hits during a call.

Flow:
  1. Twilio dials a number, call connects -> Twilio POSTs to /voice
  2. We start a pipeline for this CallSid, run the GREETING state, respond
     with TwiML: agent speaks + <Gather> listens for the caller's reply
  3. Twilio transcribes the caller's speech itself (SpeechResult) and POSTs
     to /gather -> we feed that text into the reasoner, get the next line +
     state, respond with more TwiML (gather again, hang up, or transfer)
  4. Repeat step 3 until state == END or FALLBACK_HUMAN
  5. Twilio POSTs call status changes (no-answer, completed, etc) to
     /call-status -> call_manager decides whether to retry

Note: this uses Twilio's own speech recognition (SpeechResult) rather than
our Deepgram STT wrapper from Phase 2 — simplest path to a working MVP.
Swapping in Deepgram + <Stream> for lower-latency, more accurate recognition
is a natural upgrade once this base flow is proven end-to-end.
"""

from flask import Flask, request, Response
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "phase2"))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "phase5"))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "phase6"))
from state_machine import State, can_transition, score_lead  # noqa: E402
from llm_agent import StubReasoner  # noqa: E402
from call_manager import call_manager  # noqa: E402
from twiml_helpers import say_and_gather, say_and_hangup, redirect_to_human  # noqa: E402
import crm  # noqa: E402
from compliance import check_can_call, ComplianceBlock, handle_utterance_for_compliance  # noqa: E402

app = Flask(__name__)
reasoner = StubReasoner()  # swap for LLMReasoner() once real API access is wired up

TRANSFER_NUMBER = "+92XXXXXXXXXX"  # human sales agent's number, set via env var in production


# States the reasoner can pass through without needing new user speech —
# e.g. SCORING is a pure computation step, CLOSING immediately follows it.
# We loop through these automatically so one user utterance can trigger a
# multi-step chain of reasoning without waiting on the caller.
AUTO_STATES = {State.SCORING, State.CLOSING}


def _advance(pipeline, call_sid, user_text, action_url):
    """Runs reasoning steps (looping through any auto-states) and returns
    the TwiML string to send back."""
    ctx = pipeline.ctx
    ctx.log("user", user_text)
    decision = reasoner.decide(ctx, user_text)

    if not can_transition(ctx.state, decision.next_state) and decision.next_state != ctx.state:
        # Guardrail tripped — don't let a bad decision break the call.
        # Fail safe: end the call politely rather than loop or crash.
        call_manager.end_call(call_sid)
        return say_and_hangup("Sorry, something went wrong on our end. We'll follow up another time.")

    for k, v in decision.extracted.items():
        if hasattr(ctx.lead, k):
            setattr(ctx.lead, k, v)

    ctx.state = decision.next_state
    reply_text = decision.reply_text

    # Chain through automatic states (no caller input needed) until we hit
    # a state that requires listening again, or a terminal state.
    safety_limit = 5
    while ctx.state in AUTO_STATES and safety_limit > 0:
        if ctx.state == State.SCORING:
            ctx.lead.score = score_lead(ctx.lead)
        next_decision = reasoner.decide(ctx, "")
        ctx.state = next_decision.next_state
        reply_text = next_decision.reply_text or reply_text
        safety_limit -= 1

    if ctx.state == State.END:
        call_manager.end_call(call_sid)
        return say_and_hangup(reply_text or "Thanks for your time, goodbye!")

    if ctx.state == State.FALLBACK_HUMAN:
        call_manager.end_call(call_sid)
        return redirect_to_human(reply_text or "Let me connect you with a specialist.", TRANSFER_NUMBER)

    return say_and_gather(reply_text, action_url)


@app.route("/voice", methods=["POST"])
def voice():
    call_sid = request.form.get("CallSid", "unknown")
    pipeline = call_manager.start_call(call_sid)
    twiml = _advance(pipeline, call_sid, "", action_url="/gather")
    return Response(twiml, mimetype="text/xml")


@app.route("/gather", methods=["POST"])
def gather():
    call_sid = request.form.get("CallSid", "unknown")
    speech_result = request.form.get("SpeechResult", "")
    phone_number = request.form.get("From", "")
    pipeline = call_manager.get_pipeline(call_sid)
    if pipeline is None:
        return Response(say_and_hangup("Sorry, we lost track of this call. Goodbye."), mimetype="text/xml")

    # Compliance check runs on every turn, before the reasoner even sees the
    # utterance — an explicit opt-out ends the call immediately regardless
    # of what state the conversation was in.
    if phone_number and handle_utterance_for_compliance(phone_number, speech_result):
        call_manager.end_call(call_sid)
        return Response(
            say_and_hangup("Understood — you won't receive any further calls from us. Take care."),
            mimetype="text/xml",
        )

    twiml = _advance(pipeline, call_sid, speech_result, action_url="/gather")
    return Response(twiml, mimetype="text/xml")


@app.route("/call-status", methods=["POST"])
def call_status():
    phone_number = request.form.get("To", "")
    status = request.form.get("CallStatus", "")
    result = call_manager.handle_call_status(phone_number, status)
    return {"ok": True, "result": result}


@app.route("/outbound-call", methods=["POST"])
def outbound_call():
    """
    Real implementation slot — triggers a new outbound call via Twilio's REST API:

        from twilio.rest import Client
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        call = client.calls.create(
            to=target_number,
            from_=TWILIO_PHONE_NUMBER,
            url="https://your-server.com/voice",
            status_callback="https://your-server.com/call-status",
        )

    Needs a real Twilio account + phone number + a publicly reachable URL
    (ngrok for local dev, or a deployed server) — none of which exist in this
    sandbox, so the actual dial is still a stub. The compliance gate below,
    though, is real and always runs first: no number gets dialed without
    passing the do-not-call + calling-hours check.
    """
    target_number = request.form.get("to", "")
    try:
        check_can_call(target_number)
    except ComplianceBlock as e:
        return {"error": "blocked_by_compliance", "reason": e.reason}, 403

    return {"error": "Not implemented in sandbox — needs Twilio credentials + public URL"}, 501


if __name__ == "__main__":
    app.run(port=5000)
