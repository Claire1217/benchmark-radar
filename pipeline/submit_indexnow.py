#!/usr/bin/env python3
"""Notify IndexNow participants about recently changed public URLs."""

from __future__ import annotations

import argparse
from datetime import date, timedelta
import json
from pathlib import Path
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET


ENDPOINT = "https://api.indexnow.org/indexnow"
HOST = "benchmark-radar.com"


def sitemap_urls(path: Path, days: int, include_all: bool) -> list[str]:
    root = ET.parse(path).getroot()
    namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    cutoff = date.today() - timedelta(days=days)
    urls = []
    for item in root.findall("sm:url", namespace):
        location = item.findtext("sm:loc", namespaces=namespace)
        modified = item.findtext("sm:lastmod", namespaces=namespace)
        if location and (include_all or not modified or date.fromisoformat(modified[:10]) >= cutoff):
            urls.append(location)
    return urls


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sitemap", type=Path, required=True)
    parser.add_argument("--key", required=True)
    parser.add_argument("--days", type=int, default=8)
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()
    urls = sitemap_urls(args.sitemap, args.days, args.all)
    payload = json.dumps({
        "host": HOST,
        "key": args.key,
        "keyLocation": f"https://{HOST}/{args.key}.txt",
        "urlList": urls,
    }).encode()
    request = Request(ENDPOINT, data=payload, headers={"Content-Type": "application/json; charset=utf-8"}, method="POST")
    with urlopen(request, timeout=30) as response:
        print(f"indexnow_status={response.status} urls={len(urls)}")


if __name__ == "__main__":
    main()
