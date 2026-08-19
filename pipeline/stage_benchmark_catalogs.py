#!/usr/bin/env python3
"""Download external benchmark catalogs into a non-canonical staging schema.

The adapters deliberately preserve source identifiers and evidence-shaped raw
fields. They do not infer canonical benchmark IDs and never modify Radar or
Library data.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from typing import Any, Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = ROOT / "data" / "staging"
BENCHLM_URL = "https://benchlm.ai/data/benchmarks.json"
LLM_STATS_URL = "https://llm-stats.com/benchmarks"

PROTOCOL_TERMS = (
    "protocol", "method", "setting", "setup", "prompt", "harness",
    "subset", "split", "shot", "scaffold", "judge", "grader",
)
METRIC_TERMS = (
    "metric", "score", "scale", "unit", "accuracy", "pass@", "elo",
)
ATTRIBUTION_TERMS = (
    "source", "provenance", "citation", "paper", "project", "url",
    "author", "organization", "maintainer", "license",
)
VERSION_KEYS = ("version", "benchmark_version", "benchmarkVersion", "revision")
KEY_KEYS = ("benchmarkKey", "key", "id", "slug", "benchmark_id", "benchmarkId")
NAME_KEYS = ("name", "title", "label", "display_name", "displayName")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def first_value(record: dict[str, Any], keys: Iterable[str]) -> Any:
    for key in keys:
        value = record.get(key)
        if value not in (None, "", [], {}):
            return value
    return None


def scalar_evidence(record: dict[str, Any], terms: tuple[str, ...], limit: int = 32) -> list[dict[str, Any]]:
    """Retain bounded raw scalar fields whose paths indicate useful evidence."""
    found: list[dict[str, Any]] = []

    def visit(value: Any, path: str, depth: int) -> None:
        if len(found) >= limit or depth > 4:
            return
        if isinstance(value, dict):
            for key, child in value.items():
                child_path = f"{path}.{key}" if path else str(key)
                visit(child, child_path, depth + 1)
        elif isinstance(value, list):
            # Preserve compact metadata lists, but do not copy score matrices.
            if len(value) <= 12 and all(isinstance(item, (str, int, float, bool, type(None))) for item in value):
                if any(term in path.casefold() for term in terms):
                    found.append({"path": path, "value": value})
            else:
                for index, child in enumerate(value[:4]):
                    visit(child, f"{path}[{index}]", depth + 1)
        elif any(term in path.casefold() for term in terms):
            found.append({"path": path, "value": value})

    visit(record, "", 0)
    return found[:limit]


def benchmark_items(payload: Any) -> list[tuple[str | None, dict[str, Any]]]:
    """Accept list, {items|benchmarks: list/dict}, or key-to-record shapes."""
    if isinstance(payload, dict) and "items" in payload:
        container = payload["items"]
    elif isinstance(payload, dict) and "benchmarks" in payload:
        container = payload["benchmarks"]
    else:
        container = payload
    if isinstance(container, list):
        return [(None, item) for item in container if isinstance(item, dict)]
    if isinstance(container, dict):
        return [
            (str(key), value if isinstance(value, dict) else {"value": value})
            for key, value in container.items()
        ]
    raise ValueError("catalog JSON must be a benchmark list or object")


def adapt_payload(
    payload: Any,
    *,
    source_id: str,
    source_url: str,
    retrieved_at: str,
    payload_bytes: bytes | None = None,
) -> dict[str, Any]:
    candidates: list[dict[str, Any]] = []
    for mapping_key, raw_record in benchmark_items(payload):
        source_key = first_value(raw_record, KEY_KEYS) or mapping_key
        name = first_value(raw_record, NAME_KEYS) or source_key
        raw_version = first_value(raw_record, VERSION_KEYS)
        candidates.append({
            "source": source_id,
            "sourceKey": str(source_key) if source_key is not None else None,
            "nameHint": str(name) if name is not None else None,
            "rawVersion": raw_version,
            "protocolEvidence": scalar_evidence(raw_record, PROTOCOL_TERMS),
            "metricEvidence": scalar_evidence(raw_record, METRIC_TERMS),
            "attributionEvidence": scalar_evidence(raw_record, ATTRIBUTION_TERMS),
            "retrievedAt": retrieved_at,
            "rawRecordSha256": sha256(canonical_json(raw_record)),
            "stagingStatus": "unreviewed",
        })
    raw_bytes = payload_bytes if payload_bytes is not None else canonical_json(payload)
    return {
        "schemaVersion": "1.0",
        "mode": "staging-only",
        "source": {
            "id": source_id,
            "url": source_url,
            "attribution": source_url,
            "retrievedAt": retrieved_at,
            "payloadSha256": sha256(raw_bytes),
        },
        "recordCount": len(candidates),
        "candidates": candidates,
    }


def fetch_bytes(url: str, *, accept: str, timeout: int = 30) -> bytes:
    headers = {"Accept": accept, "User-Agent": "benchmark-radar-staging/1.0"}
    request = Request(url, headers=headers)
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.read()
    except (HTTPError, URLError, TimeoutError) as error:
        raise RuntimeError(f"catalog request failed for {url}: {type(error).__name__}") from None


def fetch_json(url: str, *, timeout: int = 30) -> tuple[Any, bytes]:
    body = fetch_bytes(url, accept="application/json", timeout=timeout)
    try:
        return json.loads(body), body
    except json.JSONDecodeError:
        raise RuntimeError(f"catalog returned invalid JSON: {url}") from None


class PublicLinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[dict[str, str]] = []
        self._href: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "a":
            self._href = dict(attrs).get("href")
            self._text = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._href is not None:
            self.links.append({"href": self._href, "text": " ".join("".join(self._text).split())})
            self._href = None
            self._text = []


def adapt_llm_stats_public_page(html: str, retrieved_at: str) -> dict[str, Any]:
    """Use the public directory for discovery without treating it as authority."""
    parser = PublicLinkParser()
    parser.feed(html)
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    blocked_hosts = {"llm-stats.com", "www.llm-stats.com", "x.com", "twitter.com", "discord.com"}
    primary_hosts = {"arxiv.org", "www.arxiv.org", "github.com", "huggingface.co"}
    for link in parser.links:
        url = urljoin(LLM_STATS_URL, link["href"])
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        text = link["text"].strip()
        if parsed.scheme != "https" or not host or url in seen:
            continue
        is_detail = host in {"llm-stats.com", "www.llm-stats.com"} and re.fullmatch(
            r"/benchmarks/[^/?#]+", parsed.path
        )
        if is_detail:
            seen.add(url)
            slug = parsed.path.rsplit("/", 1)[-1]
            candidates.append({
                "source": "llm-stats-public-directory",
                "sourceKey": slug,
                "nameHint": text or slug,
                "catalogDetailUrl": url,
                "originalSourceUrl": None,
                "discoveredAt": LLM_STATS_URL,
                "retrievedAt": retrieved_at,
                "stagingStatus": "catalog-detail-pending-primary-source",
                "canonicalPromotionAllowed": False,
            })
            continue
        if host in blocked_hosts:
            continue
        # Only direct scholarly/code/data links count as resolved original
        # sources. Generic outbound links remain excluded instead of being
        # promoted on catalog authority alone.
        if host not in primary_hosts or not text:
            continue
        seen.add(url)
        candidates.append({
            "source": "llm-stats-public-page",
            "sourceKey": url,
            "nameHint": text,
            "originalSourceUrl": url,
            "discoveredAt": LLM_STATS_URL,
            "retrievedAt": retrieved_at,
            "stagingStatus": "original-source-resolved",
            "canonicalPromotionAllowed": False,
        })
    # The Next.js directory also serializes detail routes inside its streamed
    # page payload rather than ordinary anchor tags. Retain those routes as
    # discovery hints; they still cannot enter canonical data until a later
    # resolver finds and verifies an original source.
    for path in re.findall(r"/benchmarks/[A-Za-z0-9][A-Za-z0-9._-]*", html):
        url = urljoin(LLM_STATS_URL, path)
        if url in seen:
            continue
        seen.add(url)
        slug = path.rsplit("/", 1)[-1]
        candidates.append({
            "source": "llm-stats-public-directory",
            "sourceKey": slug,
            "nameHint": slug,
            "catalogDetailUrl": url,
            "originalSourceUrl": None,
            "discoveredAt": LLM_STATS_URL,
            "retrievedAt": retrieved_at,
            "stagingStatus": "catalog-detail-pending-primary-source",
            "canonicalPromotionAllowed": False,
        })
    raw = html.encode("utf-8")
    return {
        "schemaVersion": "1.0",
        "mode": "public-page-discovery-only",
        "source": {
            "id": "llm-stats",
            "url": LLM_STATS_URL,
            "attribution": LLM_STATS_URL,
            "retrievedAt": retrieved_at,
            "payloadSha256": sha256(raw),
        },
        "recordCount": len(candidates),
        "candidates": candidates,
        "policy": "Directory entries are discovery hints only; every candidate must be resolved to and verified against an original source before canonical use.",
    }


def write_staging(output: Path, payload: dict[str, Any]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def stage_benchlm(output_dir: Path, retrieved_at: str) -> Path:
    payload, body = fetch_json(BENCHLM_URL)
    output = output_dir / "benchlm_candidates.json"
    write_staging(output, adapt_payload(
        payload,
        source_id="benchlm",
        source_url=BENCHLM_URL,
        retrieved_at=retrieved_at,
        payload_bytes=body,
    ))
    return output


def stage_llm_stats(output_dir: Path, retrieved_at: str) -> Path | None:
    try:
        body = fetch_bytes(LLM_STATS_URL, accept="text/html")
        payload = adapt_llm_stats_public_page(body.decode("utf-8", errors="replace"), retrieved_at)
    except RuntimeError as error:
        # Catalog discovery is optional and must never block the daily primary-
        # source index.
        print(f"skipped llm-stats public-page discovery: {error}")
        return None
    output = output_dir / "llm_stats_candidates.json"
    write_staging(output, payload)
    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stage external benchmark catalogs without canonical promotion.")
    parser.add_argument("--source", choices=("benchlm", "llm-stats", "all"), default="all")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    retrieved_at = utc_now()
    outputs: list[Path] = []
    if args.source in {"benchlm", "all"}:
        outputs.append(stage_benchlm(args.output_dir, retrieved_at))
    if args.source in {"llm-stats", "all"}:
        llm_stats_output = stage_llm_stats(args.output_dir, retrieved_at)
        if llm_stats_output:
            outputs.append(llm_stats_output)
    print(f"staged {len(outputs)} catalog source(s); canonical data unchanged")


if __name__ == "__main__":
    main()
