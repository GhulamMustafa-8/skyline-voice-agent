/**
 * Design plan (per the frontend-design brief):
 *
 * Subject: an internal ops screen for a real-estate agency reviewing how the
 * AI voice agent's calls went today — not a marketing dashboard. The
 * audience is whoever runs sales ops: they want to know, at a glance, how
 * many calls happened, how many are worth a callback, and where the agent
 * struggled.
 *
 * Color: warm paper background (#F7F4EE), near-black warm ink (#211F1C),
 * brass accent (#AD8A4D) for the primary "hot leads" figure — a nod to
 * estate-agent signage brass without leaning on a generic SaaS blue/purple.
 * Muted teal (#3C6E71) marks warm leads, quiet rose (#9C4B44) marks
 * escalations/objections — desaturated so they read as data, not alarms.
 *
 * Type: "Source Serif 4" for the big headline figures (gives the page a
 * printed-ledger, brokerage-paperwork feel), "Inter" for every label, table
 * row, and data value (a serif at small sizes for dense data is harder to
 * scan).
 *
 * Layout: a single ledger column, not a card grid — hairline rules divide
 * sections the way a printed call sheet or property listing sheet would.
 * This is a deliberate choice tied to the real-estate paperwork motif
 * (ledgers, listing sheets), not the generic broadsheet default: the whole
 * page is built around one literal object (today's stack of call records),
 * not a dashboard chrome applied to any dataset.
 *
 * Principle: nothing here is decorative. Every rule, number, and bar reports
 * something. No card shadows, no gradient washes, no icon per stat.
 */

import React, { useMemo, useState } from "react";

const COLORS = {
  paper: "#F7F4EE",
  ink: "#211F1C",
  inkMuted: "#6B6459",
  hairline: "#DDD5C7",
  brass: "#AD8A4D",
  teal: "#3C6E71",
  rose: "#9C4B44",
};

const OUTCOME_META = {
  end: { label: "Completed", color: COLORS.ink },
  fallback_human: { label: "Escalated to human", color: COLORS.rose },
  not_interested: { label: "Not interested", color: COLORS.inkMuted },
  callback_scheduled: { label: "Callback scheduled", color: COLORS.teal },
  "": { label: "Dropped / in progress", color: COLORS.hairline },
};

// Sample data shaped exactly like phase5/crm.py's get_dashboard_stats(),
// standing in until this is wired to a real API route reading crm.db.
const SAMPLE_STATS = {
  total_calls: 42,
  by_outcome: { end: 22, fallback_human: 6, not_interested: 10, "": 4 },
  by_score: { Hot: 9, Warm: 15, Cold: 8 },
  avg_objections_per_call: 0.7,
};

const SAMPLE_RECENT_CALLS = [
  { phone: "+92 300 1234567", area: "Bahria Town", score: "Hot", outcome: "Callback scheduled", time: "4:12 PM" },
  { phone: "+92 300 7654321", area: "—", score: "—", outcome: "Not interested", time: "3:58 PM" },
  { phone: "+92 300 9999999", area: "DHA Phase 6", score: "Warm", outcome: "Escalated to human", time: "3:41 PM" },
  { phone: "+92 300 5555555", area: "Clifton", score: "Warm", outcome: "Completed", time: "3:20 PM" },
  { phone: "+92 300 2223344", area: "Gulberg", score: "Cold", outcome: "Completed", time: "2:55 PM" },
];

function outcomeBreakdown(stats) {
  const total = Object.values(stats.by_outcome).reduce((a, b) => a + b, 0) || 1;
  return Object.entries(stats.by_outcome).map(([key, count]) => ({
    key,
    label: (OUTCOME_META[key] || { label: key }).label,
    color: (OUTCOME_META[key] || { color: COLORS.ink }).color,
    count,
    pct: Math.round((count / total) * 100),
  }));
}

function scoreBreakdown(stats) {
  const order = [
    { key: "Hot", color: COLORS.brass },
    { key: "Warm", color: COLORS.teal },
    { key: "Cold", color: COLORS.hairline },
  ];
  const total = Object.values(stats.by_score).reduce((a, b) => a + b, 0) || 1;
  return order
    .filter((o) => stats.by_score[o.key] !== undefined)
    .map((o) => ({
      ...o,
      count: stats.by_score[o.key],
      pct: Math.round((stats.by_score[o.key] / total) * 100),
    }));
}

function Bar({ pct, color }) {
  return (
    <div style={{ background: COLORS.hairline, height: 6, width: "100%", borderRadius: 0 }}>
      <div style={{ background: color, height: 6, width: `${pct}%` }} />
    </div>
  );
}

