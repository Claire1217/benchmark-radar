/* Official ranks and a selected publisher's comparison never share score inputs. */
(function (root) {
  'use strict';
  function selectRanking(data, benchmarkId, modelId) {
    const audit = data.benchmark_audits?.[benchmarkId];
    const snapshot = audit?.coreEligible ? data.leaderboard_snapshots?.[benchmarkId] : null;
    const lower = data.benchmarks[benchmarkId]?.direction === 'lower_is_better';
    const best = new Map();
    for (const run of snapshot?.rows || []) {
      if (run.provenance !== 'benchmark_evaluation' || !Number.isFinite(run.display_value)) continue;
      const previous = best.get(run.name);
      if (!previous || (lower ? run.display_value < previous.display_value : run.display_value > previous.display_value)) best.set(run.name, run);
    }
    const byScore = (a, b) => (lower ? a.display_value - b.display_value : b.display_value - a.display_value) || a.name.localeCompare(b.name);
    const rank = rows => rows.sort(byScore).map((row, i, sorted) => ({...row, rank: sorted.findIndex(r => r.display_value === row.display_value) + 1}));
    const official = rank([...best.values()]);
    const selected = (data.charts[benchmarkId]?.rows || []).find(r => r.model_id === modelId);
    const receipt = data.report_audits?.[benchmarkId]?.[modelId];
    const matched = receipt?.status === 'matched_report' && receipt.value === selected?.display_value;
    const own = selected ? {...selected, name: data.models[modelId].name, ...(matched ? receipt : {}), verifiedReport: matched} : null;
    const comparison = data.report_comparisons?.[modelId]?.[benchmarkId];
    // Rank within this one report; never fill a gap from another release.
    const reports = rank(comparison ? comparison.rows.filter(r => r.plot_eligible && Number.isFinite(r.display_value)) : (own && Number.isFinite(own.display_value) ? [own] : []));
    const exceptions = comparison ? comparison.rows.filter(r => !r.plot_eligible || !Number.isFinite(r.display_value)) : [];
    return {audit, snapshot, official, reports, own, comparison, exceptions};
  }
  if (typeof module !== 'undefined') module.exports = {selectRanking};
  else root.ModelEvalRanking = {selectRanking};
})(typeof window === 'undefined' ? globalThis : window);
