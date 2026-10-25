/* Official ranks and a selected publisher's comparison never share score inputs. */
(function (root) {
  'use strict';
  function selectRanking(data, benchmarkId, modelId) {
    // Compatibility is reviewed for this model's reported protocol, not inherited
    // from another publisher just because the benchmark label is the same.
    const audit = data.model_benchmark_audits
      ? data.model_benchmark_audits[modelId]?.[benchmarkId]
      : data.benchmark_audits?.[benchmarkId];
    const snapshot = audit?.coreEligible ? data.leaderboard_snapshots?.[audit.snapshotId || benchmarkId] : null;
    const lower = data.benchmarks[benchmarkId]?.direction === 'lower_is_better';
    const closest = data.benchmarks[benchmarkId]?.direction === 'closer_to_zero_is_better';
    const rankable = lower || closest || data.benchmarks[benchmarkId]?.direction === 'higher_is_better';
    const orderValue = row => closest ? Math.abs(row.display_value) : row.display_value;
    const scoreDifference = (a, b) => (lower || closest) ? orderValue(a) - orderValue(b) : orderValue(b) - orderValue(a);
    const best = new Map();
    for (const run of snapshot?.rows || []) {
      if (run.provenance !== 'benchmark_evaluation' || !Number.isFinite(run.display_value)) continue;
      const previous = best.get(run.name);
      if (!previous || scoreDifference(run, previous) < 0) best.set(run.name, run);
    }
    const byScore = (a, b) => scoreDifference(a, b) || a.name.localeCompare(b.name);
    // Descriptive axes have no best run or best model. Preserve source order
    // and every measured run instead of inventing a direction or a winner.
    const rank = rows => rankable ? rows.sort(byScore).map((row, i, sorted) => ({...row, rank: sorted.findIndex(r => orderValue(r) === orderValue(row)) + 1})) : rows.map(row => ({...row, rank: null}));
    const official = rank(rankable ? [...best.values()] : (snapshot?.rows || []).filter(r => r.provenance === 'benchmark_evaluation' && Number.isFinite(r.display_value)));
    const selected = (data.charts[benchmarkId]?.rows || []).find(r => r.model_id === modelId);
    const receipt = data.report_audits?.[benchmarkId]?.[modelId];
    const matched = receipt?.status === 'matched_report' && receipt.value === selected?.display_value;
    const own = selected ? {...selected, name: data.models[modelId].name, ...(matched ? receipt : {}), verifiedReport: matched} : null;
    const comparison = data.report_comparisons?.[modelId]?.[benchmarkId];
    // Rank within this one report; never fill a gap from another release.
    const reports = rank(comparison ? comparison.rows.filter(r => r.plot_eligible && Number.isFinite(r.display_value)) : (own && Number.isFinite(own.display_value) ? [own] : []));
    const exceptions = comparison ? comparison.rows.filter(r => !r.plot_eligible || !Number.isFinite(r.display_value)) : [];
    return {audit, snapshot, official, reports, own, comparison, exceptions, rankable};
  }
  if (typeof module !== 'undefined') module.exports = {selectRanking};
  else root.ModelEvalRanking = {selectRanking};
})(typeof window === 'undefined' ? globalThis : window);
