"""Independent geometry, warm-start provenance, objective and control-space audit."""
import numpy as np
from scipy.spatial.transform import Rotation
from strep import ROOT,read,save,sha256,now
from rig_asset import RigAsset
from rig_transition import localize
from verify_trajectory_fit import energy
from rig_trajectory_fit import DEFAULTS
import verify_pose_trajectory

OUT=ROOT/'reports/coupled-pose-v1'


def total(world,points,original_world,original_points,original_local,parents,spec,request):
    local=localize(world,parents)
    value=energy(world,points,local,original_world,original_points,original_local,
                 spec,request,request['supports'],DEFAULTS)['total']
    goal=request['joint_goal'];pose=world[goal['frame'],goal['node']]
    value+=float(np.sum(((pose[:3,3]-goal['position_m'])*goal['position_weight'])**2))
    value+=float(np.sum(((pose[:3,:3]-goal['rotation_matrix'])*goal['rotation_weight'])**2))
    return value


def run():
    frozen=read(OUT/'implementation.json')['files']
    assert sha256(ROOT/'scripts/rig_trajectory_fit.py')==frozen['rig_trajectory_fit.py']
    verify_pose_trajectory.OUT=OUT
    verify_pose_trajectory.verify()
    rows=[]
    for case in read(OUT/'protocol.json')['cases']:
        folder=OUT/case;source=ROOT/'reports/pose-trajectory-v1'/case
        provenance=read(folder/'warm-start.json')
        assert all(sha256(source/name)==digest for name,digest in provenance['files'].items())
        assert sha256(folder/'coordinate.glb')==provenance['files']['candidate.glb']
        data=dict(np.load(folder/'fit.npz',allow_pickle=False));warm=dict(np.load(source/'fit.npz',allow_pickle=False))
        assert np.array_equal(data['before'],warm['before']) and np.array_equal(data['warm_start'],warm['after'])
        assert np.array_equal(data['warm_parameters'],warm['parameters'])
        basis=np.load(folder/'basis.npy',allow_pickle=False)
        change=data['parameters']-data['warm_parameters']
        coefficients=np.linalg.lstsq(basis,change,rcond=None)[0]
        span_error=float(np.max(np.abs(basis@coefficients-change)));assert span_error<1e-9
        request=read(folder/'request.json');spec=read(folder/'spec.json');rig=RigAsset.load(folder/'original.glb')
        assert np.array_equal(basis[np.array(request['envelope'])==0],np.zeros_like(basis[np.array(request['envelope'])==0]))
        points={name:np.array([rig.vertices(w) for w in data[name]]) for name in ['before','warm_start','after']}
        energies={name:total(data[name],points[name],data['before'],points['before'],data['local_before'],rig.parents,spec,request) for name in ['warm_start','after']}
        summary=read(folder/'fit-summary.json')['convergence']
        assert abs(energies['warm_start']-summary['cost_before'])<1e-5
        assert abs(energies['after']-summary['cost_after'])<1e-5
        assert energies['after']<=energies['warm_start']+1e-7
        root=spec['root_node']
        save(folder/'root-motion.json',dict(space='SOMA pelvis world transform after experimental coordinated correction',
            times_s=(np.arange(len(data['after']))/30).tolist(),
            positions_m=data['after'][:,root,:3,3].tolist(),
            rotations_xyzw=Rotation.from_matrix(data['after'][:,root,:3,:3]).as_quat().tolist(),
            source_glb_sha256=sha256(folder/'candidate.glb'),quality_approved=False))
        rows.append(dict(case=case,warm_start_hashes_passed=True,original_unchanged=True,
                         control_span_max_error=span_error,independent_energy=energies,
                         solver_success=summary['solver_success'],quality_approved=False))
    save(OUT/'coupled-verification.json',dict(verified_at=now(),checks_passed=True,cases=rows,
        quality_approved=False,scope='Independent saved-array FK/geometry/energy and control-span checks, plus decoded GLB invariants. Shared frozen scalar weights; no optimizer invocation.'))
    from build_coupled_pose_review import build
    build(OUT)


if __name__=='__main__':run()
