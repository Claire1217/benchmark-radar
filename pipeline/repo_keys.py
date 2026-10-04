"""Canonical GitHub repository keys shared by Trends, star histories and growth."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
ALIASES=json.loads((ROOT/'data/github_repository_aliases.json').read_text()) if (ROOT/'data/github_repository_aliases.json').exists() else {}
def repo_key(url):
 from urllib.parse import urlparse
 path=urlparse(url or "").path.strip("/").removesuffix(".git").lower()
 key="/".join(path.split("/")[:2]) if urlparse(url or "").hostname in {"github.com", "www.github.com"} else ""
 seen=set()
 while key in ALIASES and key not in seen:
  seen.add(key);key=ALIASES[key]
 return key

def current_repo_directions(records):
 result={}
 for r in records:
  if r.get("displayEligible") is False or r.get("evaluationMode")=="viewpoint_probe":continue
  url=(r.get("links") or {}).get("code")
  key=repo_key(url)
  # Main tool repository stars cannot be isolated to the benchmark it hosts.
  if not key or key in {"aider-ai/aider","allenai/olmocr"} or (r.get("attention") or {}).get("githubScope")=="hosting_repo":continue
  result.setdefault(key,set()).update(r.get("researchTopics",r.get("researchDirections",[])))
 return result
