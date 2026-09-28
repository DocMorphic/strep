"""Read-only contact checks for retained, rejected trajectory proposals."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from threadpoolctl import threadpool_limits
from strep import ROOT,read,save,sha256,now
from rig_asset import RigAsset,array
from bounded_pose_ik import hierarchy_order,world_matrices
from verify_palm_region import measure


def run(study,output):
    study,output=Path(study).resolve(),Path(output).resolve()
    if output.exists():raise ValueError('Preserve earlier diagnostic')
    request=read(study/'request.json');raw=(study/'history.json').read_bytes();history=json.loads(raw)['iterations']
    if len(history)<2:raise ValueError('No recorded proposals yet')
    previous,current=history[0],history[1]
    trials=[dict(alpha=0.,parameters=previous['parameters'],depths_m=[max(c['max_depth_m'] for c in s['collision']) for s in previous['window']])]+current['step_trials']
    scene_path=Path(request['source_scene'])
    if sha256(scene_path)!=request['source_scene_sha256']:raise ValueError('Scene changed')
    scene=read(scene_path)['scene'];patches=read(study/'palm-region.json');basis=np.asarray(read(study/'initial-parameters.json')['basis'])
    if sha256(study/'palm-region.json')!=request['palm_region_sha256']:raise ValueError('Patches changed')
    actors=[]
    for label in ['A','B']:
        src=request['sources'][label];path=Path(src['raw_glb']);local_path=study/f'{label}-source-local.npz'
        if sha256(path)!=src['raw_glb_sha256'] or sha256(local_path)!=src['local_npz_sha256']:raise ValueError('Source changed')
        rig=RigAsset.load(path);local=np.load(local_path,allow_pickle=False)['authored_finger_local'][75]
        names={n.get('name'):i for i,n in enumerate(rig.document['nodes'])};nodes=[names[n] for n in ['LeftShoulder','LeftArm','LeftForeArm','LeftHand']]
        placement=scene['actors'][label]['transform'];r=Rotation.from_quat(placement['rotation_xyzw']).as_matrix();t=np.asarray(placement['translation_m'])
        actors.append((rig,local,nodes,r,t))
    primitive=actors[0][0].document['meshes'][0]['primitives'][0]
    faces=array(actors[0][0].document,actors[0][0].binary,primitive['indices']).reshape(-1,3)
    base=np.asarray(trials[0]['depths_m']);rows=[]
    with threadpool_limits(limits=1):
        for trial in trials:
            if 'depths_m' not in trial:continue
            points=[]
            for (rig,source,nodes,r,t),part in zip(actors,np.split(np.asarray(trial['parameters']),2)):
                delta=basis[75]@np.asarray(part).reshape(5,12);local=source.copy()
                local[nodes,:3,:3]=local[nodes,:3,:3]@Rotation.from_rotvec(delta.reshape(4,3)).as_matrix()
                world=world_matrices(local,rig.parents,hierarchy_order(rig.parents));points.append(rig.vertices(world)@r.T+t)
            region=measure(points,[patches['A'],patches['B']],faces,.003)
            region_pass=all(d['within_tolerance_count']>=3 and min(d['source_area_witness']['area_m2'],d['target_area_witness']['area_m2'])>=2.5e-5 for d in region['directions'])
            depths=np.asarray(trial['depths_m'])
            if depths.shape!=base.shape:raise ValueError('Different trial clock')
            strict=[dict(frame=s['frame'],before_m=float(a),after_m=float(b)) for s,a,b in zip(previous['window'],base,depths) if b>max(1e-6,a)]
            screen_nonregressing=bool(np.all(depths<=np.maximum(base,.005)+1e-9))
            event_index=next(i for i,s in enumerate(previous['window']) if s['frame']==75)
            rows.append(dict(alpha=trial['alpha'],region=region,region_area_pass=region_pass,normal_within_20_degrees=region['opposing_normal_degrees']<=20,
                event_recorded_depth_m=float(depths[event_index]),peak_recorded_depth_m=float(depths.max()),
                strict_depth_regressions=strict,no_new_5mm_sample_failures_and_no_worse_existing_failures=screen_nonregressing,
                previously_accepted=trial.get('accepted'),quality_approved=False))
    output.mkdir();(output/'history-snapshot.json').write_bytes(raw)
    save(output/'summary.json',dict(at=now(),study=str(study),source_request_sha256=sha256(study/'request.json'),history_snapshot_sha256=hashlib.sha256(raw).hexdigest(),
        initial_parameters_sha256=sha256(study/'initial-parameters.json'),diagnostic_sha256=sha256(__file__),rows=rows,quality_approved=False,
        scope='First retained proposal set only. Reconstructed event skin/contact region; depth values reused from recorded all-surface queries at sparse fitting samples. 5mm screen comparison is diagnostic, not a changed live protocol or accepted candidate. No full motion/export/semantic approval.'))
    print([{k:r[k] for k in ['alpha','region_area_pass','normal_within_20_degrees','event_recorded_depth_m','peak_recorded_depth_m','no_new_5mm_sample_failures_and_no_worse_existing_failures']} for r in rows],flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('study',type=Path);p.add_argument('output',type=Path);a=p.parse_args();run(a.study,a.output)
