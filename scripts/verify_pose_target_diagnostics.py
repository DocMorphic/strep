"""Reconstruct diagnostic anchor probes without importing an optimizer."""
import argparse
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from strep import ROOT, read, save, sha256, now
from rig_asset import RigAsset


def angle(matrix):
    return np.degrees(Rotation.from_matrix(matrix).magnitude())


def verify(folder):
    report=read(folder/'diagnostic.json')
    source=ROOT/'reports/pose-trajectory-v1'/report['case']
    for name,digest in report['source_hashes'].items():
        assert sha256(source/name)==digest
    spec=read(source/'spec.json');request=read(source/'request.json')
    data=dict(np.load(source/'fit.npz',allow_pickle=False))
    probes=dict(np.load(folder/'probes.npz',allow_pickle=False))
    rig=RigAsset.load(source/'original.glb');frame=report['frame']
    root=spec['root_node'];edits=list(spec['edit_joints'].values())
    nodes=[entry['node'] for entry in edits];goal=request['joint_goal']
    limits=spec['limits'];env=request['envelope'][frame]
    rows=[]
    for label,key in [('retained_candidate','initial'),('bounds_only','bounds_only'),('fixed_neighbors','fixed_neighbors')]:
        x=probes[key];local=data['local_before'][frame].copy()
        for entry,vector in zip(edits,x[3:].reshape(-1,3)):
            local[entry['node'],:3,:3] @= Rotation.from_rotvec(vector).as_matrix()
        computed={}
        def world(node):
            if node in computed:return computed[node]
            parent=rig.parents[node]
            upstream=np.eye(4) if parent<0 else world(parent)
            transform=local[node].copy()
            if node==root:transform[:3,3]+=np.linalg.solve(upstream[:3,:3],x[:3])
            computed[node]=upstream@transform
            return computed[node]
        pose=np.array([world(i) for i in range(len(rig.parents))])
        target=pose[goal['node']]
        position=float(np.linalg.norm(target[:3,3]-goal['position_m']))
        orientation=float(angle(np.linalg.solve(np.array(goal['rotation_matrix']),target[:3,:3])))
        floor=max(0.,-float(rig.vertices(pose)[:,1].min()))
        actual_bounds=np.r_[[limits['root_horizontal_m']/np.sqrt(2),limits['root_vertical_m'],limits['root_horizontal_m']/np.sqrt(2)],
                           np.repeat(np.radians([e['limit_degrees'] for e in edits])/np.sqrt(3),3)]*env
        assert np.all(np.abs(x)<=actual_bounds+1e-9)
        residuals=[]
        for neighbor in [frame-1,frame+1]:
            if not 0<=neighbor<len(data['parameters']):continue
            d=x-data['parameters'][neighbor]
            residuals.append(float(1-(np.linalg.norm(d[:3])/limits['root_step_m'])**2))
            residuals.extend((1-(np.linalg.norm(d[3:].reshape(-1,3),axis=1)/np.radians(limits['joint_step_degrees']))**2).tolist())
            neighbor_local=data['local_before'][neighbor,nodes,:3,:3]@Rotation.from_rotvec(data['parameters'][neighbor,3:].reshape(-1,3)).as_matrix()
            reference_step=angle(np.linalg.solve(data['local_before'][neighbor,nodes,:3,:3],data['local_before'][frame,nodes,:3,:3]))
            candidate_step=angle(np.linalg.solve(neighbor_local,local[nodes,:3,:3]))
            limit=np.radians(np.minimum(180,reference_step+.5))
            residuals.extend(((2*np.cos(np.radians(candidate_step))-2*np.cos(limit))/np.maximum(2*(1-np.cos(limit)),1e-8)).tolist())
        recorded=report['probes'][label]
        assert abs(position-recorded['position_error_m'])<1e-9
        assert abs(orientation-recorded['orientation_error_degrees'])<1e-7
        assert abs(floor-recorded['anchor_skin_floor_depth_m'])<1e-9
        # Use the same dimensionless tolerance as the saved diagnostic. A
        # tolerance in meters/radians is not interchangeable near a boundary.
        feasible=min(residuals)>=-1e-7
        assert abs(min(residuals)-recorded['neighbor_constraint_min'])<1e-6
        assert feasible==recorded['neighbors_feasible']
        assert (position<=.005 and orientation<=5)==recorded['target_screen_passed']
        rows.append(dict(probe=label,position_error_m=position,orientation_error_degrees=orientation,
                         anchor_skin_floor_depth_m=floor,box_bounds_passed=True,neighbor_bounds_passed=feasible))
    save(folder/'verification.json',dict(verified_at=now(),source_hashes_passed=True,
        independent_fk_and_measurements_passed=True,probes=rows,quality_approved=False,
        verifier_sha256=sha256(Path(__file__)),diagnostic_sha256=sha256(folder/'diagnostic.json')))
    print(report['case']+' diagnostic reconstruction passed')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('folder',type=Path);args=p.parse_args();verify(args.folder)
