import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from study_coupled_breadth_population import selected_rows, verify_completion
from strep import save, sha256


def test_selection_keeps_every_excluded_case_and_original_order():
    rows = [dict(id=name, excluded_by_vertical_bound=value) for name, value in [('b', True), ('control', False), ('a', True)]]
    assert [r['id'] for r in selected_rows(dict(rows=rows))] == ['b', 'a']


@pytest.mark.parametrize('rows', [
    [dict(id='a', excluded_by_vertical_bound=True)]*2,
    [dict(id='a', excluded_by_vertical_bound=1)],
    [dict(id='a', excluded_by_vertical_bound=False)],
])
def test_incomplete_or_ambiguous_population_is_rejected(rows):
    with pytest.raises(ValueError):
        selected_rows(dict(rows=rows))


@pytest.mark.parametrize('changed', ['request.json', 'audit.json', 'engine/verification.json',
                                    'take/candidate/character.glb', 'source/candidate/character.glb'])
def test_reused_pilot_cannot_hide_changed_proof_or_motion(tmp_path, changed):
    for name in ['take/candidate/character.glb', 'source/candidate/character.glb']:
        path = tmp_path/name
        path.parent.mkdir(parents=True)
        path.write_bytes(name.encode())
    save(tmp_path/'request.json', dict(case='fixture'))
    (tmp_path/'engine').mkdir()
    save(tmp_path/'engine/verification.json', dict(checks=[]))
    save(tmp_path/'audit.json', dict(candidate_sha256=sha256(tmp_path/'take/candidate/character.glb'),
                                  source_sha256=sha256(tmp_path/'source/candidate/character.glb')))
    done = {field+'_sha256': sha256(tmp_path/name) for field, name in
            [('request', 'request.json'), ('audit', 'audit.json'), ('engine', 'engine/verification.json')]}
    save(tmp_path/'completion.json', done)
    assert verify_completion(tmp_path) == done
    with (tmp_path/changed).open('ab') as stream:
        stream.write(b'changed')
    with pytest.raises(ValueError, match='Changed completed'):
        verify_completion(tmp_path)
