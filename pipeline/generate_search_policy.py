"""Publish the controlled concept vocabulary to all search consumers."""
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
def render():
    source=json.loads((ROOT/'data/evidence_concepts.json').read_text())
    policy={'version':1,'concepts':[{k:c[k] for k in ('id','label','aliases','parent') if k in c} for c in source['concepts']]}
    return '(function(root){const policy='+json.dumps(policy,ensure_ascii=False,separators=(',',':'))+';if(typeof module!=="undefined"&&module.exports)module.exports=policy;root.BenchmarkSearchPolicy=policy;})(typeof globalThis!=="undefined"?globalThis:this);\n'
if __name__=='__main__':
    (ROOT/'web/search-policy.js').write_text(render())
