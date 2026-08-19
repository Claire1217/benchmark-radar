#!/usr/bin/env python3
"""Assemble the dependency-free static artifact deployed by GitHub Pages."""

from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "web"
OUTPUT = ROOT / "_site"


def main() -> None:
    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)
    shutil.copytree(SOURCE, OUTPUT)
    data_dir = OUTPUT / "data"
    data_dir.mkdir()
    for name in ("benchmarks_index.json", "domain_trends.json"):
        shutil.copy2(ROOT / "data" / name, data_dir / name)
    (OUTPUT / ".nojekyll").write_text("", encoding="utf-8")
    print(f"built={OUTPUT}")


if __name__ == "__main__":
    main()
