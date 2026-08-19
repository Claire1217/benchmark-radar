"use client";

import { useEffect, useMemo, useState } from "react";
import { BENCHMARK_DATA_NOTICE, type BenchmarkDemoRecord } from "./benchmarks";
import { demoManifest, listBenchmarks, taxonomy, type SortMode, type TimeWindow } from "./repository";

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
  item: BenchmarkDemoRecord;
  expanded: boolean;
  watched: boolean;
  onExpand: () => void;
  onWatch: () => void;
}) {
  const [, month, day] = item.firstSeen.split("-");
  const monthLabel = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][Number(month) - 1];
  const displayDate = `${day} ${monthLabel}`;
  return (
    <article className={`benchmark-card${expanded ? " is-expanded" : ""}`}>
      <div className="card-date"><span>First seen</span>{displayDate}</div>
      <div className="card-main">
        <div className="tag-row"><span className="area-tag">{item.area}</span>{item.topics.slice(0, 2).map((topic) => <span key={topic}>{topic}</span>)}</div>
        <h2>{item.name}</h2>
        <p className="one-line">{item.oneLine}</p>
        <div className="card-meta">
          <span className={`readiness readiness-${item.readiness.toLowerCase().replaceAll(" ", "-")}`}>{item.readiness}</span>
          <span className="adoption">↗ +{item.adoption30d} independent adopters · 30d</span>
          <span className="confidence">{item.confidence} confidence</span>
        </div>
        <div className="resource-row">
          <ResourceLink href={item.links.paper} label="Paper" />
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
              <div><dt>Momentum</dt><dd>{item.heat}/100 · {item.confidence} confidence</dd></div>
            </dl>
            <div className="metric-strip" aria-label="Simulated benchmark metrics">
              {item.metrics.map((metric) => <div key={metric.name}><span>{metric.name}</span><strong>{metric.value}</strong><small>{metric.note ?? "Demo"}</small></div>)}
            </div>
            <p className="method-note">Momentum is simulated for this prototype and kept separate from readiness. Missing signals are never treated as zero.</p>
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
        <a className="brand" href="#top" aria-label="Benchmark Radar home"><span className="brand-mark">B/</span>Benchmark Radar</a>
        <nav className="topnav" aria-label="Page sections"><a href="#radar">Radar</a><a href="#method">Method</a></nav>
        <div className="header-status"><span className="demo-pill">DEMO DATA</span><span className="watch-count">{watchlist.length} watching</span></div>
      </header>

      <section className="hero">
        <div>
          <p className="eyebrow">Research infrastructure, tracked daily</p>
          <h1>See where research<br />is becoming real.</h1>
        </div>
        <div className="hero-side">
          <p>Track the benchmarks shaping the next research frontier — from first release to real adoption.</p>
          <div className="hero-stat"><strong>12</strong><span>demo benchmarks<br />across 5 areas</span></div>
        </div>
      </section>

      <section className="trend-band" aria-label="Simulated research momentum insights">
        <div><span>01</span><strong>AI Scientist</strong><p>Surging · 3 new benchmarks</p></div>
        <div><span>02</span><strong>CAD</strong><p>Growing · runnable artifacts rising</p></div>
        <div><span>03</span><strong>Agent Safety</strong><p>Early signal · medium confidence</p></div>
        <p className="trend-disclaimer">Illustrative field signals</p>
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
          <div><span className="signal-dot" /><h2 id="radar-title">{sort === "newest" ? "New benchmarks" : "Rising benchmarks"}</h2><span className="result-count">{results.length} results</span></div>
          <span>Demo snapshot · {demoManifest.dataAsOf} · Brisbane</span>
        </div>

        <div className="benchmark-list" aria-live="polite">
          {results.length ? results.map((item) => <BenchmarkCard key={item.id} item={item} expanded={expanded.includes(item.id)} watched={watchlist.includes(item.id)} onExpand={() => setExpanded(expanded.includes(item.id) ? expanded.filter((id) => id !== item.id) : [...expanded, item.id])} onWatch={() => toggleWatch(item.id)} />) : (
            <div className="empty-state"><strong>No benchmarks in this view.</strong><p>Try a wider time window or clear the current filters.</p><button onClick={clearFilters}>Clear filters</button></div>
          )}
        </div>
      </section>

      <section className="method" id="method">
        <p className="eyebrow">How to read this radar</p>
        <div className="method-grid"><div><span>01</span><h2>Newest is discovery.</h2><p>Every high-confidence Benchmark enters the time-ordered feed. Popularity never decides whether it is visible.</p></div><div><span>02</span><h2>Momentum is adoption.</h2><p>Adoption, GitHub, Hugging Face and citations are normalized by field and age. Missing evidence stays missing.</p></div><div><span>03</span><h2>Readiness is separate.</h2><p>Paper only, Inspectable, Runnable and Maintained describe whether others can verify and reuse the evaluation.</p></div></div>
      </section>

      <footer><p>{BENCHMARK_DATA_NOTICE}</p><p>Watchlist is stored only in this browser.</p></footer>
    </main>
  );
}
