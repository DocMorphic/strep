"""Independent native replay and radial-guide checks for a boundary patch."""
import copy
from pathlib import Path
import numpy as np
from strep import ROOT,read,sha256
from scene_solver_context import context_primitives


def verify(study,patch,problem,source,base_parameters):
    study,patch=Path(study).resolve(),Path(patch).resolve();prior=read(study/'protocol.json');protocol=read(patch/'protocol.json');result=read(patch/'result.json')
    if ROOT/protocol['base_study']!=study or result['status']!='complete':raise ValueError('Completed matching boundary patch required')
    for name,key in [('protocol.json','protocol_sha256'),('motion.npz','candidate_sha256')]:
        if sha256(patch/name)!=result[key]:raise ValueError('Boundary artifact changed')
    for path,digest in protocol['inputs'].items():
        if sha256(path)!=digest:raise ValueError('Boundary input changed')
    for name,digest in protocol['implementation'].items():
        if sha256(patch/'implementation'/name)!=digest:raise ValueError('Boundary snapshot changed')
    for name in ['source-motion.npz','source.glb','authored-scene.json','original-scene.json']:
        if sha256(patch/name)!=sha256(study/name):raise ValueError('Boundary changed source or authored scene')
    left,right=prior['edited_interval'];start,end=prior['projection_interval'];eligible=list(range(left+1,start))+list(range(end+1,right))
    assert protocol['eligible_frames']==eligible and [r['frame'] for r in result['rows']]==eligible
    changed=[r['frame'] for r in result['rows'] if r['changed']];assert changed==result['changed_frames']
    candidate=dict(np.load(patch/'motion.npz',allow_pickle=False));locked=np.setdiff1d(np.arange(prior['frame_count']),changed)
    for key in source:np.testing.assert_array_equal(source[key][locked],candidate[key][locked])
    columns=np.array([3*problem.lookup[problem.names.index(side+part)]+k for side in ['Left','Right'] for part in ['Shoulder','Arm','ForeArm','Hand'] for k in range(3)])
    np.testing.assert_array_equal(columns,protocol['arm_columns']);frozen=np.setdiff1d(np.arange(problem.dim),columns)
    p=copy.copy(problem);p.regions=[];maximum_guide_error=0.
    for row in result['rows']:
        frame=row['frame'];p.frame=frame;p.objects=[(g,o['id'],p.t(o['positions_m'][frame])[None],p.t(o['rotations'][frame])[None]) for g,o in context_primitives(p.context)]
        base=np.array(base_parameters[frame]);before,motion=p.independent(base);vertices=p.surface.vertices(motion['global_rot_mats'][0],motion['posed_joints'][0])
        for guide,binding in zip(row['guides'],prior['bindings']):
            assert guide['hand']==binding['hand'] and guide['anchor']==binding['anchor']
            root=p.names.index(binding['hand']);descendants={root}
            for j,parent in enumerate(p.parents):
                if parent in descendants:descendants.add(j)
            ids=np.flatnonzero(np.any(np.isin(p.skin['lbs_indices'],list(descendants))&(p.skin['lbs_weights']>0),axis=1));assert len(ids)==guide['vertex_count']
            g,_,center,rotation=next(o for o in p.objects if o[1]==binding['object_id']);center,rotation=center.numpy()[0],rotation.numpy()[0]
            radial=(vertices[binding['anchor']]-center)@rotation;radial[1]=0.;radial/=np.linalg.norm(radial);direction=rotation@radial
            np.testing.assert_allclose(direction,guide['direction'],atol=1e-14,rtol=0)
            margin=protocol['boundary_settings']['guide_clearance_m'];distance=guide['distance_m'];assert distance>=0
            original_gaps=g.distance_gradient(vertices[ids],center,rotation)[0];expected=0.
            if original_gaps.min()<margin:
                local=(vertices[ids]-center)@rotation;radius,height=g.dimensions
                eligible_points=local[np.abs(local[:,1])<height/2+margin][:,[0,2]];d=radial[[0,2]];axial=eligible_points@d
                discriminant=axial**2+(radius+margin)**2-np.sum(eligible_points**2,axis=1)
                intervals=sorted((-a-np.sqrt(v),-a+np.sqrt(v)) for a,v in zip(axial,discriminant) if v>0)
                for low,high in intervals:
                    if low<expected<high:expected=float(high)
            maximum_guide_error=max(maximum_guide_error,abs(expected-distance));assert abs(expected-distance)<1e-10
            assert g.distance_gradient(vertices[ids]+distance*direction,center,rotation)[0].min()>=margin-1e-10
        if row['changed']:
            values=np.array(row['parameters']);np.testing.assert_array_equal(values[frozen],base[frozen]);after,replay=p.independent(values)
            assert before==row['before'] and after==row['candidate'] and after['bounds_passed']
            assert after['pose_witness_passed']==row['geometry_and_bounds_passed']
            for key in candidate:np.testing.assert_array_equal(replay[key][0].astype(candidate[key].dtype),candidate[key][frame])
    return candidate,dict(study=patch.relative_to(ROOT).as_posix(),result_sha256=sha256(patch/'result.json'),protocol_sha256=sha256(patch/'protocol.json'),
        changed_frames=changed,unchanged_frames=len(locked),non_arm_parameters_exact=True,grasp_and_guard_exact=True,maximum_guide_error_m=maximum_guide_error)


