# Phase 1: Scope & Requirements — Real Estate Lead-Gen Voice Agent

## 1. Use Case
Outbound voice agent calls prospects from a lead list (people who showed interest via a form,
ad click, or old inquiry) to:
- Re-engage them
- Understand their property requirement (buy/rent, budget, location, timeline)
- Qualify them as hot / warm / cold
- Book a callback/site visit with a human agent if qualified

## 2. Conversation Flow (State Machine)

```
[START]
  -> Greeting + AI disclosure ("Hi, I'm an AI assistant calling on behalf of [Company]...")
  -> Confirm identity ("Am I speaking with [Name]?")
      -> No / Wrong number -> Apologize -> [END: wrong_number]
      -> Yes -> Continue

[INTENT_CHECK]
  -> "You'd enquired about properties in [Area] a while back — still looking?"
      -> Not interested -> Handle gracefully -> Ask reason (optional) -> [END: not_interested]
      -> Busy right now -> Offer callback time -> [END: callback_scheduled]
      -> Interested -> Continue

[QUALIFICATION]
  -> Ask: Buy or Rent?
  -> Ask: Budget range
  -> Ask: Preferred location/area
  -> Ask: Timeline (immediate / 1-3 months / just exploring)
  -> [If any objection arises here -> OBJECTION_HANDLING -> return to qualification]

[SCORING]
  -> Hot: clear budget + urgent timeline + specific location
  -> Warm: some info given but vague timeline
  -> Cold: just exploring / no clear budget

[CLOSING]
  -> Hot/Warm -> Offer to schedule call/site visit with human agent -> Confirm date/time
  -> Cold -> Thank them, note preferences for future follow-up
  -> [END: call_complete, lead logged with score]

[OBJECTION_HANDLING] (sub-flow, re-entrant)
  -> "Price is too high" -> Mention flexible options / ask budget -> return
  -> "Not a good time" -> Offer to call back later, ask best time -> [END: callback_scheduled]
  -> "How did you get my number" -> Explain (prior inquiry/consent) -> return or end if upset
  -> "I'm not interested at all" -> Respect it, mark do-not-call -> [END: not_interested]

[FALLBACK]
  -> If conversation gets complex/negotiation-heavy or user asks for pricing specifics
     -> Offer to transfer to human agent with context summary
```

## 3. Sample Script Snippets

**Opening:**
"Hi, this is an AI assistant calling on behalf of [Company Name]. Am I speaking with [Name]?
... Great — I'm reaching out because you'd shown interest in properties around [Area]
a little while back. Are you still exploring options?"

**Qualification questions:**
- "Are you looking to buy or rent?"
- "Do you have a budget range in mind?"
- "Which area or neighborhood are you focused on?"
- "Are you looking to move in the next few weeks, or is this more long-term planning?"

**Objection — price:**
"Totally understand — budgets matter a lot. Just so I can point you to the right options,
what range were you hoping to stay within?"

**Objection — bad timing:**
"No problem at all. When would be a better time for a quick call — later today, or tomorrow?"

**Closing (hot lead):**
"This sounds like a great fit. I'll set you up with one of our property consultants —
does [day/time] work for a quick call or site visit?"

**Closing (not interested):**
"Understood, thanks for your time. I'll make sure we don't reach out again unless you'd like us to."

## 4. Lead Scoring Logic (rule-based for MVP)
| Signal | Hot | Warm | Cold |
|---|---|---|---|
| Budget given | Yes, specific | Vague | Not given |
| Timeline | Immediate/1 month | 1-3 months | Exploring only |
| Location | Specific area | General area | Not sure |

## 5. Compliance Notes (baked into script from day 1)
- AI disclosure at call start (non-negotiable)
- Immediate opt-out honored ("don't call me again" -> mark do-not-call, end call politely)
- No call outside reasonable hours (assume 9am-7pm local, enforced later at scheduling layer)

## 6. Out of Scope for Phase 1
- Actual voice pipeline (STT/TTS) — Phase 2
- Real phone calls via Twilio — Phase 3
- Database/CRM storage — Phase 5
- This phase is script + flow design only, so the reasoning logic has a clear spec before any code is written.
