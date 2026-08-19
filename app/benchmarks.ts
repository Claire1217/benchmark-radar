import snapshot from "../data/benchmarks.json";

export type BenchmarkLinkSet = {
  report: string;
  paper: string;
  pdf: string;
  project: string | null;
  code: string | null;
  data: string | null;
};

export type BenchmarkMetric = {
  name: string;
  value: string;
  note?: string;
};

export type BenchmarkRecord = {
  id: string;
  name: string;
  paperTitle: string;
  aliases: string[];
  oneLine: string;
  area: string;
  capabilities: string[];
  topics: string[];
  construction: string;
  annotation: string;
  readiness: "Paper only" | "Inspectable" | "Runnable" | "Maintained";
  releasedAt: string;
  firstSeenAt: string;
  indexedAt: string;
  sourceUpdatedAt: string;
  adoption30d: number | null;
  heat: number | null;
  confidence: "Low" | "Medium" | "High";
  recognitionConfidence: number;
  relation: "introduces" | "extends" | "aggregates";
  links: BenchmarkLinkSet;
  motivation: string;
  constructionDetail: string;
  metrics: BenchmarkMetric[];
  source: {
    type: "arxiv";
    id: string;
    url: string;
    title: string;
    authors: string[];
    categories: string[];
  };
  evidence: {
    snippet: string;
    reasonCodes: string[];
  };
  dataStatus: "primary-source-indexed";
  demo: false;
};

export const BENCHMARK_DATA_NOTICE =
  "Records are indexed from primary-source metadata. Unknown fields remain unknown; adoption and momentum appear only after enough dated observations are collected.";

export const benchmarkSnapshot = snapshot as {
  manifest: {
    schemaVersion: string;
    pipelineVersion: string;
    generatedAt: string | null;
    dataAsOf: string;
    timezone: string;
    recordCount: number;
    sourceCoverage: string[];
    isDemo: false;
    run: {
      sourceDate: string;
      papersFetched: number;
      accepted: number;
      reviewQueued: number;
    };
  };
  records: BenchmarkRecord[];
};

export const benchmarks = benchmarkSnapshot.records;
