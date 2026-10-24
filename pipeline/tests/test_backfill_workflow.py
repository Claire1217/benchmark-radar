"""Exercise the production workflow's Git handoff with a local bare remote."""
import os
from pathlib import Path
import subprocess
import tempfile
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / '.github/workflows/editorial-backfill.yml'


def run_block(text, name):
    step = text.split('      - name: ' + name + '\n', 1)[1].split('\n      - ', 1)[0]
    return textwrap.dedent(step.split('        run: |\n', 1)[1])


def git(directory, *args):
    return subprocess.check_output(['git', '-C', str(directory), *args], text=True,
                                   stderr=subprocess.PIPE).strip()


class BackfillWorkflowTests(unittest.TestCase):
    def test_queued_run_syncs_first_and_commits_all_review_progress(self):
        workflow = WORKFLOW.read_text()
        sync = run_block(workflow, 'Sync latest main after waiting in the queue')
        commit = run_block(workflow, 'Generate and commit completed batches')
        explicit = next(line.strip().split()[2:] for line in commit.splitlines()
                        if line.strip().startswith('git add README.md'))
        for state_exists in (False, True):
            with self.subTest(state_exists=state_exists), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                remote, seed, worker = (root / name for name in ('remote.git', 'seed', 'worker'))
                root.mkdir(exist_ok=True)
                git(root, 'init', '--bare', '--initial-branch=main', str(remote))
                git(root, 'clone', str(remote), str(seed))
                git(seed, 'config', 'user.email', 'test@example.com')
                git(seed, 'config', 'user.name', 'Test')
                tracked = explicit + ['data/catalog_records.json', 'data/source_coverage.json']
                if state_exists:
                    tracked.append('data/review_state.json')
                for name in tracked:
                    path = seed / name
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text('{}\n')
                git(seed, 'add', '.')
                git(seed, 'commit', '-m', 'baseline')
                git(seed, 'push', 'origin', 'main')
                git(root, 'clone', str(remote), str(worker))
                # A run queued on an old checkout must start from this newer state.
                (seed / 'data/review_queue.json').write_text('{"newerMain":true}\n')
                git(seed, 'commit', '-am', 'new data while job waits')
                git(seed, 'push', 'origin', 'main')
                env = {**os.environ, 'RUNNER_TEMP': str(root)}
                subprocess.run(['bash', '-e', '-c', sync], cwd=worker, env=env,
                               check=True, capture_output=True, text=True)
                self.assertIn('newerMain', (worker / 'data/review_queue.json').read_text())
                expected = {
                    'data/review_state.json': '{"attempts":2}\n',
                    'data/catalog_records.json': '{"newCatalog":true}\n',
                    'data/source_coverage.json': '{"persistedWindows":19}\n',
                    'data/review_queue.json': '{"reviewedFromLatestMain":true}\n',
                }
                for name, value in expected.items():
                    (worker / name).write_text(value)
                # Generation has separate integration coverage. Execute the exact
                # workflow Git operations, stubbing only those expensive commands.
                subprocess.run(['bash', '-e', '-c', 'python() { :; }; make() { :; };\n' + commit],
                               cwd=worker, env=env, check=True, capture_output=True, text=True)
                for name, value in expected.items():
                    self.assertEqual(git(remote, 'show', 'main:' + name), value.strip())
                self.assertEqual(git(worker, 'status', '--porcelain'), '')

    def test_historical_candidate_review_has_no_expiry_and_is_bounded(self):
        workflow = WORKFLOW.read_text()
        command = next(line for line in workflow.splitlines() if '--review-queue' in line)
        self.assertNotIn('--released-from', command)
        self.assertIn('--released-through', command)
        self.assertIn('--limit 16', command)
        self.assertNotIn('--allow-unpublish', workflow)
        self.assertLess(workflow.index('Sync latest main'), workflow.index('--review-queue'))

    def test_recovery_snapshot_precedes_generation_in_both_writers(self):
        for name, generation in [('daily-index', 'Refresh opted-in Library attention'),
                                 ('editorial-backfill', 'Generate and commit completed batches')]:
            workflow = (ROOT / f'.github/workflows/{name}.yml').read_text()
            snapshot = workflow.split('      - name: Preserve collected and reviewed progress before generation', 1)[1]
            snapshot = snapshot.split('\n      - ', 1)[0]
            self.assertIn('if: always()', snapshot)
            self.assertIn('actions/upload-artifact@v4', snapshot)
            for path in ('review_state', 'source_coverage', 'source_evidence',
                         'review_queue', 'catalog_records', 'curated_records', 'editorial_copy'):
                self.assertIn('data/' + path + '.json', snapshot)
            self.assertLess(workflow.index('Preserve collected'), workflow.index('      - name: ' + generation))
            self.assertIn('group: benchmark-publish-pipeline', workflow)


if __name__ == '__main__':
    unittest.main()
