"""Exact surface derivatives, staged floor protection and preserved failures."""
import copy
import sys
from pathlib import Path
import numpy as np
import pytest
from threadpoolctl import threadpool_limits
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from test_rig_mesh_trajectory import make
from rig_mesh_trajectory import MeshContactTrajectoryFitter,CoupledMeshContactFitter,run
from rig_coupled_pose import window_basis
from mesh_contact_feasibility import MeshContactFeasibility
from strep import save,read,sha256


def setup(tmp_path,shift=0.,fixed=False):
    source,rig,before,local,spec=make(tmp_path)
    local[:,spec['root_node'],1,3]+=shift
    env=np.array([0,1,1,1,1,1,0.]) if fixed else np.ones(7)
    f=MeshContactTrajectoryFitter(rig,spec,local,env)
    c=CoupledMeshContactFitter(f,window_basis(env,2))
    return source,spec,f,c,MeshContactFeasibility(c)


@pytest.mark.parametrize('shift',[0.,-.26])
def test_floor_and_contact_derivatives_match_independent_full_mesh(tmp_path,shift):
    _,spec,f,c,s=setup(tmp_path,shift)
    rng=np.random.default_rng(423);x=rng.normal(size=np.prod(c.shape))*.002
    floor,fj,contact,cj=s.pair(x)
    def independent(z):
        values=c.parameters(z);floors=[];contacts=[]
        for frame,value in enumerate(values):
            points=f.rig.vertices(f.pose(frame,value)[0]);floors.append(1+points[:,1].min()/spec['screen']['floor_depth_m'])
            for target in f.active[frame]:
                ids=spec['patches'][target['patch']]['vertices']
                contacts.append(1-np.linalg.norm(points[ids].mean(axis=0)-target['target_position_m'])/spec['screen']['contact_error_m'])
        return np.r_[floors,contacts]
    np.testing.assert_allclose(np.r_[floor,contact],independent(x),atol=1e-10)
    for _ in range(12):
        direction=rng.normal(size=len(x));direction/=np.linalg.norm(direction);eps=1e-7
        numeric=(independent(x+eps*direction)-independent(x-eps*direction))/(2*eps)
        np.testing.assert_allclose(np.vstack([fj,cj])@direction,numeric,rtol=5e-5,atol=2e-6)


def test_stage_cannot_pursue_contacts_before_floor_restoration(tmp_path):
    _,_,_,_,s=setup(tmp_path,-.26)
    with pytest.raises(ValueError,match='Restore floor'):s.phase(tmp_path,'contacts',2)


def test_contact_stage_reaches_target_without_losing_floor_clearance(tmp_path):
    _,_,f,c,s=setup(tmp_path,fixed=True);before=f.world.copy()
    with threadpool_limits(limits=1):values,trace,result=s.solve(tmp_path,5,40)
    assert result['sampled_constraints_reached'] and result['floor_constraint_min']>=.01-1e-8
    assert result['phases']['floor']['attempted'] is False and result['phases']['contacts']['attempted']
    assert not result['cost_is_selection_metric'] and not result['infeasibility_proven']
    np.testing.assert_array_equal(values[[0,-1]],0)
    np.testing.assert_allclose(f.world[[0,-1]],before[[0,-1]],atol=1e-12)
    assert np.all(np.abs(values)<=f.bounds*f.envelope[:,None]+1e-8)
    assert all(f.constraints(i,x)[0].min()>=-1e-7 for i,x in enumerate(values))
    assert trace and trace[-1]['phase']=='contacts'


def test_unreachable_contact_keeps_floor_hard_and_does_not_claim_infeasibility(tmp_path):
    _,spec,f,c,_=setup(tmp_path)
    spec['contacts'][0]['target_position_m'][1]=-2.
    s=MeshContactFeasibility(c)
    with threadpool_limits(limits=1):values,_,result=s.solve(tmp_path,3,10)
    assert result['floor_constraint_min']>=.01-1e-8 and not result['contacts_reached']
    assert not result['infeasibility_proven'] and not result['quality_approved']
    assert np.all(np.abs(values)<=f.bounds+1e-8)
    for world in f.world:assert f.rig.vertices(world)[:,1].min()>=-.00495-1e-9


def test_failed_floor_restoration_skips_contacts_and_keeps_fixed_failure(tmp_path):
    _,_,f,c,s=setup(tmp_path,-.26,fixed=True);before=f.world.copy()
    with threadpool_limits(limits=1):values,trace,result=s.solve(tmp_path,3,10)
    assert result['contact_phase_skipped'] and result['phases']['contacts'] is None
    assert not result['floor_reached'] and not result['sampled_constraints_reached']
    assert all(r['phase']=='floor' for r in trace)
    np.testing.assert_array_equal(values[[0,-1]],0)
    np.testing.assert_allclose(f.world[[0,-1]],before[[0,-1]],atol=1e-12)


