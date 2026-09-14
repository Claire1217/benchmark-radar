import copy
import json
import unittest
from pipeline.sync_catalogs import parse_llm_stats, merge_payloads, normalized_name


def row(name, source='test', source_id=None):
    return {'id':name,'name':name,'normalizedName':normalized_name(name),'categories':[],
            'sourceRecords':[{'catalog':source,'sourceId':source_id or name,'url':'https://example.org/'+name}]}


class CatalogRefreshTests(unittest.TestCase):
    def test_live_api_schema(self):
        records=[{'benchmark_id':'science','name':'Science'}]
        self.assertEqual(parse_llm_stats(json.dumps(records).encode()), records)
        self.assertEqual(parse_llm_stats(json.dumps({'benchmarks':records}).encode()), records)
        with self.assertRaises(ValueError):
            parse_llm_stats(b'{"error":"unavailable"}')

    def test_preserves_history_and_supplements_on_refresh(self):
        previous={'retrievedAt':'2026-08-27','records':[row('Old')],'sources':{}}
        fresh={'retrievedAt':'2026-09-15','records':[row('New')],'sources':{}}
        supplement={'records':[row('Other','harbor')],'sources':{}}
        before=copy.deepcopy(previous)
        result=merge_payloads(fresh,previous,supplement)
        self.assertEqual({r['name']for r in result['records']},{'Old','New','Other'})
        self.assertEqual(previous,before)
        self.assertEqual(merge_payloads(fresh,result,supplement),result)

    def test_merge_provenance_without_merging_versions(self):
        fresh={'retrievedAt':'2026-09-15','records':[row('Bench 1.0'),row('Bench 2.0')],'sources':{}}
        result=merge_payloads(fresh,{}, {'records':[row('Bench 1.0','harbor')],'sources':{}})
        self.assertEqual(len(result['records']),2)
        self.assertEqual(len(result['records'][0]['sourceRecords']),2)

    def test_plus_is_part_of_benchmark_identity(self):
        self.assertNotEqual(normalized_name('RefCOCO'),normalized_name('RefCOCO+'))
        self.assertEqual(normalized_name('τ²-Bench'),normalized_name('tau2-bench'))
