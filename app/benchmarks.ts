import snapshot from "../data/benchmarks_index.json";

export type BenchmarkLinkSet = {
  report: string;
  paper?: string;
  pdf: string;
  project: string | null;
  code: string | null;
  data: string | null;
  hfPaper?: string | null;
};

export type BenchmarkMetric = {
  name: string;
  value: string;
  note?: string;
};

export type BenchmarkRecord = {
  id: string;
  familyId: string;
  name: string;
  paperTitle?: string;
  aliases?: string[];
  oneLine: string;
  area: string;
  applicationDomains: string[];
  primaryDomain: string;
  industrySectors: string[];
  domainCuration?: { state: "auto" | "reviewed"; method: string };
  capabilities: string[];
  topics: string[];
  construction: string;
  annotation: string;
  readiness: "Paper only" | "Inspectable" | "Runnable" | "Maintained";
  releasedAt: string;
  firstSeenAt: string;
  indexedAt?: string;
  sourceUpdatedAt?: string;
  adoption30d?: number | null;
  heat?: number | null;
  confidence?: "Low" | "Medium" | "High";
  recognitionConfidence: number;
  relation?: "introduces" | "extends" | "aggregates";
  links: BenchmarkLinkSet;
  motivation?: string;
  constructionDetail?: string;
  metrics?: BenchmarkMetric[];
  source: {
    type: "arxiv";
    id: string;
    url?: string;
    title?: string;
    authors?: string[];
    categories?: string[];
  };
  evidence: {
    snippet: string;
    reasonCodes: string[];
  };
  dataStatus: "primary-source-indexed";
  demo: false;
  attention?: {
    asOf: string;
    hfPaperUpvotes: number | null;
    hfDailySubmittedAt: string | null;
    hfPaperUrl?: string | null;
    githubStars: number | null;
    githubRepo?: string | null;
    hfDatasetDownloads: number | null;
    hfDatasetLikes: number | null;
    hfDataset?: string | null;
  };
  ranking?: Record<"today" | "30d" | "90d", {
    score: number | null;
    rank: number | null;
    coverage: number;
    confidence: "Low" | "Medium" | "High";
    method?: string;
    components?: Record<string, { value: number | null; percentile: number | null; mode: string }>;
    datasetDownloadRank?: number;
    datasetRankPopulation?: number;
  }>;
};

export const BENCHMARK_DATA_NOTICE =
  "Records are indexed from primary-source metadata. Unknown fields remain unknown; adoption and momentum appear only after enough dated observations are collected.";

export const benchmarkSnapshot = snapshot as {
  manifest: {
    schemaVersion: string;
    pipelineVersion: string;
    generatedAt: string | null;
    dataAsOf: string;
    latestSourceDate?: string;
    timezone: string;
    recordCount: number;
    sourceCoverage: string[];
    isDemo: false;
    run: {
      sourceDate: string;
      papersFetched: number;
      accepted: number;
      reviewQueued: number;
      sourceWindow?: { from: string; to: string };
    };
    metrics?: {
      observedAt: string;
      methodVersion: string;
      windows: string[];
      note: string;
    };
  };
  records: BenchmarkRecord[];
};

export const benchmarks = benchmarkSnapshot.records;
