import pathlib
import subprocess
import unittest


class LibraryScrollTests(unittest.TestCase):
    def test_visible_height_before_and_after_sticking(self):
        root = pathlib.Path(__file__).resolve().parents[2]
        script = r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const context={document:{querySelector:()=>null,getElementById:()=>null}};
vm.createContext(context);
vm.runInContext(fs.readFileSync('web/library-scroll.js','utf8'),context);
const height=context.librarySidebarHeight;
assert.equal(height(720,313,88),391);
assert.equal(height(720,88,88),616);
assert.equal(height(720,-200,88),616);
assert.equal(height(500,313,88),171);
assert.equal(height(300,313,88),0);
for(const viewport of [500,720,1080]){
  for(const top of [88,200,313]){
    assert(top+height(viewport,top,88)<=viewport-16);
  }
}
"""
        subprocess.run(["node", "-e", script], cwd=root, check=True)
