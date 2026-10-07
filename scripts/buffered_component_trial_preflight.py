"""Authenticate an archived complete-clock trial before any scientific work.

Archive verification is separate from numerical validation and release gates.
Low storage must not create the trial directory or launch an expensive worker.
"""
import copy
import json
from pathlib import Path
import re
import shutil
from strep import sha256

ROLES = ('model', 'model_reader', 'trial', 'trial_reader', 'calibration', 'calibration_reader')
SCHEMAS = dict(zip(ROLES, ('strep-full-component-trajectory-v1',
    'strep-full-component-trajectory-replay-v1', 'strep-full-trajectory-trial-v1',
    'strep-full-trajectory-trial-replay-v1', 'strep-empirical-material-calibration-v1',
    'strep-empirical-material-calibration-independent-v1')))
DISK_RESERVE_BYTES = 1 << 30
ESTIMATED_OUTPUT_BYTES = 650 << 20
MAX_RECEIPT_FILE_BYTES = 64 << 20
MAX_RECEIPT_POPULATION_BYTES = 128 << 20
MODEL_FLAGS = ('all180_original_native_stencils_caps_scales_and90_columns_exact',
    'all180_complete1673_component_skin_stencils_and90_columns_exact',
    'all180_complete11_full_skin_stencils_and90_columns_exact',
    'all1673_complete_source_memberships_and348_axis_populations_exact',
    'all107072_pair_rows_and90_projected_columns_exact',
    'all99_positive_sample_margins_and_complete_clock_exact',
    'all_original_clock_weights_and_deficits_exact')
TRIAL_FLAGS = ('all_complete1710_legacy_witness_populations_and90_projected_columns_exact',
    'complete571824_pair_guard_partition_and3636_rows_exact',
    'all10032_affine_coordinate_enclosures_verified_by_exact_rationals',
    'all_three1763_variable_conics_and_original_clock_weights_exact',
    'all6336_positive_component_conic_rows_hard',
    'every_actual_export_native_reference_contact11_queries_and107072_rows_exact',
    'complete_actual_eligibility_and_absent_scene_selection_exact')
CALIBRATION_FLAGS = ('all_eight_complete1710_actual_and_original_model_affine_arrays_exact',
    'every13680_observation_and_per_row_empirical_margin_exact',
    'complete_endpoint_row_source_identity_and_policy_digest_exact',
    'original_ceiling_and_tightened_affine_rejection_counts_exact',
    'no_producer_calibration_or_solver_api_used', 'no_new_skin_or_native_or_geometry_query')


def _read(path, maximum_bytes=MAX_RECEIPT_FILE_BYTES):
    if not path.is_file() or path.stat().st_size > maximum_bytes:
        raise ValueError('Bounded source JSON file required')
    def reject(value):raise ValueError('Nonfinite JSON number: '+value)
    with path.open(encoding='utf-8-sig') as stream:
        return json.load(stream, parse_constant=reject)


def _pin(pin, base):
    if (not isinstance(pin, dict) or set(pin) != {'path', 'sha256'}
            or type(pin['path']) is not str or not pin['path']
            or type(pin['sha256']) is not str or re.fullmatch('[0-9a-f]{64}', pin['sha256']) is None):
        raise ValueError('Explicit source path and lowercase SHA256 required')
    path = (base/pin['path']).resolve()
    if not path.is_file() or sha256(path) != pin['sha256']:
        raise ValueError('Missing or changed source archive: '+str(path))
    return path


