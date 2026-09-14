import contextlib
import io
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cli_discovery import discover
from benchmark_reader import run

class DiscoveryTests(unittest.TestCase):
    def test_window_filter_sort_and_missing_scores(self):
        def row(id, day, score=None, **extra):
            return dict(id=id, name=id, releasedAt=day, firstSeenAt='2026-09-13', primaryDomain='Biology', oneLine='protein folding evaluation', ranking={'90d': {'score': score}}, **extra)
        payload={'manifest':{'dataAsOf':'2026-09-15','latestSourceDate':'2026-09-13'},'records':[
            row('high','2026-09-07',80),row('low','2026-09-13',20),row('missing','2026-09-12'),
            row('old','2026-09-06',100),row('future','2026-09-14',100),row('hidden','2026-09-13',100,displayEligible=False)]}
        args=SimpleNamespace(command='hot',as_of=None,window='7d',domain='biology',query='protein folding',limit=2,offset=0)
        data=discover(payload,args)
        self.assertEqual([r['id'] for r in data['results']],['high','low'])
        self.assertEqual((data['total'],data['nextOffset'],data['ranking']['unrankedCount']),(3,2,1))
        args.offset=2
        self.assertEqual(discover(payload,args)['results'][0]['id'],'missing')
        args.command='daily';args.date='2026-09-13';args.basis='released';args.offset=0
        self.assertEqual(discover(payload,args)['total'],1)
        args.basis='discovered'
        self.assertEqual(discover(payload,args)['total'],5)

    def invoke(self,args):
        output=io.StringIO()
        with contextlib.redirect_stdout(output):
            code=run(args)
        return code,json.loads(output.getvalue())

    def test_cli_contract(self):
        for args in [['daily','--date','2026-02-30'],['hot','--window','3m'],['hot','--offset','-1']]:
            code,data=self.invoke(args)
            self.assertEqual(code,2);self.assertEqual(data['error']['code'],'invalid_arguments')
        for args in [['daily'],['hot','--window','90d'],['search','science','--sort','attention']]:
            code,data=self.invoke(args)
            self.assertEqual(code,0);self.assertTrue(data['ok'])
            self.assertIn('attention',data['data']['results'][0])