def test_actual_feasibility_export_records_mode_and_independent_checks(tmp_path):
    source,spec,_,_,_=setup(tmp_path);draft=tmp_path/'draft.json';save(draft,spec)
    out=tmp_path/'fit';result=run(source,draft,out,spacing=2,max_iterations=40,feasibility=True,floor_iterations=5)
    request=read(out/'request.json');summary=read(out/'feasibility-summary.json')
    assert request['feasibility'] is True and request['floor_iterations']==5
    assert summary['sampled_constraints_reached']
    check=read(out/'independent-inspection.json')
    assert check['floor_frames_failed']==check['failed_intervals']==0
    assert sha256(out/'contact-spec.json')==sha256(draft) and not result['quality_approved']
    assert result['selected_file']==('candidate.glb' if result['numerical_screen_passed'] else 'original.glb')


def test_crashed_export_is_archived_and_existing_output_is_preserved(tmp_path,monkeypatch):
    import rig_mesh_trajectory as module
    source,spec,_,_,_=setup(tmp_path);draft=tmp_path/'draft.json';save(draft,spec)
    def fail(*args,**kwargs):raise RuntimeError('Deliberate export fault')
    monkeypatch.setattr(module,'encode',fail);out=tmp_path/'failed'
    with pytest.raises(RuntimeError,match='export fault'):run(source,draft,out,2,1)
    assert read(out/'pipeline.json')['status']=='failed'
    assert read(out/'failure.json')['error_type']=='RuntimeError'
    assert sha256(out/'original.glb')==sha256(source) and sha256(out/'contact-spec.json')==sha256(draft)
    digest=sha256(out/'failure.json')
    with pytest.raises(FileExistsError):run(source,draft,out,2,1)
    assert sha256(out/'failure.json')==digest


def test_concurrently_created_folder_is_never_marked_failed_by_this_run(tmp_path,monkeypatch):
    source,spec,_,_,_=setup(tmp_path);draft=tmp_path/'draft.json';save(draft,spec)
    out=(tmp_path/'race').resolve();original_mkdir=Path.mkdir
    def concurrent_creation(path,*args,**kwargs):
        if path==out and not path.exists():
            original_mkdir(path,*args,**kwargs)
            (path/'pipeline.json').write_text('{"status":"other-worker"}',encoding='utf-8')
        return original_mkdir(path,*args,**kwargs)
    monkeypatch.setattr(Path,'mkdir',concurrent_creation)
    with pytest.raises(FileExistsError):run(source,draft,out,2,1)
    assert read(out/'pipeline.json')['status']=='other-worker'
    assert not (out/'failure.json').exists()


@pytest.mark.parametrize('changed',['source','draft'])
def test_input_change_during_copy_cannot_rebind_fitting_request(tmp_path,monkeypatch,changed):
    import rig_mesh_trajectory as module
    source,spec,_,_,_=setup(tmp_path);draft=tmp_path/'draft.json';save(draft,spec)
    target=source if changed=='source' else draft;copyfile=module.shutil.copyfile
    def mutate_before_copy(origin,destination,*args,**kwargs):
        if Path(origin)==target:target.write_bytes(target.read_bytes()+b' ')
        return copyfile(origin,destination,*args,**kwargs)
    monkeypatch.setattr(module.shutil,'copyfile',mutate_before_copy)
    out=tmp_path/'mutation'
    with pytest.raises(ValueError,match='changed while snapshotting'):run(source,draft,out,2,1)
    assert read(out/'pipeline.json')['status']=='failed'
    assert not (out/'result.json').exists()


@pytest.mark.parametrize('choice',[True,0,False,201])
def test_invalid_phase_budgets_do_not_mutate_trajectory(tmp_path,choice):
    _,_,f,_,s=setup(tmp_path);before=f.values.copy()
    with pytest.raises(ValueError,match='budget'):s.solve(tmp_path,choice,10)
    np.testing.assert_array_equal(f.values,before)


@pytest.mark.parametrize('choice',[1,None,'true'])
def test_cli_mode_requires_exact_boolean(tmp_path,choice):
    source,spec,_,_,_=setup(tmp_path);draft=tmp_path/'draft.json';save(draft,spec)
    with pytest.raises(ValueError,match='choice'):run(source,draft,tmp_path/'fit',feasibility=choice)
    assert not (tmp_path/'fit').exists()