def preflight(request_path):
    """Verify source receipts, storage and complete archive bindings.

No output writes, dependency installs, native/skin/collision calls or solver
imports. A ready result still requires numerical and same-pose validation.
    """
    request_path = Path(request_path).resolve()
    request = _read(request_path, maximum_bytes=128 << 10)
    if (not isinstance(request, dict) or set(request) != {'schema', 'sources', 'output'}
            or request['schema'] != 'strep-buffered-component-trial-request-v1'
            or not isinstance(request['sources'], dict) or set(request['sources']) != set(ROLES)
            or type(request['output']) is not str or not request['output']):
        raise ValueError('Complete explicitly pinned trial request required')
    paths = {role: _pin(request['sources'][role], request_path.parent) for role in ROLES}
    if len(set(paths.values())) != len(ROLES):
        raise ValueError('Each source role requires its distinct receipt')
    if sum(path.stat().st_size for path in paths.values()) > MAX_RECEIPT_POPULATION_BYTES:
        raise ValueError('Complete receipt population exceeds metadata budget; no subset returned')
    reports = {role: _read(path) for role, path in paths.items()}
    if any(not isinstance(r, dict) or r.get('schema') != SCHEMAS[role] or r.get('status') != 'complete'
           or r.get('quality_approved') is not False or r.get('release_approved') is not False
           or r.get('original_selected') is not True for role, r in reports.items()):
        raise ValueError('Complete unapproved source receipts required')
    for producer, consumer, flags in (('model', 'model_reader', MODEL_FLAGS),
            ('trial', 'trial_reader', TRIAL_FLAGS), ('calibration', 'calibration_reader', CALIBRATION_FLAGS)):
        if (reports[consumer].get('producer_result_sha256') != request['sources'][producer]['sha256']
                or any(reports[consumer].get(flag) is not True for flag in flags)):
            raise ValueError('Complete source reader and exact producer binding required: '+consumer)
    output = (request_path.parent/request['output']).resolve()
    if (output.exists() or not output.parent.is_dir()
            or any(output == p or output in p.parents for p in paths.values())):
        raise ValueError('Fresh trial output with an existing parent, outside source receipts required')
    # Compare bytes on the actual output filesystem, retaining the original
    # reserve and estimate. Metadata-only preparation does not bypass this.
    free = shutil.disk_usage(output.parent).free
    result = dict(schema='strep-buffered-component-trial-preflight-v1',
        status='blocked-insufficient-storage', request_sha256=sha256(request_path),
        source_receipts_sha256={str(paths[r]): request['sources'][r]['sha256'] for r in ROLES},
        output=str(output), disk_free_bytes=free, disk_reserve_bytes=DISK_RESERVE_BYTES,
        estimated_output_bytes=ESTIMATED_OUTPUT_BYTES,
        required_disk_free_bytes=DISK_RESERVE_BYTES+ESTIMATED_OUTPUT_BYTES,
        output_created=False, numerical_validation_complete=False, scientific_work_started=False,
        quality_approved=False, release_approved=False)
    if free <= result['required_disk_free_bytes']:
        return result
    bindings = {str(request_path): result['request_sha256'], **result['source_receipts_sha256']}
    for role, report in reports.items():
        if not isinstance(report.get('inputs_sha256'), dict):
            raise ValueError('Complete archived input bindings required: '+role)
        additions = dict(report['inputs_sha256'])
        if role in ('model', 'trial', 'calibration'):
            if not isinstance(report.get('files_sha256'), dict) or not report['files_sha256']:
                raise ValueError('Complete archived output bindings required: '+role)
            for name, digest in report['files_sha256'].items():
                if type(name) is not str or not name:
                    raise ValueError('Explicit archive member required')
                member = (paths[role].parent/name).resolve()
                if paths[role].parent not in member.parents:
                    raise ValueError('Archive output member must stay inside its source directory')
                additions[str(member)] = digest
        for name, digest in additions.items():
            checked = _pin(dict(path=name, sha256=digest), paths[role].parent)
            key = str(checked)
            if key in bindings and bindings[key] != digest:
                raise ValueError('Conflicting source digest: '+key)
            bindings[key] = digest
    result.update(status='ready-for-numerical-validation', inputs_sha256=bindings,
        source_paths={r: str(p) for r, p in paths.items()}, source_reports=copy.deepcopy(reports),
        bindings_checked=len(bindings))
    return result
