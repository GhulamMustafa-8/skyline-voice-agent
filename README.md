# Skyline Realty Voice Agent — Autonomous Outbound Lead-Qualification Agent

An agentic voice AI that calls real-estate leads, has a real qualification
conversation (buy/rent, budget, area, timeline), handles objections, scores
the lead, logs everything to a CRM, and escalates to a human when it should —
all with compliance (AI disclosure, do-not-call, calling hours) built in from
day one rather than bolted on.

Built as a portfolio project to demonstrate agentic AI engineering: multi-step
reasoning with tool use, a verifiable state machine (not just prompt-and-hope),
and the "boring" production concerns (compliance, CRM, retries) that separate
a demo script from a system.

## Why this project

Most "AI voice agent" portfolio projects are a single LLM call wrapped in a
speech API. This one is built around a **deterministic state machine that the
LLM's decisions are validated against** — the model chooses what to say and
which state to move to via function calling, but it cannot make an illegal
transition (e.g. jump straight from greeting to closing). That guardrail is
what makes an agentic system trustworthy enough to put in front of real phone
calls, and it's the main engineering idea this project demonstrates.

## Architecture

```
Caller <--phone--> Twilio <--webhook--> Flask server (Phase 3)
                                            |
                                            v
                                   Compliance gate (Phase 6)
                                   (do-not-call / hours / opt-out)
                                            |
                                            v
                                   Call Manager (Phase 3)
                                   (per-call state, keyed by CallSid)
                                            |
                                            v
                              +----------------------------+
                              |   Conversation State        |
                              |   Machine (Phase 2)         |
                              |   - legal transitions only  |
                              +----------------------------+
                                            |
                                            v
                              LLM Reasoner (Phase 4)
                              - function calling: reply, next_state,
                                extracted fields, sentiment, objection flag
                                            |
                                            v
                                    CRM / SQLite (Phase 5)
                                    - leads, call_logs
                                            |
                                            v
                                Analytics Dashboard (Phase 7)
                                (React, ledger-style call log)
```

## Phase-by-phase summary

| Phase | What it built | Key file(s) |
|---|---|---|
| 1 | Scope, conversation script, objection bank, scoring rubric | `phase1/scope_and_script.md` |
| 2 | Core state machine + pluggable STT/LLM/TTS pipeline | `phase2/state_machine.py`, `pipeline.py` |
| 3 | Twilio webhook integration (turn-based `<Gather>`), call manager, retry logic | `phase3/webhook_server.py`, `call_manager.py` |
| 4 | Real LLM function-calling reasoner: sentiment, objection counting, structured extraction | `phase4/llm_reasoner.py` |
| 5 | SQLite CRM: leads table, call logs, dashboard aggregation query | `phase5/crm.py` |
| 6 | Compliance gate: do-not-call, calling hours, mid-call opt-out | `phase6/compliance.py` |
| 7 | Analytics dashboard (React) — ledger-style call review UI | `phase7/Dashboard.jsx` |
| 8 | Edge-case tests, full regression, this README | `phase8/test_edge_cases.py` |

## Key design decisions (worth mentioning in an interview)

- **State machine + LLM, not LLM alone.** The reasoner picks a `next_state`
  from a fixed enum via tool use; `can_transition()` rejects illegal jumps
  before they ever reach the caller. This is what makes the "agent" part
  trustworthy rather than a chatbot that might say anything.
- **Escalation is reachable from (almost) everywhere.** An early bug (caught
  by `phase4/test_llm_reasoner.py`) only allowed escalation to a human from
  one specific state. Real callers get frustrated at unpredictable points, so
  `FALLBACK_HUMAN` and `END` had to be legal from nearly every state — a
  finding worth mentioning as an example of test-driven design correction.
- **Compliance is a gate everything calls through, not a checklist.**
  `check_can_call()` is the single place that decides whether a number can be
  dialed; both the live conversation (`/gather`) and the outbound dial route
  go through it. A plain "not interested" is deliberately NOT the same as an
  opt-out — only an explicit "don't contact me again" permanently blocks a
  number, since a cold lead today may be a warm one in six months.
- **Pluggable interfaces everywhere.** STT, TTS, and the reasoner are all
  behind small abstract interfaces with a "stub" (offline, free) and a "real"
  implementation slot. This let the whole system be built and tested without
  ever needing an API key, and means swapping in Deepgram/ElevenLabs/Claude
  is a one-line change, not a rewrite.

## Known limitations (be upfront about these)

- **Turn-based, not streaming.** Uses Twilio's `<Gather>` (speak, then
  listen for a full utterance) rather than continuous bidirectional audio
  streaming. This is simpler and was the right choice to get a correct MVP,
  but it means the caller can't interrupt the agent mid-sentence. Upgrading
  to Twilio Media Streams + a real-time STT provider is the natural next
  step for lower latency and interruption handling.
- **Field-extraction accuracy** depends entirely on the reasoner. The
  `StubReasoner`/`MockAnthropicClient` used for offline testing are simple
  keyword-matchers, not real language understanding — they're good enough to
  validate the surrounding plumbing (state transitions, CRM writes,
  compliance gating) but not a substitute for testing against the real LLM.
  Multilingual (Urdu/English code-switching) input is explicitly a known gap
  for the current stub, not silently swallowed — see
  `phase8/test_edge_cases.py`.
- **No live network testing.** This was built in a sandboxed environment
  with no internet access, so Twilio, Deepgram, ElevenLabs, and Anthropic API
  calls are all real-shaped code with the actual request/response structure,
  but were never exercised against the live services. Every layer was instead
  verified with realistic offline substitutes (Flask's test client standing
  in for Twilio, a mock Anthropic client matching the real tool-use response
  shape, headless-browser screenshots for the dashboard UI). Plugging in real
  credentials is the last step, not a redesign.

## Running this for real

1. **Twilio**: buy a number, set its voice webhook to `<your-server>/voice`,
   status callback to `<your-server>/call-status`. Needs a public URL (ngrok
   for local dev).
2. **Anthropic API**: set `ANTHROPIC_API_KEY`, swap `StubReasoner()` /
   `MockAnthropicClient()` for `LLMReasoner(client=anthropic.Anthropic(...))`
   in `webhook_server.py`.
3. **Deepgram/ElevenLabs** (optional upgrade): implement the two
   `NotImplementedError` slots in `phase2/stt.py` and `tts.py`, and switch
   `webhook_server.py` from `<Gather>` to `<Stream>` for real-time audio.
4. `pip install flask twilio anthropic` and run `python3 webhook_server.py`.

## Test coverage

Every phase has an offline, no-API-key-required test that was run and passed
during development:
- `phase2/test_conversation.py` — state machine + pipeline wiring
- `phase3/test_webhook_flow.py` — Twilio webhook simulation
- `phase4/test_llm_reasoner.py` — LLM function-calling plumbing, sentiment,
  objection escalation (caught the escalation-reachability bug)
- `phase5/test_crm.py` — CRM writes + dashboard aggregation
- `phase6/test_compliance.py` + `test_compliance_integration.py` — DNC,
  calling hours, mid-call opt-out, wired into the live call flow
- `phase7/test_dashboard_data.js` — dashboard data transforms
- `phase8/test_edge_cases.py` — silence, gibberish, rambling, infinite-loop
  protection, dropped call state, code-switched input
