"""Metadata boundaries and real ZIP transport; numeric Studio study is separate."""
from pathlib import Path
from types import SimpleNamespace
import copy
import json
import sys
import zipfile

import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import studio_native_transition_contact_fit as studio
import native_transition_contact_package as package
from strep import save, sha256


@pytest.fixture
def source(tmp_path, monkeypatch):
    monkeypatch.setattr(studio, 'ROOT', tmp_path)
    root = tmp_path / 'reports/source'
    save(root / 'scene.json', dict(contacts=[]))
    motion = SimpleNamespace(rows=[dict(entry=dict(authored=dict(id='touch', limits=dict(position_m=.001))))],
                             initial=np.zeros(1), lower=-np.ones(1), upper=np.ones(1))
    motion.edits = SimpleNamespace(controls=lambda x: np.asarray(x, float))
    problem = SimpleNamespace(folder=root, motion=motion)
    recipe = dict(schema=studio.legacy.correction.SCHEMA, source={'folder': str(root), 'result_sha256': 'a'*64},
                  actors={'A': {'knots': [0, .5, 1]}}, geometry={}, label='test', iterations=1, maximum_pose_vertex_queries=1000)
    monkeypatch.setattr(studio.legacy, 'recipe_for', lambda bridge: copy.deepcopy(recipe))
    monkeypatch.setattr(studio.legacy.correction, 'Problem', lambda recipe, base: problem)
    payload = dict(schema=studio.SCHEMA, bridge={'resume_from': None}, reserves_m={'touch': .0001}, seed=None)
    return tmp_path, recipe, payload, problem


def test_studio_request_keeps_limits_and_explicit_null_seed(source):
    _, recipe, payload, problem = source
    actual, reserve, seed = studio.validate_request(payload)
    assert actual == recipe and seed is None
    assert reserve['reserves_m'] == payload['reserves_m']
    assert reserve['contacts_sha256'] == sha256(problem.folder / 'scene.json')
    assert problem.motion.rows[0]['entry']['authored']['limits']['position_m'] == .001


@pytest.mark.parametrize('fault', ['schema', 'extra', 'continuation', 'zero', 'unknown'])
def test_invalid_studio_reserve_requests_reject_before_output(source, fault):
    root, _, payload, _ = source
    if fault == 'schema': payload['schema'] = 'wrong'
    elif fault == 'extra': payload['approval'] = True
    elif fault == 'continuation': payload['bridge']['resume_from'] = {'folder':'other'}
    elif fault == 'zero': payload['reserves_m']['touch'] = 0
    else: payload['reserves_m'] = {'missing': .0001}
    with pytest.raises(ValueError): studio.validate_request(payload)
    assert not (root / 'reports' / studio.NAMESPACE).exists()


@pytest.mark.parametrize('job', ['../escape', '', '/absolute', 'a/b', 'a%20b', 'a?b'])
def test_namespace_rejects_ambiguous_or_escaping_job_ids(source, job):
    with pytest.raises(ValueError): studio.folder_for(job)


def test_old_seed_uses_contained_epoch_validation_and_same_permissions(source, monkeypatch):
    root, recipe, payload, _ = source
    seed = root / 'reports/prior'
    save(seed / 'result.json', {'schema': studio.legacy.correction.SCHEMA})
    save(seed / 'recipe.json', recipe)
    save(seed / 'fit/probes/final/probe.json', {'controls': [.1]})
    payload['seed'] = {'folder': 'prior', 'result_sha256': sha256(seed / 'result.json')}
    monkeypatch.setattr(studio.legacy, 'ROOT', root)
    seen=[]
    monkeypatch.setattr(studio.legacy, 'validate_request', lambda p: seen.append(copy.deepcopy(p)))
    assert studio.validate_request(payload)[2] == seed / 'fit/probes/final/probe.json'
    assert seen[0]['resume_from'] == payload['seed']
    changed=copy.deepcopy(recipe)
    changed['actors']['A']['knots'] = [0, .25, .5, .75, 1]
    save(seed / 'recipe.json', changed)
    with pytest.raises(ValueError, match='permissions'): studio.validate_request(payload)


