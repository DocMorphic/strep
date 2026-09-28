import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from strep import read
from rig_loop import validate,prepare
from rig_contact_authoring import metadata


def recipe():
    m=metadata('20260926-195412-bf0e8a1d','corrected')
    return dict(schema='strep-rig-loop-v1',label='Wave cycle',job=m['job_id'],variant=m['variant'],glb_sha256=m['glb_sha256'],start_frame=10,period_frames=60,blend_frames=8,turn_degrees=15)


@pytest.mark.parametrize('fault',['hash','short','tail','negative','float','turn'])
def test_invalid_loop_rejected(fault):
    p=recipe()
    if fault=='hash':p['glb_sha256']='0'*64
    if fault=='short':p['period_frames']=8
    if fault=='tail':p['period_frames']=110
    if fault=='negative':p['start_frame']=-1
    if fault=='float':p['period_frames']=60.5
    if fault=='turn':p['turn_degrees']=float('inf')
    with pytest.raises(ValueError):validate(p)


@pytest.mark.parametrize('mode',['travel','in_place'])
def test_repeated_loop_accumulates_cycle_transform_and_retains_source_seam(tmp_path,monkeypatch,mode):
    import action_worker_lock
    from rig_studio_job import run
    from rig_asset import RigAsset
    from gltf_tools import sample_animation
    from rig_contact_tracks import signals
    monkeypatch.setattr(action_worker_lock,'ROOT',tmp_path)
    request=recipe();request['root_mode']=mode
    if mode=='in_place':request['turn_degrees']=0
    folder=tmp_path/'loop';prepare(request,folder);run(folder)
    result=read(folder/'result.json');assert result['frames']==61 and result['variants']['repeated']['frames']==181
    runtime=read(folder/'transfer/runtime-cycle.json')
    assert runtime['glb_sha256']==result['variants']['transfer']['sha256'] and runtime['period_frames']==60
    assert runtime['markers']==[dict(name='cycle_boundary',phase_frame=0,first_cycle=1)]
    assert result['runtime_adapter'].endswith('/transfer/godot_cycle_adapter.gd')
    import zipfile
    with zipfile.ZipFile(folder/'character-animation.zip') as archive:
        assert archive.read('transfer/godot_cycle_adapter.gd')==(folder/'transfer/godot_cycle_adapter.gd').read_bytes()
    single=RigAsset.load(folder/'transfer/character.glb');repeated=RigAsset.load(folder/'repeated/character.glb');raw=RigAsset.load(folder/'input/character.glb')
    assert single.document['animations'][0]['name'].startswith('Strep · ')
    assert single.document['animations'][0]['name'].endswith(' · motion')
    assert single.document['animations'][0]['extras']['strep_label']=='Wave cycle'
    cycle=np.array(read(folder/'transfer/timeline.json')['cycle_transform']);root=result['root_node']
    assert cycle[1,3]==0 and np.linalg.det(cycle[:3,:3])==pytest.approx(1)
    if mode=='in_place':np.testing.assert_allclose(cycle,np.eye(4),atol=1e-12)
    original=[sample_animation(raw.document,raw.binary,0,f) for f in (69,70,71)]
    actual=[sample_animation(repeated.document,repeated.binary,0,f) for f in (59,60,61)]
    np.testing.assert_allclose(actual,original,atol=1e-5)
    for f in (0,1,7,20,59,60,61,120,180):
        phase=f%60;c=f//60;before=sample_animation(single.document,single.binary,0,phase);after=sample_animation(repeated.document,repeated.binary,0,f)
        for node,parent in enumerate(single.parents):
            ancestor=node
            while ancestor>=0 and ancestor!=root:ancestor=single.parents[ancestor]
            expected=np.linalg.matrix_power(cycle,c)@before[node] if ancestor==root else before[node]
            np.testing.assert_allclose(after[node],expected,atol=1e-5)
    audit=read(folder/'transfer/loop-audit.json');assert audit['source_seam_transform_error']<1e-5
    a,_=signals(read(folder/'transfer/report.json'));b,_=signals(read(folder/'repeated/report.json'))
    for role in a:
        assert a[role][0]==a[role][-1]
        np.testing.assert_array_equal(b[role],np.r_[a[role][:-1],a[role][:-1],a[role]])
    assert [e['frame'] for e in read(folder/'repeated/events.json')['events']]==[60,120,180]
