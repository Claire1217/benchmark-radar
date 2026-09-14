"""Exercise the real browser date selection without network or a browser runtime."""
import pathlib
import subprocess
import unittest

class LatestFeedTests(unittest.TestCase):
    def test_initial_feed_fills_from_previous_days(self):
        root = pathlib.Path(__file__).resolve().parents[2]
        script = r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const context={window:{},localStorage:{getItem:()=>null},fetch:()=>new Promise(()=>{})};
vm.createContext(context);vm.runInContext(fs.readFileSync('web/app.js','utf8'),context);
vm.runInContext(`
state.manifest={latestSourceDate:'2026-09-13',dataAsOf:'2026-09-15'};
state.benchmarks=[{releasedAt:'2026-09-13'},...Array.from({length:4},()=>({releasedAt:'2026-09-12'})),...Array.from({length:8},()=>({releasedAt:'2026-09-11'})),{releasedAt:'2026-09-10'},...Array.from({length:20},()=>({releasedAt:'2026-09-13',displayEligible:false})),{releasedAt:'2026-09-16'}];
state.latestFrom=latestAvailableDate();`,context);
assert.equal(vm.runInContext('state.latestFrom',context),'2026-09-11');
assert.equal(vm.runInContext('state.benchmarks.filter(displayEligible).filter(eligible).length',context),13);
assert.equal(vm.runInContext('previousLatestDate()',context),'2026-09-10');
vm.runInContext(`state.benchmarks=Array.from({length:12},()=>({releasedAt:'2026-09-13'}));`,context);
assert.equal(vm.runInContext('latestAvailableDate()',context),'2026-09-13');
vm.runInContext(`state.benchmarks=[{releasedAt:'2026-09-12'}];`,context);
assert.equal(vm.runInContext('latestAvailableDate()',context),'2026-09-12');
vm.runInContext('state.benchmarks=[]',context);
assert.equal(vm.runInContext('latestAvailableDate()',context),'2026-09-13');
'''
        subprocess.run(['node', '-e', script], cwd=root, check=True, capture_output=True, text=True)
