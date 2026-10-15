"""End-to-end pipeline check using a tiny benchmark and deterministic agent replies."""

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from autoform.constitution import isabelle, report, runner

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'tests' / 'fixtures' / 'toy-benchmark'
CONFIG = ROOT / 'tests' / 'fixtures' / 'toy-config.json'


class PipelineIntegrationTest(unittest.TestCase):
    def test_toy_constitution_pipeline_and_resume(self):
        with tempfile.TemporaryDirectory(prefix='autoform-integration-') as temporary:
            temp = Path(temporary)
            bin_dir = temp / 'bin'
            bin_dir.mkdir()
            fake_codex = bin_dir / 'codex'
            shutil.copyfile(ROOT / 'tests' / 'fixtures' / 'fake_codex.py', fake_codex)
            fake_codex.chmod(0o755)
            calls = temp / 'codex-calls.txt'
            run_dir = temp / 'run'
            environment = {
                'PATH': str(bin_dir) + os.pathsep + os.environ.get('PATH', ''),
                'TOY_CODEX_CALLS': str(calls),
            }
            with mock.patch.object(runner, 'BASE', FIXTURE), mock.patch.object(report, 'BASE', FIXTURE), mock.patch.dict(os.environ, environment):
                with self.assertRaisesRegex(RuntimeError, 'provisional'):
                    runner.run(CONFIG, run_dir, with_reviews=True)
                self.assertFalse((run_dir / 'manifest.json').exists())
                runner.run(CONFIG, run_dir, with_reviews=True, allow_provisional=True)
                self.assertEqual(len(calls.read_text().splitlines()), 32)

                manifest = json.loads((run_dir / 'manifest.json').read_text())
                self.assertEqual(manifest['benchmark_status'], 'provisional_development')
                self.assertEqual(len(list((run_dir / 'candidates').glob('*/assessment.json'))), 8)
                for document in ('character-consistent', 'character-inconsistent'):
                    for method in ('smt', 'fol', 'asp', 'isabelle'):
                        candidate_dir = run_dir / 'candidates' / f'{document}__{method}__direct__01'
                        assessment = json.loads((candidate_dir / 'assessment.json').read_text())
                        diagnostics = json.loads((candidate_dir / 'case-diagnostics.json').read_text())
                        self.assertEqual(assessment['validity']['schema'], 'valid')
                        self.assertEqual(assessment['validity']['source_trace'], 'valid')
                        self.assertEqual(assessment['natural_language_defensibility']['status'], 'agent_reviewed')
                        self.assertEqual(assessment['design_fidelity']['missing_design_rules'], [])
                        self.assertEqual(assessment['design_fidelity']['extra_candidate_rules'], [])
                        self.assertEqual(len(assessment['coherence']['conflicts']), int(document.endswith('inconsistent')))
                        expected = 'conflicting' if document.endswith('inconsistent') else 'required'
                        self.assertEqual(diagnostics['C05']['initial']['send_alert']['status'], expected)
                        self.assertEqual(assessment['validity']['backend']['status'], 'checked' if method != 'isabelle' or isabelle.isabelle_binary() else 'not_run')
                        if method != 'isabelle':
                            self.assertTrue(assessment['validity']['backend']['agrees_with_finite_checker'])
                        else:
                            self.assertTrue((candidate_dir / 'backend' / 'Candidate.thy').is_file())
                        self.assertTrue((candidate_dir / 'generation_call' / 'prompt.txt').is_file())
                        self.assertEqual(len(list((candidate_dir / 'reviews').glob('vote-*.json'))), 3)

                prompt = (run_dir / 'candidates' / 'character-inconsistent__fol__direct__01' / 'generation_call' / 'prompt.txt').read_text()
                self.assertNotIn('Toy case C05', prompt)
                self.assertNotIn('intended_consistency', prompt)
                findings = (run_dir / 'findings.md').read_text()
                self.assertIn('## Key results', findings)
                self.assertIn('## Error analysis', findings)
                self.assertIn('Preserved provision', findings)
                runner.run(CONFIG, run_dir, with_reviews=True, allow_provisional=True)
                self.assertEqual(len(calls.read_text().splitlines()), 32, 'Resume must reuse saved agent calls')


    def test_agent_failure_is_saved_without_stopping_the_run(self):
        with tempfile.TemporaryDirectory(prefix='autoform-failure-') as temporary:
            temp = Path(temporary)
            bin_dir = temp / 'bin'
            bin_dir.mkdir()
            fake_codex = bin_dir / 'codex'
            shutil.copyfile(ROOT / 'tests' / 'fixtures' / 'fake_codex.py', fake_codex)
            fake_codex.chmod(0o755)
            environment = {
                'PATH': str(bin_dir) + os.pathsep + os.environ.get('PATH', ''),
                'TOY_CODEX_FAIL_ON_INCONSISTENT': '1',
            }
            run_dir = temp / 'run'
            config = ROOT / 'tests' / 'fixtures' / 'toy-failure-config.json'
            with mock.patch.object(runner, 'BASE', FIXTURE), mock.patch.object(report, 'BASE', FIXTURE), mock.patch.dict(os.environ, environment):
                runner.run(config, run_dir, allow_provisional=True)
            good = json.loads((run_dir / 'candidates' / 'character-consistent__smt__direct__01' / 'assessment.json').read_text())
            failed_dir = run_dir / 'candidates' / 'character-inconsistent__smt__direct__01'
            failed = json.loads((failed_dir / 'assessment.json').read_text())
            self.assertEqual(good['validity']['schema'], 'valid')
            self.assertEqual(failed['validity']['schema'], 'generation_failed')
            self.assertIn('Codex exited 2', failed['validity']['reason'])
            self.assertIn('toy generation failure', (failed_dir / 'generation_call' / 'stderr.log').read_text())
            self.assertIn('Generation or schema failure: 1/2 candidates', (run_dir / 'findings.md').read_text())


if __name__ == '__main__':
    unittest.main()
