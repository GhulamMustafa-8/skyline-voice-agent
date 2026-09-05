import React, { useMemo, useState } from "react";

const COLORS = {
  bg: "#15140F",
  surface: "#1E1C16",
  border: "rgba(241,236,225,0.08)",
  textPrimary: "#F1ECE1",
  textSecondary: "#A39C8C",
  textMuted: "#6E6858",
  amber: "#E3A34D",
  teal: "#4FA8A0",
  green: "#6FA96B",
  red: "#C1584A",
};

const OUTCOME_META = {
  end: { label: "Completed", color: COLORS.green },
  fallback_human: { label: "Escalated to human", color: COLORS.red },
  not_interested: { label: "Not interested", color: COLORS.textMuted },
  callback_scheduled: { label: "Callback scheduled", color: COLORS.teal },
  "": { label: "Dropped / in progress", color: COLORS.textMuted },
};

const SAMPLE_STATS = {
  total_calls: 42,
  by_outcome: { end: 22, fallback_human: 6, not_interested: 10, "": 4 },
  by_score: { Hot: 9, Warm: 15, Cold: 8 },
  avg_objections_per_call: 0.7,
};

const SAMPLE_HOURLY = [
  { hour: "9a", count: 2 },
  { hour: "10a", count: 4 },
  { hour: "11a", count: 5 },
  { hour: "12p", count: 3 },
  { hour: "1p", count: 6 },
  { hour: "2p", count: 7 },
  { hour: "3p", count: 8 },
  { hour: "4p", count: 5 },
  { hour: "5p", count: 2 },
];

const SAMPLE_RECENT_CALLS = [
  { phone: "+92 300 123 4567", area: "Bahria Town", score: "Hot", outcome: "Callback scheduled", time: "4:12 PM" },
  { phone: "+92 300 765 4321", area: "-", score: "-", outcome: "Not interested", time: "3:58 PM" },
  { phone: "+92 300 999 9999", area: "DHA Phase 6", score: "Warm", outcome: "Escalated to human", time: "3:41 PM" },
  { phone: "+92 300 555 5555", area: "Clifton", score: "Warm", outcome: "Completed", time: "3:20 PM" },
  { phone: "+92 300 222 3344", area: "Gulberg", score: "Cold", outcome: "Completed", time: "2:55 PM" },
];

function outcomeBreakdown(stats) {
  const total = Object.values(stats.by_outcome).reduce((a, b) => a + b, 0) || 1;
  return Object.entries(stats.by_outcome).map(([key, count]) => ({
    key,
    label: (OUTCOME_META[key] || { label: key }).label,
    color: (OUTCOME_META[key] || { color: COLORS.textPrimary }).color,
    count,
    pct: Math.round((count / total) * 100),
  }));
}

