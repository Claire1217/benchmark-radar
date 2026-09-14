import contextlib
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from benchmark_reader import run

class AgentOutputTests(unittest.TestCase):
    def test_json_in_terminal_and_pipe(self):
        for tty in [True, False]:
            for args in [['search','SciCode','--limit','1'], ['--json','search','SciCode','--limit','1'], ['search','SciCode','--json','--limit','1'], ['hot','--window','bad'], ['search','--text']]:
                with self.subTest(tty=tty,args=args):
                    out,err=io.StringIO(),io.StringIO()
                    with contextlib.redirect_stdout(out),contextlib.redirect_stderr(err),patch.object(out,'isatty',return_value=tty):
                        code=run(args)
                    payload=json.loads(out.getvalue())
                    self.assertEqual(payload['ok'],code==0)
                    self.assertEqual(err.getvalue(),'')
                    self.assertEqual(len(out.getvalue().splitlines()),1)
