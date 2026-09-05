/**
 * Pure transforms from the CRM's raw stats shape (see phase5/crm.py's
 * get_dashboard_stats) into chart-ready shapes for the dashboard UI.
 * Kept separate from the React component so this logic can be tested with
 * plain Node — no browser/bundler needed to verify it's correct.
 */

function outcomeBreakdown(stats) {
  const labels = {
    end: "Completed",
    fallback_human: "Escalated to human",
    not_interested: "Not interested",
    callback_scheduled: "Callback scheduled",
    "": "In progress / dropped",
  };
  const total = Object.values(stats.by_outcome).reduce((a, b) => a + b, 0) || 1;
  return Object.entries(stats.by_outcome).map(([key, count]) => ({
    key,
    label: labels[key] || key,
    count,
    pct: Math.round((count / total) * 100),
  }));
}

function scoreBreakdown(stats) {
  const order = ["Hot", "Warm", "Cold"];
  const total = Object.values(stats.by_score).reduce((a, b) => a + b, 0) || 1;
  return order
    .filter((k) => stats.by_score[k] !== undefined)
    .map((key) => ({
      key,
      count: stats.by_score[key],
      pct: Math.round((stats.by_score[key] / total) * 100),
    }));
}

function summaryHeadline(stats) {
  const hot = stats.by_score.Hot || 0;
  const total = stats.total_calls || 0;
  return {
    totalCalls: total,
    hotLeads: hot,
    avgObjections: stats.avg_objections_per_call,
  };
}

module.exports = { outcomeBreakdown, scoreBreakdown, summaryHeadline };