function scoreBreakdown(stats) {
  const order = [
    { key: "Hot", color: COLORS.amber },
    { key: "Warm", color: COLORS.teal },
    { key: "Cold", color: COLORS.textMuted },
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

function Meter({ pct, color }) {
  return (
    <div style={{ background: "rgba(241,236,225,0.08)", height: 6, borderRadius: 3, width: "100%" }}>
      <div style={{ background: color, height: 6, borderRadius: 3, width: `${pct}%` }} />
    </div>
  );
}

function HourlyWave({ data }) {
  const max = Math.max(...data.map((d) => d.count), 1);
  const peak = data.reduce((a, b) => (b.count > a.count ? b : a), data[0]);
  return (
    <div>
      <div style={{ display: "flex", alignItems: "flex-end", gap: 4, height: 52 }}>
        {data.map((d) => (
          <div
            key={d.hour}
            title={`${d.count} calls at ${d.hour}`}
            style={{
              flex: 1,
              height: `${Math.max((d.count / max) * 100, 8)}%`,
              background: d.hour === peak.hour ? COLORS.amber : "rgba(241,236,225,0.14)",
            }}
          />
        ))}
      </div>
      <div style={{ display: "flex", gap: 4, marginTop: 4 }}>
        {data.map((d) => (
          <div key={d.hour} style={{ flex: 1, textAlign: "center", fontSize: 11, color: COLORS.textMuted }}>
            {d.hour}
          </div>
        ))}
      </div>
    </div>
  );
}

export default function Dashboard({ stats = SAMPLE_STATS, recentCalls = SAMPLE_RECENT_CALLS, hourly = SAMPLE_HOURLY }) {
  const [timeLabel] = useState(() =>
    new Date().toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" })
  );
  const outcomes = useMemo(() => outcomeBreakdown(stats), [stats]);
  const scores = useMemo(() => scoreBreakdown(stats), [stats]);

  return (
    <div
      style={{
        background: COLORS.bg,
        color: COLORS.textPrimary,
        fontFamily: "Inter, ui-sans-serif, system-ui, sans-serif",
        padding: "clamp(24px, 5vw, 40px) clamp(18px, 4vw, 28px)",
        maxWidth: 720,
        margin: "0 auto",
        minHeight: "100vh",
      }}
    >
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&family=Inter:wght@400;500;600&display=swap');
        .row { display: grid; grid-template-columns: 130px 1fr 32px; align-items: center; gap: 10px; padding: 7px 0; }
        .call-row { display: grid; grid-template-columns: 1fr 100px 70px 1fr 60px; gap: 10px; padding: 9px 0; border-top: 1px solid ${COLORS.border}; font-size: 13px; align-items: center; transition: background-color 120ms ease; }
        .call-row:hover { background-color: rgba(241,236,225,0.03); }
        .mono { font-family: 'JetBrains Mono', ui-monospace, monospace; }
        @media (max-width: 520px) {
          .call-row { grid-template-columns: 1fr 70px 1fr; }
          .call-row .hide-sm { display: none; }
        }
      `}</style>

      {/* Status line */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 8, paddingBottom: 14, borderBottom: `1px solid ${COLORS.border}`, marginBottom: 24 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ width: 8, height: 8, borderRadius: "50%", background: COLORS.green, display: "inline-block" }} />
          <span style={{ fontSize: 14, fontWeight: 600 }}>Skyline voice agent</span>
          <span style={{ fontSize: 13, color: COLORS.textMuted }}>dispatch</span>
        </div>
        <span className="mono" style={{ fontSize: 13, color: COLORS.textSecondary }}>{timeLabel}</span>
      </div>

      {/* Headline metrics */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 12, marginBottom: 32 }}>
        <div style={{ background: COLORS.surface, borderRadius: 8, padding: "16px" }}>
          <div style={{ fontSize: 13, color: COLORS.textSecondary, marginBottom: 6 }}>Calls placed</div>
          <div className="mono" style={{ fontSize: 30, fontWeight: 500 }}>{stats.total_calls}</div>
        </div>
        <div style={{ background: COLORS.surface, borderRadius: 8, padding: "16px" }}>
          <div style={{ fontSize: 13, color: COLORS.textSecondary, marginBottom: 6 }}>Hot leads</div>
          <div className="mono" style={{ fontSize: 30, fontWeight: 500, color: COLORS.amber }}>{stats.by_score.Hot || 0}</div>
        </div>
        <div style={{ background: COLORS.surface, borderRadius: 8, padding: "16px" }}>
          <div style={{ fontSize: 13, color: COLORS.textSecondary, marginBottom: 6 }}>Avg objections</div>
          <div className="mono" style={{ fontSize: 30, fontWeight: 500 }}>{stats.avg_objections_per_call}</div>
        </div>
      </div>

      {/* Calls by hour */}
      <div style={{ marginBottom: 32 }}>
        <div style={{ fontSize: 13, color: COLORS.textSecondary, marginBottom: 12 }}>Calls by hour</div>
        <HourlyWave data={hourly} />
      </div>

      {/* Outcomes */}
      <div style={{ marginBottom: 32 }}>
        <div style={{ fontSize: 13, color: COLORS.textSecondary, marginBottom: 10 }}>How calls ended</div>
        {outcomes.map((o) => (
          <div className="row" key={o.key || "blank"}>
            <span style={{ fontSize: 13 }}>{o.label}</span>
            <Meter pct={o.pct} color={o.color} />
            <span className="mono" style={{ fontSize: 13, color: COLORS.textSecondary, textAlign: "right" }}>{o.count}</span>
          </div>
        ))}
      </div>

      {/* Lead quality */}
      <div style={{ marginBottom: 32 }}>
        <div style={{ fontSize: 13, color: COLORS.textSecondary, marginBottom: 10 }}>Lead quality</div>
        {scores.map((s) => (
          <div className="row" key={s.key}>
            <span style={{ fontSize: 13 }}>{s.key}</span>
            <Meter pct={s.pct} color={s.color} />
            <span className="mono" style={{ fontSize: 13, color: COLORS.textSecondary, textAlign: "right" }}>{s.count}</span>
          </div>
        ))}
      </div>

      {/* Recent calls */}
      <div>
        <div style={{ fontSize: 13, color: COLORS.textSecondary, marginBottom: 6 }}>Recent calls</div>
        {recentCalls.map((c, i) => (
          <div className="call-row" key={i}>
            <span className="mono">{c.phone}</span>
            <span className="hide-sm" style={{ color: COLORS.textSecondary }}>{c.area}</span>
            <span style={{ fontWeight: 500, color: c.score === "Hot" ? COLORS.amber : c.score === "Warm" ? COLORS.teal : COLORS.textMuted }}>
              {c.score}
            </span>
            <span className="hide-sm" style={{ color: c.outcome === "Escalated to human" ? COLORS.red : COLORS.textSecondary }}>
              {c.outcome}
            </span>
            <span className="mono" style={{ color: COLORS.textMuted, textAlign: "right" }}>{c.time}</span>
          </div>
        ))}
      </div>
    </div>
  );
}