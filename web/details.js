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

  const validCopy = (record) => {
    if (record.description) return record.description;
    if (record.constructionDetail && !record.constructionDetail.startsWith("Unknown")) return record.constructionDetail;
    return null;
  };

  const measureSection = (record) => {
    const detail = record.detail || {};
    const node = section("What it measures");
    const copy = validCopy(record);
    if (copy) node.append(text("p", "detail-copy", copy));
    const domains = detail.taskBreakdown?.length ? detail.taskBreakdown : record.applicationDomains || [];
    if (domains.length) node.append(chips(domains));
    const protocol = detail.protocol || {};
    const compact = factGrid([
      ["TASKS", protocol.tasks],
      ["PRIMARY METRIC", protocol.primaryMetric],
      ["VERSION", record.version || record.firstRelease?.label],
      ["LANGUAGE", record.language]
    ]);
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

  const availabilitySection = (record) => {
    const a = record.availability || {};
    const resources = [
      ["Paper", record.links?.paper || record.links?.report, Boolean(record.links?.paper || record.links?.report)],
      [a.hfDatasetStatus === "sample_only" ? "Data sample" : "Data", record.links?.data, a.hfDatasetStatus === "available" || Boolean(record.links?.data)],
      ["Code", record.links?.code, a.githubStatus === "available" || Boolean(record.links?.code)]
    ];
    const node = section("Resources");
    const list = document.createElement("div");
    list.className = "availability-list";
    resources.forEach(([label, url, available]) => {
      const item = document.createElement(url && available ? "a" : "span");
      item.className = available ? "available" : "not-found";
      item.textContent = `${label} ${available ? "✓" : "Not found"}`;
      if (item.tagName === "A") {
        item.href = url;
        item.target = "_blank";
        item.rel = "noreferrer";
      }
      list.append(item);
    });
    node.append(list);
    return node;
  };

  const provenance = (record) => {
    const node = document.createElement("details");
    node.className = "detail-provenance";
    node.append(text("summary", "", "Sources & provenance"));
    if (record.evidence?.snippet) node.append(text("p", "evidence", record.evidence.snippet));
    const links = document.createElement("div");
    links.className = "detail-links";
    [
      link("Original source", record.links?.paper || record.links?.report),
      link("Project", record.links?.project),
      link("Hugging Face paper", record.links?.hfPaper)
    ].filter(Boolean).forEach((item) => links.append(item));
    if (links.childElementCount) node.append(links);
    return node;
  };

  const radarSummary = (record) => {
    const state = window.benchmarkRadarState;
    const rank = record.ranking?.[state?.window];
    const attention = rank?.rank ? `#${rank.rank} · ${state.window}` : record.attention?.hfPaperUpvotes != null ? `${record.attention.hfPaperUpvotes} HF votes` : null;
    const assets = [record.links?.paper || record.links?.report, record.links?.data, record.links?.code].filter(Boolean).length;
    return factGrid([
      ["CURRENT ATTENTION", attention, "Public visibility, not quality"],
      ["PUBLIC RESOURCES", `${assets} found`, "Paper · data · code"],
      ["READINESS", record.readiness, "Availability at first review"]
    ]);
  };

  const renderRadarDetails = (record, panel) => {
    panel.replaceChildren();
    const summary = radarSummary(record);
    if (summary) panel.append(summary);
    panel.append(measureSection(record));
    const why = whySection(record);
    if (why) panel.append(why);
    panel.append(availabilitySection(record), provenance(record));
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
    const node = section("Tracked model reports");
    const links = document.createElement("div");
    links.className = "detail-links";
    reports.slice(0, 8).forEach((report) => {
      const label = [report.provider, report.model].filter(Boolean).join(" · ") || report.sourceId || "Model report";
      const item = link(label, report.url);
      if (item) links.append(item);
    });
    node.append(links, text("p", "detail-note", "A source link shows reported use; it does not by itself prove an independently reproduced score."));
    return node;
  };

  const publisherSection = (record) => {
    const publishers = record.publishers || [];
    if (!publishers.length) return null;
    const node = section("Published by");
    const links = document.createElement("div");
    links.className = "detail-links";
    publishers.forEach((publisher) => {
      const item = link(publisher.name, publisher.sourceUrl);
      if (item) links.append(item);
    });
    node.append(links, text("p", "detail-note", "Publisher provenance is separate from model-lab adoption."));
    return node;
  };

  const renderLibraryDetails = (record, panel) => {
    const detail = record.detail || {};
    const leaderboard = detail.leaderboard || {};
    const independent = detail.adoption?.independentOrganizations?.length || 0;
    const reports = record.modelReportReferences?.length || 0;
    panel.replaceChildren();
    const summary = factGrid([
      ["INDEPENDENT ADOPTION", independent ? `${independent} tracked` : reports ? `${reports} report reference${reports === 1 ? "" : "s"}` : null, independent ? "Source-linked organizations" : "Official model reports"],
      ["BEST COMPARABLE", leaderboard.bestScore == null ? null : `${leaderboard.bestScore} · ${leaderboard.primaryMetric || "score"}`, leaderboard.bestSystem],
      ["SATURATION", leaderboard.saturationStatus, leaderboard.assessment]
    ]);
    if (summary) panel.append(summary);
    const publisherNode = publisherSection(record);
    const reportsNode = reportReferences(record);
    const coverageNode = modelCoverage(record);
    if (publisherNode) panel.append(publisherNode);
    if (reportsNode) panel.append(reportsNode);
    if (coverageNode) panel.append(coverageNode);
    panel.append(measureSection(record));
    const why = whySection(record);
    if (why) panel.append(why);
    panel.append(availabilitySection(record), provenance(record));
  };

  window.renderBenchmarkDetails = (record, panel, surface) => {
    if (!record || !panel) return;
    if (surface === "radar") renderRadarDetails(record, panel);
    else renderLibraryDetails(record, panel);
  };
})();
