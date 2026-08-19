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
  if (typeof window === "undefined") return { window: "30d" as TimeWindow, sort: "newest" as SortMode, areas: [] as string[], topics: [] as string[], search: "" };
  const params = new URLSearchParams(window.location.search);
  const windowValue = params.get("window");
  const sortValue = params.get("sort");
  return {
    window: (windowValue === "today" || windowValue === "90d" ? windowValue : "30d") as TimeWindow,
    sort: (sortValue === "momentum" ? "momentum" : "newest") as SortMode,
    areas: params.getAll("area"),
    topics: params.getAll("topic"),
    search: params.get("q") ?? "",
  };
}

function ResourceLink({ href, label }: { href: string | null; label: string }) {
  if (!href) return <span className="resource-link unavailable">{label} unavailable</span>;
  return <a className="resource-link" href={href} target="_blank" rel="noreferrer">{label} ↗</a>;
}

function BenchmarkCard({ item, expanded, watched, onExpand, onWatch }: {
  item: BenchmarkRecord;
  expanded: boolean;
  watched: boolean;
  onExpand: () => void;
  onWatch: () => void;
}) {
  const [, month, day] = item.releasedAt.split("-");
  const monthLabel = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][Number(month) - 1];
  const displayDate = `${day} ${monthLabel}`;
  return (
    <article className={`benchmark-card${expanded ? " is-expanded" : ""}`}>
      <div className="card-date"><span>Released</span>{displayDate}</div>
      <div className="card-main">
        <div className="tag-row"><span className="area-tag">{item.area}</span>{item.topics.slice(0, 2).map((topic) => <span key={topic}>{topic}</span>)}</div>
        <h2>{item.name}</h2>
        <p className="one-line">{item.oneLine}</p>
        <div className="card-meta">
          <span className={`readiness readiness-${item.readiness.toLowerCase().replaceAll(" ", "-")}`}>{item.readiness}</span>
          <span className="adoption">{item.adoption30d === null ? "Adoption: collecting" : `↗ +${item.adoption30d} independent adopters · 30d`}</span>
          <span className="confidence">Source evidence · {item.confidence}</span>
        </div>
        <div className="resource-row">
          <ResourceLink href={item.links.report} label="Source" />
          <ResourceLink href={item.links.pdf} label="PDF" />
          {item.links.project && <ResourceLink href={item.links.project} label="Project" />}
          <ResourceLink href={item.links.code} label="Code" />
          <ResourceLink href={item.links.data} label="Data" />
        </div>
        {expanded && (
          <div className="detail-panel" id={`details-${item.id}`}>
            <div className="detail-copy">
              <section><h3>Motivation</h3><p>{item.motivation}</p></section>
              <section><h3>Construction</h3><p>{item.constructionDetail}</p></section>
            </div>
            <dl className="fact-grid">
              <div><dt>Construction</dt><dd>{item.construction}</dd></div>
              <div><dt>Annotation</dt><dd>{item.annotation}</dd></div>
              <div><dt>Capabilities</dt><dd>{item.capabilities.join(" · ")}</dd></div>
              <div><dt>Indexed</dt><dd>{item.firstSeenAt} · {item.source.type.toUpperCase()} {item.source.id}</dd></div>
            </dl>
            <div className="source-evidence">
              <h3>Source evidence</h3>
              <p>{item.evidence.snippet}</p>
              <small>{item.evidence.reasonCodes.join(" · ")} · recognition {Math.round(item.recognitionConfidence * 100)}%</small>
            </div>
            <p className="method-note">Construction, adoption, and momentum stay unknown until the source or dated observations provide evidence. Missing values are never converted to zero.</p>
          </div>
        )}
      </div>
      <div className="card-actions">
        <button className={`watch-button${watched ? " is-watched" : ""}`} onClick={onWatch} aria-pressed={watched}>{watched ? "Watching" : "Watch"}</button>
        <button className="details" onClick={onExpand} aria-expanded={expanded} aria-controls={`details-${item.id}`}>{expanded ? "Close details ↑" : "View details ↓"}</button>
      </div>
    </article>
  );
}

