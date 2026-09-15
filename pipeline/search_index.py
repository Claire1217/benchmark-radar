"""Local weighted BM25 retrieval. Expansions aid recall; they are not evidence."""
import difflib
import re
import sqlite3
from usage_store import norm

# Small, auditable vocabulary. Agents can also pass explicit English alternatives.
CONCEPTS = [
    ('科学', ('science', 'scientific')),
    ('编程', ('coding', 'programming')),
    ('代码', ('code', 'coding')),
    ('复现', ('reproduction', 'reproduce', 'replication')),
    ('生物', ('biology', 'biological')),
    ('化学', ('chemistry', 'chemical')),
    ('物理', ('physics', 'physical')),
    ('分子', ('molecular', 'molecule')),
    ('蛋白质', ('protein',)),
    ('推理', ('reasoning',)),
    ('数学', ('math', 'mathematics')),
    ('多模态', ('multimodal',)),
    ('机器人', ('robotics', 'robot')),
    ('长上下文', ('long context',)),
    ('工具调用', ('tool use', 'tool calling')),
]
STOP = {'a', 'an', 'the', 'for', 'of', 'in', 'on', 'and', 'to', 'with', 'find', 'benchmark', 'benchmarks'}


def identity_key(text):
    # Plus and decimal/version punctuation can distinguish real benchmark variants.
    return re.sub(r'[^\w+.]+', '', str(text).casefold())


def terms_for(query, alternatives=()):
    original = re.findall(r'[a-z0-9]+', query.casefold())
    terms = [word for word in original if word not in STOP]
    expansions = []
    for chinese, english in CONCEPTS:
        if chinese in query or any(re.search(r'\b' + re.escape(word) + r'\b', query, re.I) for word in english):
            expansions.extend(english)
    for text in alternatives:
        expansions.extend(re.findall(r'[a-z0-9]+', text.casefold()))
    terms = list(dict.fromkeys(terms + expansions))
    # Keep unknown identifiers searchable, while making limited Chinese support explicit.
    if not terms:
        terms = re.findall(r'\w+', query.casefold())
    return terms[:64], list(dict.fromkeys(expansions))[:64]


class SearchIndex:
    def __init__(self, records, get_labels):
        self.records = {r['id']: r for r in records}
        self.db = sqlite3.connect(':memory:')
        self.db.execute("CREATE VIRTUAL TABLE docs USING fts5(id UNINDEXED, name, aliases, description, domains, tokenize='porter unicode61')")
        self.fields = {}
        for r in records:
            fields = [r['name'], ' '.join(r.get('aliases', [])),
                      r.get('description') or r.get('oneLine') or '', ' '.join([*get_labels(r),*r.get('researchTopics',[]),*[v for k in ('tasks','capabilities','environments','modalities','protocols') for v in r.get('benchmarkTaxonomy',{}).get(k,[])]])]
            self.fields[r['id']] = fields
            self.db.execute('INSERT INTO docs VALUES (?, ?, ?, ?, ?)', [r['id'], *fields])
        self.db.commit()

    def close(self):
        self.db.close()

    def search(self, query, alternatives=()):
        terms, expansions = terms_for(query, alternatives)
        meta = {'original': query, 'expandedTerms': expansions, 'method': 'exact-name-alias + weighted-bm25-v1',
                'matchPolicy': 'Any query concept may match; partial matches are retained and ranked.',
                'languageSupport': 'English stemming and a limited explicit Chinese concept dictionary; not multilingual semantic search.'}
        hits = {}
        if not query.strip() and not alternatives:
            hits = {rid: {'exactMatch': None, 'score': 0.0, 'matchedFields': [], 'snippet': ''} for rid in self.records}
        elif terms:
            expression = ' OR '.join('"' + term.replace('"', '""') + '"' for term in terms)
            for rid, score, snippet in self.db.execute("SELECT id, bm25(docs,0,10,8,3,1), snippet(docs,-1,'[',']',' … ',24) FROM docs WHERE docs MATCH ?", (expression,)):
                matched = []
                for field in ('name', 'aliases', 'description', 'domains'):
                    if self.db.execute('SELECT 1 FROM docs WHERE id=? AND docs MATCH ?', (rid, field + ' : (' + expression + ')')).fetchone():
                        matched.append(field)
                hits[rid] = {'exactMatch': None, 'score': -score, 'matchedFields': matched, 'snippet': snippet}
        normalized = identity_key(query)
        if normalized:
            for rid, r in self.records.items():
                exact = 'name' if identity_key(r['name']) == normalized else 'alias' if normalized in {identity_key(a) for a in r.get('aliases', [])} else None
                if exact:
                    hit = hits.setdefault(rid, {'score': 0.0, 'matchedFields': [exact], 'snippet': r['name']})
                    hit['exactMatch'] = exact
        names = sorted({r['name'] for r in self.records.values()})
        meta['suggestions'] = difflib.get_close_matches(query, names, n=5, cutoff=.65) if query and not hits else []
        return hits, meta


def relevance_order(row):
    match = row['relevance']
    return ({'name': 0, 'alias': 1}.get(match['exactMatch'], 2), -match['score'], row['name'].casefold(), row['id'])
