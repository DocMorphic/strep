"""Decision reporting tests; deliberately use only the standard library."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from studio_mesh_diagnostics import CHECKS, summarize
from studio_mesh_character_job import diagnostics
from strep import sha256
from strep import save
import studio_mesh_character_job as jobs
import studio_mesh_character_recovery_job as recovery


def decision(index=0, geometry=True):
    row = dict(probe=index, accepted=False, geometry_evaluated=geometry)
    row.update({key: True for key, _, needs_geometry in CHECKS if not needs_geometry or geometry})
    return row


class DiagnosticsTests(unittest.TestCase):
    def test_failed_skipped_and_historical_checks_remain_distinct(self):
        failed = decision()
        failed['self_surface_nonregression_pass'] = False
        skipped = decision(1, False)
        skipped['source_rows_pass'] = False
        legacy = decision(2)
        del legacy['self_surface_nonregression_pass']
        result = summarize([failed, skipped, legacy], 3, 0)
        check = next(x for x in result['checks'] if x['key'] == 'self_surface_nonregression_pass')
        self.assertEqual([check[k] for k in ('passed', 'failed', 'not_checked', 'not_recorded')], [0, 1, 1, 1])
        self.assertFalse(result['quality_approved'])
        self.assertFalse(result['release_approved'])

    def test_accepted_does_not_imply_all_geometry_passes(self):
        row = decision()
        row.update(accepted=True, geometry_conditions_pass=False)
        result = summarize([row], 1, 1)
        self.assertEqual(result['accepted'], 1)
        self.assertEqual(next(x for x in result['checks'] if x['key'] == 'geometry_conditions_pass')['failed'], 1)

    def test_rejects_mismatched_counts_and_malformed_decisions(self):
        for rows, count, accepted in [([decision()], 2, 0), ([decision()], 1, 1), ([decision(1)], 1, 0),
                                      ([decision()], True, 0), ([decision()], 1, True)]:
            with self.subTest(rows=rows, count=count, accepted=accepted), self.assertRaises(ValueError):
                summarize(rows, count, accepted)
        for patch in [dict(accepted=1), dict(geometry_evaluated=1), dict(source_rows_pass='false'),
                      dict(geometry_evaluated=False), dict(probe=True)]:
            row = decision(); row.update(patch)
            with self.subTest(patch=patch), self.assertRaises(ValueError):
                summarize([row], 1, 0)

    def test_missing_history_is_not_a_pass(self):
        result = summarize([dict(probe=0, accepted=False)], 1, 0)
        self.assertTrue(all(x['not_recorded'] == 1 for x in result['checks']))
        self.assertEqual(summarize([], 0, 0)['attempts'], 0)

    def test_only_integrity_bound_log_is_used_for_both_layouts(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary).resolve()
            for recoverable, directory in [(False, 'fit'), (True, 'optimizers/saved')]:
                path = folder / directory / 'probes.json'
                path.parent.mkdir(parents=True)
                path.write_text(json.dumps([decision()]), encoding='utf8')
                result = dict(recoverable=recoverable, fit_directory=directory, probes=1, accepted_steps=0,
                              files_sha256={directory + '/probes.json': sha256(path)})
                self.assertTrue(diagnostics(folder, result)['available'])
                unbound = copy.deepcopy(result); unbound['files_sha256'] = {}
                self.assertFalse(diagnostics(folder, unbound)['available'])
                path.write_text('[]', encoding='utf8')
                with self.assertRaisesRegex(ValueError, 'changed'):
                    diagnostics(folder, result)
            result['fit_directory'] = '../outside'
            with self.assertRaisesRegex(ValueError, 'escape'):
                diagnostics(folder, result)

    def test_completed_review_returns_bound_diagnostics_in_both_layouts(self):
        with tempfile.TemporaryDirectory() as temporary:
            for recoverable in (False, True):
                job = ('a' if recoverable else 'b') * 32
                folder = jobs.absolute(Path(temporary) / job)
                save(folder / 'request.json', dict(recoverable=recoverable))
                prepared = dict(request_sha256=sha256(folder / 'request.json'))
                save(folder / 'prepared.json', prepared)
                directory = 'optimizers/saved' if recoverable else 'fit'
                probe_path = folder / directory / 'probes.json'
                save(probe_path, [decision()])
                result = dict(recoverable=recoverable, fit_directory=directory, probes=1, accepted_steps=0,
                              files_sha256={directory + '/probes.json': sha256(probe_path)}, **prepared)
                publication = folder / 'publications/saved' if recoverable else folder
                save(publication / 'result.json', result)
                (publication / 'correction-package.zip').write_bytes(b'bound archive fixture')
                receipt = dict(result_sha256=sha256(publication / 'result.json'),
                               zip_sha256=sha256(publication / 'correction-package.zip'), **prepared)
                save(publication / 'receipt.json', receipt)
                save(folder / 'guard/pipeline.json', dict(status='complete'))
                attempt = folder / 'attempts/saved'
                if recoverable:
                    save(folder / 'publication.json', dict(directory='publications/saved', receipt_sha256=sha256(publication / 'receipt.json')))
                    save(attempt / 'completion.json', dict(publication_sha256=sha256(folder / 'publication.json'), **prepared))
                with patch.object(jobs, 'folder_for', return_value=folder), \
                     patch.object(recovery, 'request_for', return_value=({}, prepared)), \
                     patch.object(recovery, 'active', return_value=(attempt, dict(number=1))), \
                     patch.object(recovery, 'attempt_status', return_value=(dict(status='complete'), False)):
                    response = jobs.review(job)
                    self.assertEqual(response['diagnostics']['attempts'], 1)
                    self.assertFalse(response['diagnostics']['quality_approved'])
                    save(probe_path, [])
                    with self.assertRaises(ValueError):
                        jobs.review(job)


if __name__ == '__main__':
    unittest.main()