@pytest.fixture
def bundle(tmp_path, monkeypatch):
    folder = tmp_path / 'proposal'
    names = ['request.json','recipe.json','reserve-binding.json','source-rate-caps.npz','optimization.json','completion.json']
    for n in names: (folder / n).parent.mkdir(parents=True, exist_ok=True); (folder / n).write_bytes(b'fixture')
    save(folder / 'prepared.json', {'seed_sha256': None})
    (folder / 'candidate').mkdir();(folder / 'candidate/scene.json').write_bytes(b'fixture-scene')
    (folder / 'probes/start').mkdir(parents=True);(folder / 'probes/start/probe.json').write_bytes(b'fixture-probe')
    original = folder / 'original-transition'
    save(original / 'recipe.json', {})
    save(original / 'prepared.json', {'inputs':{},'implementation_sha256':{}})
    save(original / 'result.json', {'files_sha256':{}})
    result = dict(checks={'whole_scene_geometry': False}, all_declared_samples_pass=False, binding={'role':'fixture'},
                  candidate_files_sha256={'scene.json':sha256(folder / 'candidate/scene.json')},
                  probe_files_sha256={'start/probe.json':sha256(folder / 'probes/start/probe.json')})
    save(folder / 'result.json', result)
    monkeypatch.setattr(package.workflow, 'METHODS', ())
    monkeypatch.setattr(package.workflow, 'verify', lambda p: copy.deepcopy(result))
    return folder, result, tmp_path / 'candidate.zip'


def test_zip_preserves_exact_candidate_and_selected_history_and_failed_checks(bundle):
    folder, _, output = bundle
    before=package.workflow.file_tree(folder)
    record=package.build(folder,output)
    assert package.verify(folder,output)==record
    assert record['checks']['whole_scene_geometry'] is False and not record['quality_approved']
    assert record['raw_optimizer_probes_included'] and not record['complete_external_source_graph_included']
    with zipfile.ZipFile(output) as z:
        assert z.read('candidate/scene.json')==(folder/'candidate/scene.json').read_bytes()
        assert z.read('history/probes/start/probe.json')==(folder/'probes/start/probe.json').read_bytes()
    assert package.workflow.file_tree(folder)==before


@pytest.mark.parametrize('fault',['member','approval','payload','size'])
def test_forged_zip_cannot_hide_failure_drop_history_or_change_payload(bundle,fault):
    folder, _, output = bundle
    package.build(folder,output)
    with zipfile.ZipFile(output) as z: entries={n:z.read(n) for n in z.namelist()}
    if fault=='member': entries.pop('history/source-rate-caps.npz')
    elif fault=='approval':
        r=json.loads(entries['package.json']);r['quality_approved']=True;entries['package.json']=json.dumps(r).encode()
    elif fault=='payload': entries['candidate/scene.json']=b'wrong-content'
    else: entries['candidate/scene.json']=b'fixture-scene-extra'
    with zipfile.ZipFile(output,'w') as z:
        for n,b in entries.items():z.writestr(n,b)
    with pytest.raises(ValueError):package.verify(folder,output)


def test_package_rejects_existing_or_nested_destination(bundle):
    folder, _, output = bundle
    with pytest.raises(ValueError):package.build(folder,folder/'archive.zip')
    output.write_bytes(b'existing')
    with pytest.raises(ValueError):package.build(folder,output)
    assert output.read_bytes()==b'existing'


@pytest.mark.parametrize('relative',['../bad','native-transition-contact-fit-jobs/a/../result.json',
                                     'native-transition-contact-fit-jobs/a/result.json?x',
                                     'native-transition-contact-fit-jobs/a/%2e%2e/x'])
def test_bad_published_paths_reject_before_numerical_manifest(relative,monkeypatch):
    def forbidden(_):raise AssertionError('Invalid path reached verifier')
    monkeypatch.setattr(studio,'manifest',forbidden)
    with pytest.raises(ValueError):studio.served_file(relative)