export default function Dashboard({ stats = SAMPLE_STATS, recentCalls = SAMPLE_RECENT_CALLS }) {
  const [dateLabel] = useState("Today · Sep 5");
  const outcomes = useMemo(() => outcomeBreakdown(stats), [stats]);
  const scores = useMemo(() => scoreBreakdown(stats), [stats]);
  const hot = stats.by_score.Hot || 0;

  return (
    <div
      style={{
        background: COLORS.paper,
        color: COLORS.ink,
        fontFamily: "Inter, ui-sans-serif, system-ui, sans-serif",
        padding: "48px 32px",
        maxWidth: 720,
        margin: "0 auto",
      }}
    >
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&family=Inter:wght@400;500;600&display=swap');
        .ledger-row { display: flex; justify-content: space-between; align-items: baseline; padding: 10px 0; }
        .ledger-row + .ledger-row { border-top: 1px solid ${COLORS.hairline}; }
        table.calls { width: 100%; border-collapse: collapse; }
        table.calls th { text-align: left; font-weight: 500; color: ${COLORS.inkMuted}; font-size: 13px; padding-bottom: 8px; }
        table.calls td { padding: 10px 0; border-top: 1px solid ${COLORS.hairline}; font-size: 14px; }
      `}</style>

      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: 8 }}>
        <div>
          <div style={{ fontSize: 13, color: COLORS.inkMuted, marginBottom: 4 }}>Skyline Realty · Voice Agent</div>
          <h1 style={{ fontFamily: "'Source Serif 4', serif", fontWeight: 600, fontSize: 28, margin: 0 }}>
            Call log
          </h1>
        </div>
        <div style={{ fontSize: 13, color: COLORS.inkMuted }}>{dateLabel}</div>
      </div>

      <div style={{ height: 1, background: COLORS.ink, margin: "20px 0 32px" }} />

      {/* Headline figures */}
      <div style={{ display: "flex", gap: 40, marginBottom: 40 }}>
        <div>
          <div style={{ fontFamily: "'Source Serif 4', serif", fontSize: 44, lineHeight: 1 }}>
            {stats.total_calls}
          </div>
          <div style={{ fontSize: 13, color: COLORS.inkMuted, marginTop: 6 }}>calls placed</div>
        </div>
        <div>
          <div style={{ fontFamily: "'Source Serif 4', serif", fontSize: 44, lineHeight: 1, color: COLORS.brass }}>
            {hot}
          </div>
          <div style={{ fontSize: 13, color: COLORS.inkMuted, marginTop: 6 }}>hot leads today</div>
        </div>
        <div>
          <div style={{ fontFamily: "'Source Serif 4', serif", fontSize: 44, lineHeight: 1 }}>
            {stats.avg_objections_per_call}
          </div>
          <div style={{ fontSize: 13, color: COLORS.inkMuted, marginTop: 6 }}>avg. objections / call</div>
        </div>
      </div>

      {/* Outcomes */}
      <div style={{ marginBottom: 36 }}>
        <div style={{ fontSize: 13, color: COLORS.inkMuted, marginBottom: 12, textTransform: "none" }}>
          How calls ended
        </div>
        {outcomes.map((o) => (
          <div className="ledger-row" key={o.key || "blank"}>
            <div style={{ width: 160, fontSize: 14 }}>{o.label}</div>
            <div style={{ flex: 1, margin: "0 16px" }}>
              <Bar pct={o.pct} color={o.color} />
            </div>
            <div style={{ width: 48, textAlign: "right", fontSize: 14, color: COLORS.inkMuted }}>
              {o.count}
            </div>
          </div>
        ))}
      </div>

      {/* Lead scores */}
      <div style={{ marginBottom: 36 }}>
        <div style={{ fontSize: 13, color: COLORS.inkMuted, marginBottom: 12 }}>Lead quality</div>
        {scores.map((s) => (
          <div className="ledger-row" key={s.key}>
            <div style={{ width: 160, fontSize: 14 }}>{s.key}</div>
            <div style={{ flex: 1, margin: "0 16px" }}>
              <Bar pct={s.pct} color={s.color} />
            </div>
            <div style={{ width: 48, textAlign: "right", fontSize: 14, color: COLORS.inkMuted }}>
              {s.count}
            </div>
          </div>
        ))}
      </div>

      {/* Recent calls */}
      <div>
        <div style={{ fontSize: 13, color: COLORS.inkMuted, marginBottom: 4 }}>Most recent calls</div>
        <table className="calls">
          <thead>
            <tr>
              <th>Number</th>
              <th>Area</th>
              <th>Score</th>
              <th>Outcome</th>
              <th style={{ textAlign: "right" }}>Time</th>
            </tr>
          </thead>
          <tbody>
            {recentCalls.map((c, i) => (
              <tr key={i}>
                <td>{c.phone}</td>
                <td>{c.area}</td>
                <td style={{ color: c.score === "Hot" ? COLORS.brass : c.score === "Warm" ? COLORS.teal : COLORS.inkMuted }}>
                  {c.score}
                </td>
                <td>{c.outcome}</td>
                <td style={{ textAlign: "right", color: COLORS.inkMuted }}>{c.time}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
