"""Saved rounded target coordinates only: no source poses or rig queries."""
import copy
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import scene_reference_contact_consistency as module
from scene_contact_consistency import diagnose
from test_scene_contact_consistency import scene
from strep import save,read,sha256


def fixture():
    value=scene(target_distance=2);value.update(id='fixture',fps=30)
    value['actors']={name:dict(motion=name+'.npz',source_sha256=name.lower()*64) for name in ['A','B']}
    value['contacts'][1]['target']=dict(space='actor',actor='B',joint='RightHand',offset_m=[0,0,0])
    targets={'grip-1':[[0,0,0] for _ in range(120)],'grip-2':[[2,0,0] for _ in range(120)]}
    targets['grip-2'][60]=[3,0,0]
    evaluation=dict(scene_id='fixture',fps=30,frame_count=120,
        sources={name:dict(path=entry['motion'],sha256=entry['source_sha256']) for name,entry in value['actors'].items()},
        contact_tracks={name:dict(target_world_m=points) for name,points in targets.items()})
    return value,evaluation,module.reference_tracks(copy.deepcopy(value),evaluation)


def test_fixed_reference_conflict_covers_every_overlap_frame_and_is_not_a_blocker():
    value,evaluation,tracks=fixture();original=copy.deepcopy(tracks)
    assert diagnose(value)['overlapping_pairs'][0]['status']=='unassessed'
    report=module.diagnose_reference(value,tracks)
    assert tracks==original and report['assessed_pair_frames']==report['declared_pair_frame_population']==41
    assert report['conflicting_pair_frames']==1
    pair=report['overlapping_pairs'][0];assert [r['frame'] for r in pair['frames']]==list(range(50,91))
    assert [r['frame'] for r in pair['frames'] if r['fixed_reference_pair_conflict']]==[60]
    assert not report['joint_generation_blocker'] and not report['producer_correctness_revalidated']
    assert not report['source_pose_geometry_checked'] and not report['feasibility_approved']


def test_changed_partner_reference_can_remove_the_condition_without_physics_approval():
    value,evaluation,tracks=fixture();first=module.diagnose_reference(value,tracks)
    tracks['evaluation']['contact_tracks']['grip-2'][60]=[2,0,0]
    second=module.diagnose_reference(value,tracks)
    assert first['reference_tracks_sha256']!=second['reference_tracks_sha256']
    assert second['conflicting_pair_frames']==0 and not second['feasibility_approved']


def test_mesh_contact_reference_cannot_be_replaced_with_a_joint_hint():
    value,evaluation,tracks=fixture();value['contacts'][0]['effector']['surface_vertex']=3;tracks['scene']=copy.deepcopy(value)
    report=module.diagnose_reference(value,tracks)
    assert report['declared_pair_frame_population']==41 and report['assessed_pair_frames']==0
    assert report['unassessed_pairs']==1 and report['overlapping_pairs'][0]['frames']==[]


@pytest.mark.parametrize('defect',['scene','clock','source','source_missing','bad_hash','track_missing','track_short','nan','boolean','world_changed_off_event','duplicate_id','extra','null'])
def test_stale_or_incomplete_reference_contract_rejected(defect):
    value,evaluation,tracks=fixture();data=tracks['evaluation']
    if defect=='scene':tracks['scene']['contacts'][0]['tolerance_m']=.5
    if defect=='clock':data['frame_count']=119
    if defect=='source':data['sources']['B']['sha256']='c'*64
    if defect=='source_missing':data['sources'].pop('B')
    if defect=='bad_hash':value['actors']['A']['source_sha256']='z'*64;tracks['scene']=copy.deepcopy(value);data['sources']['A']['sha256']='z'*64
    if defect=='track_missing':data['contact_tracks'].pop('grip-2')
    if defect=='track_short':data['contact_tracks']['grip-2'].pop()
    if defect=='nan':data['contact_tracks']['grip-2'][0][0]=float('nan')
    if defect=='boolean':data['contact_tracks']['grip-2'][0][0]=True
    if defect=='world_changed_off_event':data['contact_tracks']['grip-1'][5]=[1,0,0]
    if defect=='duplicate_id':value['contacts'][1]['id']='grip-1';tracks['scene']=copy.deepcopy(value)
    if defect=='extra':tracks['infeasibility_approved']=True
    if defect=='null':tracks=None
    with pytest.raises(ValueError):module.diagnose_reference(value,tracks)


def test_pair_frame_budget_rejects_without_thinning():
    value,evaluation,tracks=fixture()
    value['contacts']=[dict(value['contacts'][0],id=str(i),start_frame=0,end_frame=119) for i in range(91)]
    tracks['scene']=copy.deepcopy(value);tracks['evaluation']['contact_tracks']={str(i):[[0,0,0]]*120 for i in range(91)}
    with pytest.raises(ValueError,match='pair-frame population'):module.diagnose_reference(value,tracks)


def test_full_target_track_budget_rejects_without_thinning():
    value,evaluation,tracks=fixture();value['frame_count']=1800
    value['contacts']=[dict(value['contacts'][0],id=str(i),effector=dict(joint=str(i),offset_m=[0,0,0])) for i in range(146)]
    tracks['scene']=copy.deepcopy(value);tracks['evaluation']['frame_count']=1800
    tracks['evaluation']['contact_tracks']={str(i):[[0,0,0]]*1800 for i in range(146)}
    with pytest.raises(ValueError,match='target-track population'):module.diagnose_reference(value,tracks)


def test_offline_cli_preview_binds_inputs_and_never_overwrites(tmp_path):
    value,evaluation,tracks=fixture();source=tmp_path/'bundle.json';out=tmp_path/'preview.json'
    save(source,dict(scene=value,evaluation=evaluation));result=module.preview(source,out)
    assert result['inputs_sha256'][str(source)]==sha256(source)
    assert result['report']['conflicting_pair_frames']==1;original=out.read_bytes()
    with pytest.raises(ValueError,match='Preserve'):module.preview(source,out)
    assert out.read_bytes()==original


def test_cli_rejects_source_read_races(tmp_path,monkeypatch):
    value,evaluation,tracks=fixture();source=tmp_path/'bundle.json';out=tmp_path/'preview.json'
    save(source,dict(scene=value,evaluation=evaluation));original_read=module.read
    def race(path):
        result=original_read(path)
        if Path(path)==source:save(source,dict(scene=value,evaluation=evaluation,changed=True))
        return result
    monkeypatch.setattr(module,'read',race)
    with pytest.raises(ValueError,match='inputs changed'):module.preview(source,out)
    assert not out.exists()


def test_authoring_optional_reference_report_is_conditional_and_read_only():
    from scene_generation_guides import authoring_preview
    from test_scene_generation_authoring import payload,handler
    value,evaluation,tracks=fixture();draft=payload();draft['scene']=value;draft['reference_tracks']=tracks
    result=authoring_preview(draft)
    assert not result['contact_consistency']['has_proven_pair_conflict']
    assert result['saved_reference_consistency']['conflicting_pair_frames']==1
    assert result['saved_reference_consistency']['joint_generation_blocker'] is False
    h=handler(draft);h.do_POST();assert h.responses[-1][0]==200
    draft['reference_tracks']=None
    with pytest.raises(ValueError):authoring_preview(draft)
