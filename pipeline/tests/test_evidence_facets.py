import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import classify_categories as classify
import evidence_facets as facets
from site_views import presentation


class EvidenceFacetTests(unittest.TestCase):
    def record(self,text,name='ExampleBench'):
        return {'id':'stable','name':name,'source':{'type':'arxiv','id':'2610.00001'},
                'links':{'report':'https://arxiv.org/abs/2610.00001'},'evidence':{'snippet':text}}

    def test_multi_domain_chip_track_is_not_a_whole_benchmark_claim(self):
        record=self.record('We introduce ExampleBench, a cross-domain benchmark spanning database tuning, chip design, and molecular design.')
        result=facets.extract(record)
        chip=next(f for f in result['facts'] if f['id']=='chip-design')
        self.assertEqual(chip['scope'],'task-subset')
        self.assertEqual(chip['sourceUrl'],record['links']['report'])
        self.assertIn('chip design',chip['quote'])
        self.assertTrue({'chip-design','electronics','engineering','molecular'} <= {f['id'] for f in result['facts']})

    def test_mixed_signal_and_parasitic_tasks_have_general_domain_rules(self):
        for text in ('A benchmark of 50 transistor-level design tasks.',
                     'Evaluates analog and mixed-signal circuit design tasks.',
                     'A benchmark suite for pre-layout parasitic parameter prediction on circuit graphs.'):
            self.assertIn('chip-design',{f['id'] for f in facets.extract(self.record(text))['facts']})

    def test_editorial_word_and_primary_quote_are_distinguishable(self):
        record=self.record('We introduce ExampleBench for evaluating models on tasks.')
        record['description']='Evaluates Verilog generation and analog circuit design.'
        result=facets.extract(record)
        self.assertTrue(all(f['basis']=='editorial-description' for f in result['facts']))
        self.assertTrue(all(f['scope']=='unspecified' for f in result['facts']))

    def test_unrelated_acronym_related_text_and_model_reports_are_not_facts(self):
        record=self.record('ExampleBench evaluates exploratory data analysis (EDA) with medical records.')
        record['modelReportReferences']=[{'description':'GPT model evaluated chip design'}]
        result=facets.extract(record)
        self.assertNotIn('chip-design',{f['id'] for f in result['facts']})
        record=self.record('ExampleBench does not evaluate chip design.')
        self.assertNotIn('chip-design',{f['id'] for f in facets.extract(record)['facts']})

    def test_domain_task_environment_axes_coexist_and_are_not_limited_to_three(self):
        record=self.record('ExampleBench is a benchmark for Verilog generation, VHDL generation, analog circuit design, and hardware verification with SPICE.')
        facts=facets.extract(record)['facts']
        self.assertGreater(len(facts),3)
        self.assertTrue({'domain','task','environment'} <= {f['axis'] for f in facts})
        self.assertTrue(all(f['quote'] in record['evidence']['snippet'] for f in facts))

    def test_releasing_code_is_not_evidence_of_a_code_generation_task(self):
        record=self.record('ExampleBench evaluates speech. We release code and data for reproducibility.')
        self.assertNotIn('code-generation',{f['id'] for f in facets.extract(record)['facts']})

    def test_generated_programs_are_code_generation_without_literal_keyword(self):
        record=self.record('Evaluates functional correctness of generated Python programs from docstrings using executable tests.')
        self.assertIn('code-generation',{f['id'] for f in facets.extract(record)['facts']})

    def test_source_changes_invalidate_but_attention_changes_do_not(self):
        record=self.record('ExampleBench evaluates Verilog generation.')
        first=facets.input_fingerprint(record)
        record['attention']={'githubStars':9000}
        self.assertEqual(first,facets.input_fingerprint(record))
        record['evidence']['snippet']='ExampleBench evaluates molecular design.'
        self.assertNotEqual(first,facets.input_fingerprint(record))

    def test_archive_survives_admission_and_rejects_older_text(self):
        record=self.record('Excerpt');record['sourceUpdatedAt']='2026-10-20'
        record['reviewContext']={'abstract':'ExampleBench evaluates chip design with reusable tasks.'}
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'evidence.json';facets.retain_sources([record],path)
            before=path.read_bytes()
            old=copy.deepcopy(record);old['sourceUpdatedAt']='2026-10-01';old['reviewContext']['abstract']='Old text'
            facets.retain_sources([old],path)
            self.assertEqual(path.read_bytes(),before)
            public=copy.deepcopy(record);public.pop('reviewContext')
            result=facets.extract(public,json.loads(path.read_text()))
            self.assertIn('chip-design',{f['id'] for f in result['facts']})

    def test_known_source_baseline_also_retains_primary_text(self):
        import refresh_source_observations as refresh
        record=self.record('Excerpt');record['sourceUpdatedAt']='2026-10-20'
        observed=[];queued=[]
        def fetch(row):
            return {**row,'reviewContext':{'abstract':'Full original source text about chip design.'}}
        refresh.refresh([record],{},fetch,queued.append,now='2026-10-24T00:00:00Z',observe=observed.append)
        self.assertEqual(len(observed),1)
        self.assertEqual(queued,[])
        self.assertIn('Full original',observed[0]['reviewContext']['abstract'])

    def test_search_document_survives_compact_projection_without_exposing_full_archive(self):
        record=self.record('ExampleBench is a benchmark for chip design.')
        facets.annotate([record])
        compact=presentation({'records':[record]})['records'][0]
        self.assertIn('searchDocument',compact)
        self.assertNotIn('classificationEvidence',compact)
        self.assertNotIn('evidence',compact)
        self.assertIn('chip-design',{f['id'] for f in compact['searchDocument']['concepts']})

    def test_model_assignments_refresh_and_human_anchor_is_preserved(self):
        record=self.record('ExampleBench is a benchmark for chip design.')
        facets.annotate([record])
        assigned={'stable':{'basis':'model-review','primary':'code-generation'}}
        self.assertEqual(len(classify.pending([record],assigned)),1)
        assigned['stable']['inputHash']=classify.classification_hash(record)
        self.assertEqual(classify.pending([record],assigned),[])
        record['classificationEvidence'][0]['text'] += ' Analog circuit design is also evaluated.'
        self.assertEqual(len(classify.pending([record],assigned)),1)
        assigned['stable']['basis']='anchor-review'
        self.assertEqual(classify.pending([record],assigned),[])

    def test_model_facet_requires_real_quote_and_explicit_scope(self):
        record=self.record('ExampleBench is a benchmark for chip design.')
        facets.annotate([record]);[source]=classify.pending([record],{})
        quote=record['evidence']['snippet'];url=record['links']['report']
        answer={'id':'stable','primary':'engineering-design','evidenceQuote':quote,'sourceUrl':url,
                'facets':[{'conceptId':'chip-design','scope':'benchmark','evidenceQuote':quote,'sourceUrl':url},
                          {'conceptId':'finance','scope':'benchmark','evidenceQuote':'Invented source quote here.','sourceUrl':url}]}
        accepted=classify.validate([source],[answer],{'engineering-design'})
        self.assertEqual([f['id'] for f in accepted['stable']['facets']],['chip-design'])
        answer['evidenceQuote']='Invented category quote as well.'
        self.assertEqual(classify.validate([source],[answer],{'engineering-design'}),{})


if __name__=='__main__':unittest.main()
