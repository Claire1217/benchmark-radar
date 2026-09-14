import pathlib
import sys
import unittest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from search_index import SearchIndex, relevance_order

class SearchTests(unittest.TestCase):
    def setUp(self):
        self.index=SearchIndex([
            {'id':'human','name':'HumanEval','description':'Code tests'},
            {'id':'plus','name':'HumanEval+','description':'Code tests and additional checks'},
            {'id':'full','name':'GPQA','description':'Graduate science questions'},
            {'id':'diamond','name':'GPQA Diamond','description':'A difficult subset of GPQA'},
            {'id':'sci','name':'SciCode','aliases':['Sci Code'],'description':'Scientific programming and research code generation'},
            {'id':'generic','name':'Popular coding tools','description':'Tools for coding websites'},
            {'id':'bio','name':'BioTask','description':'Reproduction of molecular experiments'},
        ],lambda r: [])
    def tearDown(self):
        self.index.close()
    def ranked(self,q,expand=()):
        hits,meta=self.index.search(q,expand)
        rows=[{'id':rid,'name':self.index.records[rid]['name'],'relevance':v} for rid,v in hits.items()]
        return sorted(rows,key=relevance_order),meta
    def test_exact_version_is_first_and_separate(self):
        self.assertEqual(self.ranked('HumanEval')[0][0]['id'],'human')
        self.assertEqual(self.ranked('HumanEval+')[0][0]['id'],'plus')
        self.assertEqual(self.ranked('GPQA')[0][0]['id'],'full')
        self.assertEqual(self.ranked('GPQA Diamond')[0][0]['id'],'diamond')
        self.assertEqual(self.ranked('Sci Code')[0][0]['id'],'sci')
    def test_chinese_and_synonym_recall(self):
        rows,meta=self.ranked('科学编程')
        self.assertEqual(rows[0]['id'],'sci')
        self.assertIn('scientific',meta['expandedTerms'])
        self.assertIn('description',rows[0]['relevance']['matchedFields'])
    def test_missing_one_term_does_not_remove_relevant_record(self):
        rows,_=self.ranked('scientific programming research reasoning')
        self.assertEqual(rows[0]['id'],'sci')
    def test_expansion_is_explicit_and_no_query_execution(self):
        rows,meta=self.ranked('未知需求',['molecular'])
        self.assertEqual(rows[0]['id'],'bio')
        self.assertIn('molecular',meta['expandedTerms'])
        self.ranked('" OR name:* -- (')
        self.assertEqual(self.ranked('zznonexistentzz')[0],[])
    def test_typo_suggests_without_silent_identity_change(self):
        rows,meta=self.ranked('SciCdoe')
        self.assertEqual(rows,[])
        self.assertIn('SciCode',meta['suggestions'])
