import contextlib
import io
from pathlib import Path
import sys
import json
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from benchmark_reader import run

class OutputTests(unittest.TestCase):
    def invoke(self,args,tty=False):
        out,err=io.StringIO(),io.StringIO()
        with contextlib.redirect_stdout(out),contextlib.redirect_stderr(err),patch.object(out,'isatty',return_value=tty):
            code=run(args)
        return code,out.getvalue(),err.getvalue()
    def test_pipe_json_compatibility(self):
        code,out,err=self.invoke(['search','SciCode','--limit','1'])
        self.assertEqual(code,0);self.assertTrue(json.loads(out)['ok']);self.assertEqual(err,'')
    def test_explicit_json_before_or_after_command(self):
        for args in [['--json','search','SciCode'],['search','SciCode','--json']]:
            code,out,err=self.invoke(args,True)
            self.assertEqual(code,0);self.assertTrue(json.loads(out)['ok'])
    def test_readable_list_and_detail(self):
        code,out,err=self.invoke(['search','SciCode','--limit','1'],True)
        self.assertIn('ID:',out);self.assertIn('Next page:',out)
        code,out,err=self.invoke(['show','bm_naturebench_ffd14b37','--text'])
        self.assertIn('no linked records',out)
        self.assertNotIn('Reporting organizations: 0',out)
    def test_errors_preserve_machine_and_human_contract(self):
        code,out,err=self.invoke(['hot','--window','bad','--text'])
        self.assertEqual(code,2);self.assertEqual(out,'');self.assertIn('invalid_arguments',err)
        code,out,err=self.invoke(['hot','--window','bad','--json'],True)
        self.assertEqual(code,2);self.assertFalse(json.loads(out)['ok']);self.assertEqual(err,'')
        self.assertEqual(self.invoke(['--json','search','--text'])[0],2)
