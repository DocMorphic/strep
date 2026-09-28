import sys
import shutil
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from strep import ROOT,read,save
from rig_runtime_cycle import write
from rig_asset import RigAsset


@pytest.mark.parametrize('fault',['hash','repeated','weighted_ancestor','rigid_primitive'])
def test_runtime_rejects_incompatible_source(tmp_path,monkeypatch,fault):
    source=ROOT/'reports/rig-jobs/20260926-215001-012ea007/transfer'
    for file in ('character.glb','report.json','timeline.json'):shutil.copyfile(source/file,tmp_path/file)
    report=read(tmp_path/'report.json')
    if fault=='hash':report['glb_sha256']='0'*64
    if fault=='repeated':report['frames']+=1
    save(tmp_path/'report.json',report)
    if fault in ('weighted_ancestor','rigid_primitive'):
        rig=RigAsset.load(tmp_path/'character.glb')
        if fault=='weighted_ancestor':rig.primitives[0]['joints'][:]=rig.joints.index(64)
        else:rig.primitives[0]['joints']=None
        monkeypatch.setattr(RigAsset,'load',lambda path:rig)
    with pytest.raises(ValueError):write(tmp_path)
    assert not (tmp_path/'runtime-cycle.json').exists()


def test_cycle_package_exposes_optional_prop_consumer_without_binding_events(tmp_path):
    source=ROOT/'reports/rig-jobs/20260926-215001-012ea007/transfer'
    for name in ('character.glb','report.json','timeline.json','events.json'):
        shutil.copyfile(source/name,tmp_path/name)
    result=write(tmp_path)
    binding=result['playback']['object_consumer']
    assert binding['opt_in'] and not binding['bindings_automatic']
    assert result['markers']==[dict(name='cycle_boundary',phase_frame=0,first_cycle=1)]
    assert (tmp_path/binding['adapter']).read_bytes()==(ROOT/'scripts'/binding['adapter']).read_bytes()
    assert (tmp_path/binding['instructions']).read_bytes()==(ROOT/'integrations/godot/OBJECT-EVENTS.md').read_bytes()
