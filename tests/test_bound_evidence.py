import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from bound_evidence import bind_inputs
from strep import sha256


def test_additional_parent_evidence_is_verified_and_retained(tmp_path):
    source = tmp_path/'source'; parent = tmp_path/'parent'
    source.write_bytes(b'original'); parent.write_bytes(b'parent solve')
    required = {str(source): sha256(source)}; declared = dict(required, **{str(parent): sha256(parent)})
    assert bind_inputs(required, declared) == declared
    parent.write_bytes(b'changed')
    with pytest.raises(ValueError, match='changed'): bind_inputs(required, declared)


@pytest.mark.parametrize('kind', ['missing', 'different', 'changed'])
def test_required_inputs_cannot_be_omitted_rebound_or_changed(tmp_path, kind):
    source = tmp_path/'source'; source.write_bytes(b'original'); required = {str(source): sha256(source)}
    declared = required.copy()
    if kind == 'missing': declared.clear()
    if kind == 'different': declared[str(source)] = 'wrong'
    if kind == 'changed': source.write_bytes(b'changed')
    with pytest.raises(ValueError): bind_inputs(required, declared)
