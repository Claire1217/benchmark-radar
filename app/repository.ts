import { benchmarkSnapshot, benchmarks, type BenchmarkRecord } from "./benchmarks";

export type TimeWindow = "today" | "30d" | "90d";
export type SortMode = "newest" | "momentum";
export type BenchmarkQuery = {
  window: TimeWindow;
  sort: SortMode;
  areas: string[];
  domains: string[];
  topics: string[];
  search: string;
};

export const benchmarkManifest = benchmarkSnapshot.manifest;

const daysAgo = (date: string) => {
  const anchor = new Date(`${benchmarkManifest.dataAsOf}T00:00:00Z`).getTime();
  const target = new Date(`${date}T00:00:00Z`).getTime();
  return Math.floor((anchor - target) / 86_400_000);
};

export const taxonomy = {
  areas: Array.from(new Set(benchmarks.map((item) => item.area))).sort(),
  domains: Array.from(new Set(benchmarks.map((item) => item.primaryDomain))).sort(),
  topics: Array.from(new Set(benchmarks.flatMap((item) => item.topics))).sort(),
};

export interface BenchmarkRepository {
  getManifest(): typeof benchmarkManifest;
  listBenchmarks(query: BenchmarkQuery): BenchmarkRecord[];
  getBenchmark(id: string): BenchmarkRecord | null;
  listTaxonomy(): typeof taxonomy;
}

export class StaticJsonRepository implements BenchmarkRepository {
  getManifest() {
    return benchmarkManifest;
  }

  listTaxonomy() {
    return taxonomy;
  }

  listBenchmarks(query: BenchmarkQuery): BenchmarkRecord[] {
    const maxAge = query.window === "30d" ? 30 : 90;
    const needle = query.search.trim().toLowerCase();

    return benchmarks
      .filter((item) => query.window === "today"
        ? item.releasedAt === (benchmarkManifest.latestSourceDate ?? benchmarkManifest.dataAsOf)
          || item.attention?.hfDailySubmittedAt?.slice(0, 10) === benchmarkManifest.dataAsOf
        : daysAgo(item.releasedAt) <= maxAge)
      .filter((item) => !query.areas.length || query.areas.includes(item.area))
      .filter((item) => !query.domains.length || query.domains.includes(item.primaryDomain))
      .filter((item) => !query.topics.length || item.topics.some((topic) => query.topics.includes(topic)))
      .filter((item) => {
        if (!needle) return true;
        return [item.name, item.oneLine, item.area, ...item.applicationDomains, ...item.industrySectors, ...item.topics, ...item.capabilities]
          .join(" ")
          .toLowerCase()
          .includes(needle);
      })
      .sort((a, b) => query.sort === "newest"
        ? b.releasedAt.localeCompare(a.releasedAt)
        : (b.ranking?.[query.window]?.score ?? -1) - (a.ranking?.[query.window]?.score ?? -1)
          || b.releasedAt.localeCompare(a.releasedAt));
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
