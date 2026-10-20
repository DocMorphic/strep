import pytest
from strep import save, sha256
from test_studio_mesh_scene import authored
from test_studio_prop_routes import handler
import studio_mesh_scene_job as jobs
import studio_mesh_scene_preview as preview
import action_studio_server as server


@pytest.fixture(autouse=True)
def sampling_method_fixture(authored, monkeypatch):
    # This fixture's assembler binds one generated implementation file.
    monkeypatch.setattr(preview, 'ROOT', authored[0])
    monkeypatch.setattr(preview, 'SAMPLING_METHODS', ('method.py',))


def completed(authored):
    _, request, _, resolver = authored
    folder = jobs.prepare(request)
    jobs.execute(folder, resolver)
    save(folder / 'guard/pipeline.json', dict(status='complete'))
    return folder, sha256(folder / 'package/result.json')


def test_saved_preview_binds_exact_assets_grips_and_result(authored):
    folder, digest = completed(authored)
    before = {p: p.read_bytes() for p in folder.rglob('*') if p.is_file()}
    result = preview.descriptor(folder.name, digest)
    assert result['mesh_contacts'][0]['grip_position_m']
    assert result['mesh_contacts'][0]['interval_s'] == [1., 1.]
    assert result['actors']['A']['animation_index'] == 0
    assert result['skin_weight_policy'] == 'native-all-influence-unit-sum'
    assert not result['quality_approved'] and not result['motion_fitted']
    for group in ('actors', 'props'):
        for item in result[group].values():
            assert sha256(server.allowed_file(item['url'])) == item['sha256']
    request = handler(f'/api/mesh-scene-jobs/{folder.name}/preview/{digest}')
    request.do_GET()
    assert request.responses[0] == (200, result)
    request = handler(f'/api/mesh-scene-jobs/{folder.name}')
    request.do_GET()
    assert request.responses[0][1]['preview_url'] == f'/mesh-scene-viewer.html?job={folder.name}&result={digest}'
    assert all(p.read_bytes() == raw for p, raw in before.items())


@pytest.mark.parametrize('fault', ['result', 'asset', 'grip', 'pending', 'request', 'sampling-method'])
def test_preview_rejects_changed_or_incomplete_package(authored, fault):
    folder, digest = completed(authored)
    if fault == 'result':
        digest = '0' * 64
    elif fault == 'pending':
        save(folder / 'guard/pipeline.json', dict(status='starting'))
    elif fault == 'sampling-method':
        (authored[0] / 'scripts/method.py').write_text('# changed sampling')
    else:
        name = {'asset': 'package/actors/A.glb', 'grip': 'package/grips/hand.json', 'request': 'request.json'}[fault]
        (folder / name).write_bytes(b'changed')
    with pytest.raises(ValueError):
        preview.descriptor(folder.name, digest)


def test_preview_asset_paths_are_closed(authored):
    folder, digest = completed(authored)
    for name in ('request.json', 'actors/../result.json', 'actors/A.glb/extra', 'actors/A.glb?x=1', 'actors/%2e%2e/result.json'):
        assert preview.served_file(f'/files/mesh-scene-previews/{folder.name}/{digest}/{name}') is None
    with pytest.raises(ValueError):
        preview.served_file(f'/files/mesh-scene-previews/{folder.name}/{digest}/actors/missing.glb')
    request = handler(f'/api/mesh-scene-jobs/{folder.name}/preview/{digest}')
    request.headers['Host'] = 'external.test'
    request.do_GET()
    assert request.responses[0][0] == 403
