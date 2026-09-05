"""
Pipeline orchestrator: ties STT -> Reasoner -> State Machine -> TTS together.

In production this loop is driven by real-time audio chunks from a phone call
(Phase 3, via Twilio). For now it's driven by text input so we can fully test
the conversation logic offline, with zero API keys required.
"""

from state_machine import ConversationContext, State, can_transition, score_lead
from llm_agent import Reasoner, StubReasoner
from stt import STT, TextStub as STTTextStub
from tts import TTS, TextStub as TTSTextStub


class VoiceAgentPipeline:
    def __init__(self, reasoner: Reasoner, stt: STT, tts: TTS):
        self.reasoner = reasoner
        self.stt = stt
        self.tts = tts
        self.ctx = ConversationContext()

    def step(self, user_audio_or_text) -> str:
        """One turn: transcribe -> reason -> validate transition -> speak."""
        user_text = self.stt.transcribe(user_audio_or_text)
        self.ctx.log("user", user_text)

        decision = self.reasoner.decide(self.ctx, user_text)

        # Guardrail: don't let the reasoner jump to an illegal state.
        if not can_transition(self.ctx.state, decision.next_state) and decision.next_state != self.ctx.state:
            raise ValueError(
                f"Illegal transition attempted: {self.ctx.state} -> {decision.next_state}"
            )

        # Merge any extracted lead fields
        for k, v in decision.extracted.items():
            if hasattr(self.ctx.lead, k):
                setattr(self.ctx.lead, k, v)

        self.ctx.state = decision.next_state

        # Auto-score once we hit SCORING state
        if self.ctx.state == State.SCORING:
            self.ctx.lead.score = score_lead(self.ctx.lead)

        if decision.reply_text:
            self.ctx.log("agent", decision.reply_text)
            self.tts.speak(decision.reply_text)

        return decision.reply_text

    def is_done(self) -> bool:
        return self.ctx.state == State.END


def build_local_pipeline() -> VoiceAgentPipeline:
    """Wires up the offline/testable version — no network, no API keys."""
    return VoiceAgentPipeline(
        reasoner=StubReasoner(),
        stt=STTTextStub(),
        tts=TTSTextStub(),
    )
