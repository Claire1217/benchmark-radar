"use client";

import { useEffect, useMemo, useState } from "react";
import { BENCHMARK_DATA_NOTICE, type BenchmarkRecord } from "./benchmarks";
import { benchmarkManifest, listBenchmarks, taxonomy, type SortMode, type TimeWindow } from "./repository";

const WATCHLIST_KEY = "benchmark-radar:watchlist:v1";
const windows: { id: TimeWindow; label: string }[] = [
  { id: "today", label: "Today" },
  { id: "30d", label: "30 days" },
  { id: "90d", label: "90 days" },
];

function readInitialQuery() {
  if (typeof window === "undefined") return { window: "30d" as TimeWindow, sort: "newest" as SortMode, areas: [] as string[], domains: [] as string[], topics: [] as string[], search: "" };
  const params = new URLSearchParams(window.location.search);
  const windowValue = params.get("window");
  const sortValue = params.get("sort");
  return {
    window: (windowValue === "today" || windowValue === "90d" ? windowValue : "30d") as TimeWindow,
    sort: (sortValue === "momentum" ? "momentum" : "newest") as SortMode,
    areas: params.getAll("area"),
    domains: params.getAll("domain"),
    topics: params.getAll("topic"),
    search: params.get("q") ?? "",
  };
}

function ResourceLink({ href, label }: { href: string | null; label: string }) {
  if (!href) return <span className="resource-link unavailable">{label} unavailable</span>;
  return <a className="resource-link" href={href} target="_blank" rel="noreferrer">{label} ↗</a>;
}

function compactAttention(item: BenchmarkRecord) {
  const attention = item.attention;
  if (!attention) return "Attention: collecting";
  if (attention.hfPaperUpvotes !== null) return `${attention.hfPaperUpvotes.toLocaleString()} HF votes`;
  if (attention.githubStars !== null) return `${attention.githubStars.toLocaleString()} GitHub stars`;
  if (attention.hfDatasetDownloads !== null) return `${attention.hfDatasetDownloads.toLocaleString()} dataset downloads`;
  return "Attention: no public signal yet";
}

function BenchmarkCard({ item, window, expanded, watched, onExpand, onWatch }: {
  item: BenchmarkRecord;
  window: TimeWindow;
  expanded: boolean;
  watched: boolean;
  onExpand: () => void;
  onWatch: () => void;
}) {
  const [, month, day] = item.releasedAt.split("-");
  const monthLabel = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][Number(month) - 1];
  const displayDate = `${day} ${monthLabel}`;
  const rank = item.ranking?.[window];
  const datasetRank = rank?.datasetDownloadRank && rank.datasetRankPopulation
    ? `#${rank.datasetDownloadRank} of ${rank.datasetRankPopulation}`
    : "Not ranked";
  return (
    <article className={`benchmark-card${expanded ? " is-expanded" : ""}`}>
      <div className="card-date"><span>Released</span>{displayDate}</div>
      <div className="card-main">
        <div className="tag-row"><span className="area-tag">{item.primaryDomain}</span>{item.topics.slice(0, 1).map((topic) => <span key={topic}>{topic}</span>)}</div>
        <h2>{item.name}</h2>
        <p className="one-line">{item.oneLine}</p>
        <div className="card-meta">
          <span className={`readiness readiness-${item.readiness.toLowerCase().replaceAll(" ", "-")}`}>{item.readiness}</span>
          <span className="adoption">{rank?.rank ? `Attention #${rank.rank} · ${window}` : compactAttention(item)}</span>
          {rank?.rank && <span className="confidence">{compactAttention(item)}</span>}
        </div>
        <div className="resource-row">
          <ResourceLink href={item.links.report} label="Source" />
          <ResourceLink href={item.links.pdf} label="PDF" />
          {item.links.project && <ResourceLink href={item.links.project} label="Project" />}
          {item.links.hfPaper && <ResourceLink href={item.links.hfPaper} label="HF" />}
          <ResourceLink href={item.links.code} label="Code" />
          <ResourceLink href={item.links.data} label="Data" />
        </div>
        {expanded && (
          <div className="detail-panel" id={`details-${item.id}`}>
            <div className="detail-copy">
              <section><h3>Motivation</h3><p>{item.motivation ?? item.oneLine}</p></section>
              <section><h3>Construction</h3><p>{item.constructionDetail ?? "Unknown — the source does not provide enough structured evidence yet."}</p></section>
            </div>
            <dl className="fact-grid">
              <div><dt>Domain</dt><dd>{item.applicationDomains.join(" · ")}</dd></div>
              <div><dt>Industry</dt><dd>{item.industrySectors.join(" · ") || "Not specified"}</dd></div>
              <div><dt>Construction</dt><dd>{item.construction}</dd></div>
              <div><dt>Annotation</dt><dd>{item.annotation}</dd></div>
              <div><dt>Capabilities</dt><dd>{item.capabilities.join(" · ")}</dd></div>
              <div><dt>Indexed</dt><dd>{item.firstSeenAt} · {item.source.type.toUpperCase()} {item.source.id}</dd></div>
            </dl>
            <div className="metric-strip" aria-label={`${window} attention signals`}>
              <div><span>HF PAPER</span><strong>{item.attention?.hfPaperUpvotes?.toLocaleString() ?? "—"}</strong><small>votes</small></div>
              <div><span>GITHUB</span><strong>{item.attention?.githubStars?.toLocaleString() ?? "—"}</strong><small>stars</small></div>
              <div><span>HF DATASET</span><strong>{item.attention?.hfDatasetDownloads?.toLocaleString() ?? "—"}</strong><small>downloads · {datasetRank}</small></div>
            </div>
            <div className="source-evidence">
              <h3>Source evidence</h3>
              <p>{item.evidence.snippet}</p>
              <small>{item.evidence.reasonCodes.join(" · ")} · recognition {Math.round(item.recognitionConfidence * 100)}%</small>
            </div>
            <p className="method-note">Attention uses dated deltas when history exists; until then it uses current public levels. Missing signals are never converted to zero. Attention is not quality.</p>
          </div>
        )}
      </div>
      <div className="card-actions">
        <button className={`watch-button${watched ? " is-watched" : ""}`} onClick={onWatch} aria-pressed={watched}>{watched ? "Saved" : "Save"}</button>
        <button className="details" onClick={onExpand} aria-expanded={expanded} aria-controls={`details-${item.id}`}>{expanded ? "Close details ↑" : "View details ↓"}</button>
      </div>
    </article>
  );
}

