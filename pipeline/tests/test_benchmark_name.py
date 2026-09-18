import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class BenchmarkNameTests(unittest.TestCase):
    def test_tex_accents_math_and_html_escaping(self):
        script = r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const context={};vm.createContext(context);
vm.runInContext(fs.readFileSync('web/benchmark-name.js','utf8'),context);
const render=value=>vm.runInContext(`benchmarkNameHtml(${JSON.stringify(value)})`,context);
assert.equal(render('V\\={a}kQA'),'VākQA');
assert.equal(render('Jos\\\'{e}'),'José');
assert.equal(render('$\\tau^\\tau$-Bench'),'τ<sup>τ</sup>-Bench');
assert.equal(render('M$^3$ISR'),'M<sup>3</sup>ISR');
assert.equal(render('<img src=x>'),'&lt;img src=x&gt;');
assert.equal(render('literal \\unknown'),'literal \\unknown');
"""
        subprocess.run(["node", "-e", script], cwd=ROOT, check=True)


if __name__ == "__main__":
    unittest.main()
