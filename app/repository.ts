import { benchmarks, type BenchmarkDemoRecord } from "./benchmarks";

export type TimeWindow = "today" | "30d" | "90d";
export type SortMode = "newest" | "momentum";
export type BenchmarkQuery = {
  window: TimeWindow;
  sort: SortMode;
  areas: string[];
  topics: string[];
  search: string;
};

export const demoManifest = {
  schemaVersion: "1.0-demo",
  dataAsOf: "2026-08-19",
  timezone: "Australia/Brisbane",
  generatedAt: "2026-08-19T13:40:00+10:00",
  isDemo: true,
};

const daysAgo = (date: string) => {
  const anchor = new Date(`${demoManifest.dataAsOf}T00:00:00+10:00`).getTime();
  const target = new Date(`${date}T00:00:00+10:00`).getTime();
  return Math.floor((anchor - target) / 86_400_000);
};

export const taxonomy = {
  areas: Array.from(new Set(benchmarks.map((item) => item.area))).sort(),
  topics: Array.from(new Set(benchmarks.flatMap((item) => item.topics))).sort(),
};

export interface BenchmarkRepository {
  getManifest(): typeof demoManifest;
  listBenchmarks(query: BenchmarkQuery): BenchmarkDemoRecord[];
  getBenchmark(id: string): BenchmarkDemoRecord | null;
  listTaxonomy(): typeof taxonomy;
}

export class StaticJsonRepository implements BenchmarkRepository {
  getManifest() {
    return demoManifest;
  }

  listTaxonomy() {
    return taxonomy;
  }

  listBenchmarks(query: BenchmarkQuery): BenchmarkDemoRecord[] {
    const maxAge = query.window === "today" ? 0 : query.window === "30d" ? 30 : 90;
    const needle = query.search.trim().toLowerCase();

    return benchmarks
      .filter((item) => daysAgo(item.firstSeen) <= maxAge)
      .filter((item) => !query.areas.length || query.areas.includes(item.area))
      .filter((item) => !query.topics.length || item.topics.some((topic) => query.topics.includes(topic)))
      .filter((item) => {
        if (!needle) return true;
        return [item.name, item.oneLine, item.area, ...item.topics, ...item.capabilities]
          .join(" ")
          .toLowerCase()
          .includes(needle);
      })
      .sort((a, b) => query.sort === "newest"
        ? b.firstSeen.localeCompare(a.firstSeen)
        : b.heat - a.heat || b.adoption30d - a.adoption30d);
  }

  getBenchmark(id: string) {
    return benchmarks.find((item) => item.id === id) ?? null;
  }
}

export const benchmarkRepository = new StaticJsonRepository();

export const listBenchmarks = (query: BenchmarkQuery) =>
  benchmarkRepository.listBenchmarks(query);

export function getBenchmark(id: string) {
  return benchmarkRepository.getBenchmark(id);
}
