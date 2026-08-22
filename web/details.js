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

  const factGrid = (items) => {
    const rows = items.filter(([, value]) => value !== null && value !== undefined && value !== "");
    if (!rows.length) return null;
    const node = document.createElement("div");
    node.className = "detail-summary";
    rows.forEach(([label, value, note]) => node.append(fact(label, String(value), note)));
    return node;
  };

  const chips = (values, limit = 8) => {
    const unique = [...new Set(values.filter(Boolean))];
    const node = document.createElement("div");
    node.className = "detail-chips";
    unique.slice(0, limit).forEach((value) => node.append(text("span", "", value)));
    if (unique.length > limit) node.append(text("span", "", `+${unique.length - limit}`));
    return node;
  };

  const measureSection = (record) => {
    const detail = record.detail || {};
    const domains = [
      ...(detail.taskBreakdown || []),
      ...(record.capabilityGroups || []),
      ...(record.applicationDomains || []),
      ...(record.topics || [])
    ];
    const protocol = detail.protocol || {};
    const compact = factGrid([
      ["TASKS", protocol.tasks],
      ["PRIMARY METRIC", protocol.primaryMetric],
      ["VERSION", record.version || record.firstRelease?.label],
      ["LANGUAGE", record.language]
    ]);
    if (!record.description && !domains.length && !compact) return null;
    const node = section("What it measures");
    if (record.description) node.append(text("p", "detail-copy", record.description));
    if (domains.length) node.append(chips(domains));
    if (compact) compact.classList.add("detail-compact-facts");
    if (compact) node.append(compact);
    return node;
  };

  const whySection = (record) => {
    if (!record.whyItMatters) return null;
    const node = section("Why it matters");
    node.append(text("p", "detail-copy", record.whyItMatters));
    return node;
  };

  const renderRadarDetails = (record, panel) => {
    panel.replaceChildren();
    const measures = measureSection(record);
    if (measures) panel.append(measures);
    const why = whySection(record);
    if (why) panel.append(why);
  };

  const modelCoverage = (record) => {
    const groups = record.detail?.modelCoverage || [];
    if (!groups.length) return null;
    const node = section("Models tested by the benchmark authors");
    const rows = document.createElement("div");
    rows.className = "model-coverage";
    groups.slice(0, 6).forEach((group) => {
      const row = document.createElement("div");
      row.append(text("strong", "", group.provider), text("span", "", group.models.join(" · ")));
      rows.append(row);
    });
    node.append(rows);
    if (record.detail?.modelCoverageNote) node.append(text("p", "detail-note", record.detail.modelCoverageNote));
    return node;
  };

  const reportReferences = (record) => {
    const reports = record.modelReportReferences || [];
    if (!reports.length) return null;
    const node = section("Used by model labs");
    const links = document.createElement("div");
    links.className = "detail-links";
    reports.slice(0, 8).forEach((report) => {
      const label = [report.provider, report.model].filter(Boolean).join(" · ") || report.sourceId || "Model report";
      const item = link(label, report.url);
      if (item) links.append(item);
    });
    node.append(links);
    return node;
  };

  const renderLibraryDetails = (record, panel) => {
    const detail = record.detail || {};
    const leaderboard = detail.leaderboard || {};
    const independent = detail.adoption?.independentOrganizations?.length || 0;
    panel.replaceChildren();
    const summary = factGrid([
      ["INDEPENDENT ADOPTION", independent ? `${independent} tracked` : null, "Source-linked organizations"],
      ["BEST COMPARABLE", leaderboard.bestScore == null ? null : `${leaderboard.bestScore} · ${leaderboard.primaryMetric || "score"}`, leaderboard.bestSystem],
      ["SATURATION", leaderboard.saturationStatus, leaderboard.assessment]
    ]);
    if (summary) panel.append(summary);
    const reportsNode = reportReferences(record);
    const coverageNode = modelCoverage(record);
    if (reportsNode) panel.append(reportsNode);
    if (coverageNode) panel.append(coverageNode);
    const measures = measureSection(record);
    if (measures) panel.append(measures);
    const why = whySection(record);
    if (why) panel.append(why);
  };

  window.renderBenchmarkDetails = (record, panel, surface) => {
    if (!record || !panel) return;
    if (surface === "radar") renderRadarDetails(record, panel);
    else renderLibraryDetails(record, panel);
  };
})();
