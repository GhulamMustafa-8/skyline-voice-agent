const { outcomeBreakdown, scoreBreakdown, summaryHeadline } = require("./dashboard_data");

const sampleStats = {
  total_calls: 42,
  by_outcome: { end: 22, fallback_human: 6, not_interested: 10, "": 4 },
  by_score: { Hot: 9, Warm: 15, Cold: 8 },
  avg_objections_per_call: 0.7,
};

console.log("--- outcomeBreakdown ---");
console.log(outcomeBreakdown(sampleStats));

console.log("\n--- scoreBreakdown ---");
console.log(scoreBreakdown(sampleStats));

console.log("\n--- summaryHeadline ---");
console.log(summaryHeadline(sampleStats));

// Sanity checks
const outcomes = outcomeBreakdown(sampleStats);
const outcomeTotal = outcomes.reduce((a, o) => a + o.count, 0);
console.log(
  outcomeTotal === sampleStats.total_calls
    ? "PASS: outcome counts sum to total_calls"
    : `FAIL: outcome counts sum to ${outcomeTotal}, expected ${sampleStats.total_calls}`
);

const scores = scoreBreakdown(sampleStats);
const scoreTotal = scores.reduce((a, s) => a + s.count, 0);
console.log(
  scoreTotal === 32
    ? "PASS: score counts sum correctly"
    : `FAIL: score counts sum to ${scoreTotal}, expected 32`
);
