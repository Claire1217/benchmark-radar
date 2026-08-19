(function () {
  const text = (tag, className, value) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    node.textContent = value;
    return node;
  };

  const section = (title) => {
    const node = document.createElement("section");
    node.className = "detail-section";
    node.append(text("h3", "", title));
    return node;
  };

  const link = (label, url) => {
    if (!url || !/^https:\/\//.test(url)) return null;
    const node = text("a", "detail-link", `${label} ↗`);
    node.href = url;
    node.target = "_blank";
    node.rel = "noreferrer";
    return node;
  };

  const fact = (label, value, note) => {
    const node = document.createElement("div");
    node.append(text("small", "", label), text("strong", "", value));
    if (note) node.append(text("span", "", note));
    return node;
  };

  const chips = (values) => {
    const node = document.createElement("div");
    node.className = "detail-chips";
    values.forEach((value) => node.append(text("span", "", value)));
    return node;
  };

  function renderDetails(record, panel) {
    const detail = record.detail || {};
    const leaderboard = detail.leaderboard || {};
    const adopters = detail.adoption?.independentOrganizations || record.usageObservations || [];
    const best = leaderboard.bestScore == null ? "Not tracked" : `${leaderboard.bestScore} · ${leaderboard.primaryMetric || "best reported"}`;
    const summary = document.createElement("div");
    summary.className = "detail-summary";
    summary.append(
      fact("INDEPENDENT ADOPTION", adopters.length ? `${adopters.length} tracked` : "Not yet recorded", "Source-linked organizations"),
      fact("BEST COMPARABLE SCORE", best, leaderboard.bestSystem || "Comparable result unavailable"),
      fact("SATURATION", leaderboard.saturationStatus || "Unknown", leaderboard.assessment || "No sourced assessment"),
      fact("READINESS", record.readiness || "Unknown", record.evaluationMode === "score_submission" ? "Accepts comparable submissions" : "Artifact availability")
    );
    panel.replaceChildren(summary);

    const testValues = [...(detail.taskBreakdown || []), ...(record.capabilities || []).filter((value) => value !== "Evaluation")];
    if (record.constructionDetail || testValues.length) {
      const node = section("What it tests");
      if (record.constructionDetail && !record.constructionDetail.startsWith("Unknown")) node.append(text("p", "detail-copy", record.constructionDetail));
      if (testValues.length) node.append(chips([...new Set(testValues)]));
      panel.append(node);
    }

    if (detail.modelCoverage?.length) {
      const node = section("Models in the source evaluation");
      const rows = document.createElement("div");
      rows.className = "model-coverage";
      detail.modelCoverage.forEach((group) => {
        const row = document.createElement("div");
        row.append(text("strong", "", group.provider), text("span", "", group.models.join(" · ")));
        rows.append(row);
      });
      node.append(rows);
      if (detail.modelCoverageNote) node.append(text("p", "detail-note", detail.modelCoverageNote));
      panel.append(node);
    }

    if (Object.keys(detail.protocol || {}).length || leaderboard.bestScore != null) {
      const node = section("Score & protocol");
      const grid = document.createElement("div");
      grid.className = "protocol-grid";
      const protocol = detail.protocol || {};
      const rows = [
        ["Best", leaderboard.bestScore == null ? null : `${leaderboard.bestScore} · ${leaderboard.bestSystem}`],
        ["Mean", leaderboard.meanScore == null ? null : String(leaderboard.meanScore)],
        ["Metric", protocol.comparisonMetric || protocol.primaryMetric],
        ["Tasks", protocol.tasks == null ? null : String(protocol.tasks)],
        ["Conditions", protocol.conditions?.join(" · ")],
        ["Aggregation", protocol.aggregation],
        ["Repeated runs", protocol.runs],
        ["Tools", protocol.tools]
      ].filter(([, value]) => value);
      rows.forEach(([label, value]) => grid.append(fact(label.toUpperCase(), value)));
      node.append(grid);
      const source = link(`Result source${leaderboard.asOf ? ` · ${leaderboard.asOf}` : ""}`, leaderboard.sourceUrl);
      if (source) node.append(source);
      panel.append(node);
    }

    const resources = [
      link("Paper", record.links?.paper || record.links?.report),
      link("Data", record.links?.data),
      link("Code / evaluator", record.links?.code),
      link("Project", record.links?.project),
      link("Leaderboard", detail.leaderboardUrl),
      link("Submit a result", detail.submissionUrl)
    ].filter(Boolean);
    if (resources.length) {
      const node = section("Run or inspect it");
      const links = document.createElement("div");
      links.className = "detail-links";
      resources.forEach((item) => links.append(item));
      node.append(links);
      panel.append(node);
    }

    if (detail.adoption?.note) panel.append(text("p", "detail-note", detail.adoption.note));
    panel.append(text("p", "evidence", record.evidence?.snippet || "Source evidence unavailable."));
  }

  function hydrate() {
    const state = window.benchmarkRadarState;
    if (!state) return;
    const records = [...(state.benchmarks || []), ...(state.library || [])];
    document.querySelectorAll(".benchmark-card:not([data-details-hydrated])").forEach((card) => {
      card.dataset.detailsHydrated = "true";
      const record = records.find((item) => item.id === card.dataset.id);
      const panel = card.querySelector(".details-panel");
      if (record && panel) renderDetails(record, panel);
    });
  }

  new MutationObserver(hydrate).observe(document.documentElement, { childList: true, subtree: true });
  hydrate();
})();
