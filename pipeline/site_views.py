"""Trimmed record files for the website.

data/library_index.json and data/benchmarks_index.json are public downloads
(llms.txt, schema.org DataDownload), so they stay complete. The pages load
*_view.json copies that keep only the record fields the web code references,
found by scanning web/**/*.js. A field the UI starts using is therefore kept
automatically; nested values are kept whole.
"""
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
VIEWS = {'library_index.json': 'library_view.json', 'benchmarks_index.json': 'radar_view.json'}


def referenced_names(web: Path = ROOT / 'web') -> set[str]:
    names = set()
    for path in web.rglob('*.js'):
        text = path.read_text(encoding='utf-8')
        names.update(re.findall(r'[A-Za-z_$][\w$]*', text))
    return names


def slim(payload: dict, names: set[str]) -> dict:
    keep = lambda record: {k: v for k, v in record.items() if k in names}
    return {**payload, 'records': [keep(r) for r in payload['records']]}


def write_views(data_dir: Path, names: set[str] | None = None) -> dict:
    names = names or referenced_names()
    sizes = {}
    for source, target in VIEWS.items():
        payload = json.loads((data_dir / source).read_text(encoding='utf-8'))
        text = json.dumps(slim(payload, names), ensure_ascii=False, separators=(',', ':'))
        (data_dir / target).write_text(text + '\n', encoding='utf-8')
        sizes[target] = len(text)
    return sizes