def verify_floor(study,boundary,patch,problem,source):
    from region_floor_envelope import sample_weights
    study,boundary,patch=[Path(p).resolve() for p in (study,boundary,patch)]
    protocol,result=read(patch/'protocol.json'),read(patch/'result.json');base=read(study/'protocol.json')
    if ROOT/protocol['boundary_patch']!=boundary or ROOT/protocol['base_study']!=study or result['status']!='complete':raise ValueError('Matching completed floor patch required')
    if sha256(patch/'protocol.json')!=result['protocol_sha256'] or sha256(patch/'motion.npz')!=result['candidate_sha256']:raise ValueError('Floor artifact changed')
    for path,digest in protocol['inputs'].items():
        if sha256(path)!=digest:raise ValueError('Floor input changed')
    for name,digest in protocol['implementation'].items():
        if sha256(patch/'implementation'/name)!=digest:raise ValueError('Floor method snapshot changed')
    for name in ['source-motion.npz','source.glb','authored-scene.json','original-scene.json']:
        if sha256(patch/name)!=sha256(study/name):raise ValueError('Floor changed source or scene')
    cutoff=base['edited_interval'][0];free=protocol['floor_settings']['free_frames'];assert free==list(range(1,cutoff))
    delta=np.array(result['root_lift_delta_m']);assert delta.shape==(base['frame_count'],) and np.isfinite(delta).all() and np.all(delta>=0)
    locked=np.setdiff1d(np.arange(len(delta)),free);np.testing.assert_array_equal(delta[locked],0.)
    candidate=dict(np.load(patch/'motion.npz',allow_pickle=False))
    for key in source:
        expected=source[key].copy()
        if key=='root_positions':expected[:,1]+=delta
        elif key=='posed_joints':expected[:,:,1]+=delta[:,None]
        np.testing.assert_array_equal(expected,candidate[key]);np.testing.assert_array_equal(source[key][locked],candidate[key][locked])
    total=candidate['root_positions'][:,1]-problem.base['root_positions'][:,1]
    assert total.min()>=-1e-7 and total.max()<=problem.config['max_root_lift_m']+1e-7
    dense_path=ROOT/protocol['floor_base_audit']/'geometry/verification.json';dense=read(dense_path)
    assert dense['result_sha256']==sha256(study/'result.json') and dense['variants']['candidate']['glb_sha256']==sha256(study/'candidate.glb')
    original=dict(np.load(study/'motion.npz',allow_pickle=False))
    for key in source:np.testing.assert_array_equal(original[key][:cutoff+1],source[key][:cutoff+1])
    rows=[r for r in dense['variants']['candidate']['rows'] if r['frame']<=cutoff]
    predicted=np.array([r['minimum_floor_m'] for r in rows])+sample_weights([r['frame'] for r in rows],len(delta))@delta
    assert predicted.min()>=protocol['floor_settings']['target_height_m']-1e-10
    return candidate,dict(study=patch.relative_to(ROOT).as_posix(),result_sha256=sha256(patch/'result.json'),protocol_sha256=sha256(patch/'protocol.json'),
        maximum_lift_m=float(delta.max()),locked_frames_exact=len(locked),rotations_and_root_xz_exact=True,minimum_predicted_prefix_height_m=float(predicted.min()))
