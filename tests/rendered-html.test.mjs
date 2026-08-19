import assert from "node:assert/strict";
import { access, readFile } from "node:fs/promises";
import test from "node:test";

async function render(path = "/") {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("test", `${process.pid}-${Date.now()}`);
  const { default: worker } = await import(workerUrl.href);

  return worker.fetch(
    new Request(`http://localhost${path}`, {
      headers: { accept: "text/html", host: "localhost" },
    }),
    {
      ASSETS: {
        fetch: async () => new Response("Not found", { status: 404 }),
      },
    },
    { waitUntil() {}, passThroughOnException() {} },
  );
}

test("server-renders the benchmark discovery experience", async () => {
  const response = await render("/?window=30d&sort=newest");
  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type") ?? "", /^text\/html\b/i);

  const html = await response.text();
  assert.match(html, /Benchmark Radar/);
  assert.match(html, /Track emerging benchmarks/);
  assert.match(html, /PRIMARY SOURCES/);
  assert.match(html, /30 days/);
  assert.match(html, /Newest/);
  assert.match(html, /aria-pressed="true"/);
  assert.match(html, /Recent independent adoption and attention/);
  assert.match(html, /og:image/);
});

test("keeps primary-source data, repository boundaries, and removed preview explicit", async () => {
  const [page, repository, benchmarks, packageJson] = await Promise.all([
    readFile(new URL("../app/page.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/repository.ts", import.meta.url), "utf8"),
    readFile(new URL("../app/benchmarks.ts", import.meta.url), "utf8"),
    readFile(new URL("../package.json", import.meta.url), "utf8"),
  ]);

  assert.match(page, /benchmark-radar:watchlist:v1/);
  assert.match(page, /aria-expanded/);
  assert.match(repository, /class StaticJsonRepository/);
  assert.match(repository, /benchmarkSnapshot\.manifest/);
  assert.match(benchmarks, /BENCHMARK_DATA_NOTICE/);
  assert.match(benchmarks, /data\/benchmarks\.json/);
  assert.match(benchmarks, /demo: false/);
  assert.doesNotMatch(packageJson, /react-loading-skeleton/);
  await assert.rejects(
    access(new URL("../app/_sites-preview/SkeletonPreview.tsx", import.meta.url)),
  );
});
