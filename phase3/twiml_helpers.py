"""
TwiML (Twilio Markup Language) helpers.

Twilio calls your webhook URL and expects XML back telling it what to do next
(speak something, listen for speech, hang up, etc). You don't need the twilio
SDK just to GENERATE this XML — plain string templates work fine and keep this
testable without any external dependency.

Design choice: using <Gather input="speech"> (turn-based: agent speaks a full
sentence, then listens for a full user utterance) rather than raw <Stream>
(continuous bidirectional audio streaming). Turn-based is simpler to get
correct first, and is what most production IVR/voice-bot systems start with.
Continuous streaming (lower latency, handles interruptions) is a natural
Phase 3.5 upgrade once this works end-to-end.
"""

from xml.sax.saxutils import escape


def say_and_gather(text: str, action_url: str, hints: str = "") -> str:
    """Agent speaks `text`, then listens for the caller's speech and POSTs
    the transcript to `action_url`."""
    hints_attr = f' hints="{escape(hints)}"' if hints else ""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Gather input="speech" action="{escape(action_url)}" method="POST"
            speechTimeout="auto"{hints_attr}>
        <Say voice="Polly.Joanna">{escape(text)}</Say>
    </Gather>
    <Say voice="Polly.Joanna">Sorry, I didn't catch that. We'll try again later. Goodbye.</Say>
    <Hangup/>
</Response>"""


def say_and_hangup(text: str) -> str:
    """Agent speaks `text` then ends the call — used for END state."""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Joanna">{escape(text)}</Say>
    <Hangup/>
</Response>"""


def redirect_to_human(text: str, transfer_number: str) -> str:
    """FALLBACK_HUMAN state — say a short handoff line, then dial a real agent."""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Joanna">{escape(text)}</Say>
    <Dial>{escape(transfer_number)}</Dial>
</Response>"""
