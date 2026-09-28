import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from strep import save,sha256
from summarize_support_fallback import bound_pair


def evidence(tmp_path):
    source=tmp_path/'asset.glb';source.write_bytes(b'bound geometry')
    save(tmp_path/'timeline.json',dict(samples=[1,2,3]))
    record=dict(case='case',comparison_kind='fallback_common_input',before_sha256='source',after_sha256='candidate',
                inputs={str(source):sha256(source)},timeline_sha256=sha256(tmp_path/'timeline.json'))
    save(tmp_path/'completion.json',record)
    return tmp_path/'completion.json',record


def test_data_and_reference_binding(tmp_path):
    path,record=evidence(tmp_path)
    assert bound_pair(path,'case','source','candidate','fallback_common_input')==record
    with pytest.raises(ValueError):bound_pair(path,'case','source','candidate','fallback_pilot')
    with pytest.raises(ValueError):bound_pair(path,'case','earlier','candidate','fallback_common_input')


@pytest.mark.parametrize('target',['asset.glb','timeline.json'])
def test_changed_evidence_rejected(tmp_path,target):
    path,_=evidence(tmp_path);(tmp_path/target).write_bytes(b'changed')
    with pytest.raises(ValueError):bound_pair(path,'case','source','candidate','fallback_common_input')
