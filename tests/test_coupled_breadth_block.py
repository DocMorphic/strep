import shutil
import sys
from pathlib import Path
import numpy as np
import pytest
from threadpoolctl import threadpool_limits
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from strep import ROOT,read,save
from study_coupled_breadth_block import select,make_problem
from audit_coupled_breadth import audit
from verify_authored_root_correction import samples
from authored_root_correction import export
from scipy.spatial.transform import Rotation


def test_selection_uses_relative_bound_and_keeps_nonexcluded_out():
    row=lambda name,bound,cap,excluded:dict(id=name,necessary_vertical_bound_max_m_s2=bound,acceptance_peak_m_s2=cap,excluded_by_vertical_bound=excluded)
    assert select(dict(rows=[row('large',10,5,True),row('relative',3,1,True),row('ignored',100,1,False)]))['id']=='relative'
    with pytest.raises(ValueError):select(dict(rows=[row('ignored',100,1,False)]))


@pytest.fixture(scope='module')
def context():
    folder=ROOT/'reports/coupled-breadth-block-v1'
    if not folder.exists():pytest.skip('Provisioned frozen coupled fixture required')
    request=read(folder/'request.json')
    with threadpool_limits(limits=1):problem=make_problem(folder,request)
    return folder,request,problem


def test_initial_pose_and_strict_floor_hover(context):
    _,_,p=context;x=p.initial[np.ix_(p.frames,p.free)].ravel()
    with threadpool_limits(limits=1):
        first=p.evaluate(x);assert first[2].min()>-1e-7 and p.geometric_guard(p.initial)
        lowered=x.copy();lowered[1]-=.002;result=p.evaluate(lowered);n=len(p.reference_skin[0])
        assert result[2][:n].min()<-.1
        # This mutation remains within the inherited 5mm floor, but violates the new guard.
        positions=p.fitter.rig.vertices(p.evaluator.pose(p.fitter.pose(int(p.frames[0]),result[5][p.frames[0]])[0]))
        assert positions[:,1].min()>-.005
        raised=x.copy();raised[1]+=.002;result=p.evaluate(raised)
        assert result[2][n:n+2].min()<-.1


def test_independent_audit_accepts_source_and_rejects_hover_mutant(context,tmp_path):
    folder,request,p=context;source=folder/'source/candidate/character.glb';take=tmp_path/'take';take.mkdir()
    shutil.copytree(folder/'source/input',take/'input');(take/'candidate').mkdir()
    for name in ['spec.json','request.json']:shutil.copyfile(folder/'source'/name,take/name)
    shutil.copyfile(folder/'source/candidate/contacts.json',take/'candidate/contacts.json')
    def sidecar():
        _,w=samples(take/'candidate/character.glb',len(p.initial));w=w[::2]
        save(take/'candidate/root-motion.json',dict(times_s=(np.arange(len(w))/30).tolist(),positions_m=w[:,p.root,:3,3].tolist(),rotations_xyzw=Rotation.from_matrix(w[:,p.root,:3,:3]).as_quat().tolist()))
    shutil.copyfile(source,take/'candidate/character.glb');sidecar()
    with threadpool_limits(limits=1):proof=audit(take,source,request['frames'],request['target']['centers'],request['target']['limit_m_s2'])
    assert proof['all_guards_passed'] and not proof['useful_target_improvement']
    rig,w=samples(source,len(p.initial));frame=int(p.frames[0]);parent=rig.parents[p.root]
    offsets=np.zeros((len(p.initial),3));offsets[frame]=np.linalg.solve(w[2*frame,parent,:3,:3],np.array([0.,.002,0.]))
    export(rig,p.root,offsets,take/'candidate/character.glb');sidecar()
    with threadpool_limits(limits=1):proof=audit(take,source,request['frames'],request['target']['centers'],request['target']['limit_m_s2'])
    assert not proof['all_guards_passed'] and not proof['checks']['hover']
