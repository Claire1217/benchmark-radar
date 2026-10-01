import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline"))
from site_header import apply_repository_menu


class RepositoryMenuTests(unittest.TestCase):
    def test_picker_has_two_separate_links_and_native_keyboard_control(self):
        html = (ROOT / "web/index.html").read_text()
        picker = re.search(r'<details class="github-repositories">.*?</details>', html, re.S).group(0)
        self.assertIn('<summary class="github"', picker)
        self.assertEqual(picker.count('<a '), 2)
        self.assertIn('https://github.com/Claire1217/benchmark-radar', picker)
        self.assertIn('https://github.com/ktwu01/benchmark-radar', picker)
        self.assertNotIn('role="tooltip"', picker)
        self.assertEqual(picker.count('rel="noopener noreferrer"'), 2)

    def test_build_shares_menu_and_versions_assets_at_each_page_depth(self):
        main = (ROOT / 'web/index.html').read_text()
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            for name in ('github-repositories.css', 'github-repositories.js'):
                (output / name).write_text((ROOT / 'web' / name).read_text())
            (output / 'index.html').write_text(main)
            nested = output / 'model-evals/index.html'
            nested.parent.mkdir()
            nested.write_text('<head></head><body><header class="topbar"><a class="github" href="old">GitHub</a></header></body>')
            for _ in range(2):
                apply_repository_menu(main, output)
            for page in (output / 'index.html', nested):
                text = page.read_text()
                self.assertEqual(text.count('class="github-repositories"'), 1)
                self.assertEqual(text.count('github-repositories.js?v='), 1)
                self.assertEqual(text.count('github-repositories.css?v='), 1)
                self.assertIn('https://github.com/ktwu01/benchmark-radar', text)
            self.assertIn('../github-repositories.js?v=', nested.read_text())

    def test_hover_click_focus_escape_and_touch(self):
        subprocess.run(['node', str(ROOT / 'pipeline/tests/github_repositories_test.cjs')], check=True)