export default function Home() {
  const [timeWindow, setTimeWindow] = useState<TimeWindow>("30d");
  const [sort, setSort] = useState<SortMode>("newest");
  const [areas, setAreas] = useState<string[]>([]);
  const [topics, setTopics] = useState<string[]>([]);
  const [search, setSearch] = useState("");
  const [expanded, setExpanded] = useState<string[]>([]);
  const [watchlist, setWatchlist] = useState<string[]>([]);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [queryHydrated, setQueryHydrated] = useState(false);

  useEffect(() => {
    const initial = readInitialQuery();
    // URL and localStorage are browser-only; hydrate them after the server render.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setTimeWindow(initial.window);
    setSort(initial.sort);
    setAreas(initial.areas);
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
    topics.forEach((topic) => params.append("topic", topic));
    history.replaceState(null, "", `?${params.toString()}`);
  }, [timeWindow, sort, areas, topics, search, queryHydrated]);

  const results = useMemo(() => listBenchmarks({ window: timeWindow, sort, areas, topics, search }), [timeWindow, sort, areas, topics, search]);
  const activeFilterCount = areas.length + topics.length + (search ? 1 : 0);
  const clearFilters = () => { setAreas([]); setTopics([]); setSearch(""); };
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
        <div className="header-status"><span className="demo-pill">PRIMARY SOURCES</span><span className="watch-count">{watchlist.length} watching</span></div>
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
            <fieldset><legend>Area</legend><div className="filter-chips">{taxonomy.areas.map((area) => <button key={area} onClick={() => toggle(area, areas, setAreas)} className={areas.includes(area) ? "selected" : ""} aria-pressed={areas.includes(area)}>{area}</button>)}</div></fieldset>
            <fieldset><legend>Trending topic</legend><div className="filter-chips">{taxonomy.topics.slice(0, 14).map((topic) => <button key={topic} onClick={() => toggle(topic, topics, setTopics)} className={topics.includes(topic) ? "selected" : ""} aria-pressed={topics.includes(topic)}>{topic}</button>)}</div></fieldset>
            <button className="clear-button" onClick={clearFilters} disabled={!activeFilterCount}>Clear all filters</button>
          </div>
        )}

        <div className="feed-heading">
          <div><span className="signal-dot" /><h2 id="radar-title">{sort === "newest" ? "New benchmark releases" : "Rising benchmarks"}</h2><span className="result-count">{results.length} results</span></div>
          <span>Source date {benchmarkManifest.dataAsOf} · UTC · arXiv OAI-PMH</span>
        </div>

        <div className="benchmark-list" aria-live="polite">
          {results.length ? results.map((item) => <BenchmarkCard key={item.id} item={item} expanded={expanded.includes(item.id)} watched={watchlist.includes(item.id)} onExpand={() => setExpanded(expanded.includes(item.id) ? expanded.filter((id) => id !== item.id) : [...expanded, item.id])} onWatch={() => toggleWatch(item.id)} />) : (
            <div className="empty-state"><strong>No benchmarks in this view.</strong><p>Try a wider time window or clear the current filters.</p><button onClick={clearFilters}>Clear filters</button></div>
          )}
        </div>
      </section>

      <section className="method" id="method">
        <h2>How to read the tracker</h2>
        <div className="method-grid"><div><strong>Indexed</strong><p>Only explicit benchmark releases pass automatically. Ambiguous matches go to review.</p></div><div><strong>Momentum</strong><p>Recent independent adoption and attention. It remains unavailable until dated observations exist.</p></div><div><strong>Readiness</strong><p>Resource links are shown only when the primary source publishes them.</p></div></div>
      </section>

      <footer><p>{BENCHMARK_DATA_NOTICE}</p><p>Watchlist is stored only in this browser.</p></footer>
    </main>
  );
}