export default function Home() {
  const [timeWindow, setTimeWindow] = useState<TimeWindow>("30d");
  const [sort, setSort] = useState<SortMode>("newest");
  const [areas, setAreas] = useState<string[]>([]);
  const [domains, setDomains] = useState<string[]>([]);
  const [topics, setTopics] = useState<string[]>([]);
  const [search, setSearch] = useState("");
  const [expanded, setExpanded] = useState<string[]>([]);
  const [watchlist, setWatchlist] = useState<string[]>([]);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [queryHydrated, setQueryHydrated] = useState(false);
  const [visibleCount, setVisibleCount] = useState(80);

  useEffect(() => {
    const initial = readInitialQuery();
    // URL and localStorage are browser-only; hydrate them after the server render.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setTimeWindow(initial.window);
    setSort(initial.sort);
    setAreas(initial.areas);
    setDomains(initial.domains);
    setTopics(initial.topics);
    setSearch(initial.search);
    setQueryHydrated(true);
    try { setWatchlist(JSON.parse(localStorage.getItem(WATCHLIST_KEY) ?? "[]")); } catch { setWatchlist([]); }
  }, []);

  useEffect(() => {
    if (!queryHydrated) return;
    const params = new URLSearchParams();
    params.set("window", timeWindow);
    params.set("sort", sort);
    if (search) params.set("q", search);
    areas.forEach((area) => params.append("area", area));
    domains.forEach((domain) => params.append("domain", domain));
    topics.forEach((topic) => params.append("topic", topic));
    history.replaceState(null, "", `?${params.toString()}`);
  }, [timeWindow, sort, areas, domains, topics, search, queryHydrated]);

  const results = useMemo(() => listBenchmarks({ window: timeWindow, sort, areas, domains, topics, search }), [timeWindow, sort, areas, domains, topics, search]);
  const visibleResults = results.slice(0, visibleCount);
  const activeFilterCount = areas.length + domains.length + topics.length + (search ? 1 : 0);
  const clearFilters = () => { setAreas([]); setDomains([]); setTopics([]); setSearch(""); };
  const toggle = (value: string, selected: string[], setter: (values: string[]) => void) => setter(selected.includes(value) ? selected.filter((item) => item !== value) : [...selected, value]);
  const toggleWatch = (id: string) => {
    const next = watchlist.includes(id) ? watchlist.filter((item) => item !== id) : [...watchlist, id];
    setWatchlist(next);
    localStorage.setItem(WATCHLIST_KEY, JSON.stringify(next));
  };

  return (
    <main className="site-shell">
      <header className="topbar" id="top">
        <a className="brand" href="#top" aria-label="Benchmark Radar home">Benchmark Radar</a>
        <nav className="topnav" aria-label="Page sections"><a href="#radar">Radar</a><a href="#method">Method</a></nav>
        <div className="header-status"><span className="demo-pill">PRIMARY SOURCES</span><span className="watch-count">{watchlist.length} saved</span></div>
      </header>

      <section className="hero">
        <div>
          <h1>Track emerging benchmarks.</h1>
          <p>See what is new, what is gaining adoption, and what is ready to run.</p>
        </div>
        <div className="hero-summary"><strong>{benchmarkManifest.recordCount}</strong><span>verified releases in this snapshot<br />{benchmarkManifest.run.papersFetched} source papers checked</span></div>
      </section>

      <section className="radar" id="radar" aria-labelledby="radar-title">
        <div className="control-row">
          <div className="control-group"><span className="control-label">Time window</span><div className="segmented">{windows.map((item) => <button key={item.id} onClick={() => setTimeWindow(item.id)} className={timeWindow === item.id ? "active" : ""} aria-pressed={timeWindow === item.id}>{item.label}</button>)}</div></div>
          <div className="control-group"><span className="control-label">Sort by</span><div className="segmented"><button onClick={() => setSort("newest")} className={sort === "newest" ? "active" : ""} aria-pressed={sort === "newest"}>Newest</button><button onClick={() => setSort("momentum")} className={sort === "momentum" ? "active" : ""} aria-pressed={sort === "momentum"}>Momentum</button></div></div>
          <button className="filter-toggle" onClick={() => setFiltersOpen(!filtersOpen)} aria-expanded={filtersOpen}>Filters {activeFilterCount ? `(${activeFilterCount})` : ""} {filtersOpen ? "↑" : "↓"}</button>
        </div>

        {filtersOpen && (
          <div className="filter-panel">
            <label className="search-field"><span>Search this view</span><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="RSI, CAD, manipulation…" /></label>
            <fieldset><legend>Application domain</legend><div className="filter-chips">{taxonomy.domains.map((domain) => <button key={domain} onClick={() => toggle(domain, domains, setDomains)} className={domains.includes(domain) ? "selected" : ""} aria-pressed={domains.includes(domain)}>{domain}</button>)}</div></fieldset>
            <fieldset><legend>AI area / topic</legend><div className="filter-chips">{[...taxonomy.areas, ...taxonomy.topics.slice(0, 8)].map((value) => <button key={value} onClick={() => taxonomy.areas.includes(value) ? toggle(value, areas, setAreas) : toggle(value, topics, setTopics)} className={areas.includes(value) || topics.includes(value) ? "selected" : ""} aria-pressed={areas.includes(value) || topics.includes(value)}>{value}</button>)}</div></fieldset>
            <button className="clear-button" onClick={clearFilters} disabled={!activeFilterCount}>Clear all filters</button>
          </div>
        )}

        <div className="feed-heading">
          <div><span className="signal-dot" /><h2 id="radar-title">{sort === "newest" ? "New benchmark releases" : "Rising benchmarks"}</h2><span className="result-count">{results.length} results</span></div>
          <span>Updated {benchmarkManifest.dataAsOf} · source releases through {benchmarkManifest.latestSourceDate ?? benchmarkManifest.dataAsOf}</span>
        </div>

        <div className="benchmark-list" aria-live="polite">
          {results.length ? visibleResults.map((item) => <BenchmarkCard key={item.id} item={item} window={timeWindow} expanded={expanded.includes(item.id)} watched={watchlist.includes(item.id)} onExpand={() => setExpanded(expanded.includes(item.id) ? expanded.filter((id) => id !== item.id) : [...expanded, item.id])} onWatch={() => toggleWatch(item.id)} />) : (
            <div className="empty-state"><strong>No benchmarks in this view.</strong><p>Try a wider time window or clear the current filters.</p><button onClick={clearFilters}>Clear filters</button></div>
          )}
        </div>
        {visibleResults.length < results.length && <button className="load-more" onClick={() => setVisibleCount((count) => count + 80)}>Show 80 more</button>}
      </section>

      <section className="method" id="method">
        <h2>How to read the tracker</h2>
        <div className="method-grid"><div><strong>Indexed</strong><p>Only explicit benchmark releases pass automatically. Ambiguous matches go to review.</p></div><div><strong>Attention</strong><p>HF votes, GitHub stars, and HF dataset downloads. Window deltas replace current levels as daily history accumulates.</p></div><div><strong>Readiness</strong><p>Resource links are shown only when the primary source publishes them. Popularity never changes readiness.</p></div></div>
      </section>

      <footer><p>{BENCHMARK_DATA_NOTICE}</p><p>Saved items are stored only in this browser.</p></footer>
    </main>
  );
}
