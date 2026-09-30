"""Bind all saved crossing times to the actual native finger control support."""
import argparse
from pathlib import Path
import shutil
import numpy as np
from strep import ROOT, read, save, sha256, now


def run(study, prepared_folder, output):
    from rig_asset import RigAsset
    from rig_clip_import import AnimationSampler
    from scene_pair_problem import load_actors
    from native_finger_motion import NativeFingerMotion
    from paired_approach_basis import BoundSkin
    from replay_finger_proposal import verify_scale
    from window_triangle_objective import compile_window, finger_support
    study,prepared_folder,output=map(lambda p:Path(p).resolve(),[study,prepared_folder,output])
    if output.exists():raise ValueError('Fresh window audit output required')
    result=read(study/'result.json');request=read(study/'request.json')
    if result['status']!='complete':raise ValueError('Completed finger study required')
    files={str(study/'result.json'):sha256(study/'result.json')}
    for name,digest in result['outputs'].items():
        path=(study/name).resolve()
        if path.parent!=study or sha256(path)!=digest:raise ValueError('Study output changed')
        files[str(path)]=digest
    for path,digest in request['inputs'].items():
        if sha256(path)!=digest:raise ValueError('Study input changed')
        files[path]=digest
    if files.get(str(prepared_folder/'request.json'))!=sha256(prepared_folder/'request.json'):
        raise ValueError('Prepared scene is not bound to the study')
    prepared,actors=load_actors(prepared_folder)
    scene_path=(prepared_folder/prepared['scene_snapshot']['path']).resolve()
    if not scene_path.is_relative_to(prepared_folder) or sha256(scene_path)!=prepared['scene_snapshot']['sha256']:
        raise ValueError('Bound scene required')
    files[str(scene_path)]=sha256(scene_path);scene=read(scene_path)['scene']
    contact=next(c for c in scene['contacts'] if c['id'] in prepared['authored']['protected_contact_ids'])
    times=np.asarray(request['audit_times_s']);geometry=read(study/'geometry.json')
    if [r['time_s'] for r in geometry]!=times.tolist():raise ValueError('Complete recorded audit clock required')
    samples=[]
    for row in geometry:
        path=(study/row['path']).resolve()
        if files.get(str(path))!=row['sha256']:raise ValueError('Unbound geometry')
        surface=read(path);pairs=[[r['left_triangle'],r['right_triangle']] for r in surface['records'] if r['kind']=='proper_crossing']
        if len(pairs)!=row['counts'].get('proper_crossing',0) or row['counts']!=surface['counts']:raise ValueError('Complete crossing population required')
        samples.append(dict(time_s=row['time_s'],proper=pairs))
    points=[];supports=[];scales=[];clips=[]
    donor=Path(request['donor']);donor_clips=read(donor/'decoded.json')['clips']
    for i,(actor,clip) in enumerate(zip(actors,read(study/'decoded.json')['clips'])):
        path=(study/clip['path']).resolve()
        if files.get(str(path))!=clip['sha256'] or clip['sha256']!=donor_clips[i]['sha256']:
            raise ValueError('Audit currently requires unchanged donor clips')
        rig=RigAsset.load(path);target=contact['effector'] if i==0 else contact['target']
        hand=next(n for n,node in enumerate(rig.document['nodes']) if node.get('name')==target['joint'])
        model=NativeFingerMotion(rig,hand,request['selected_nodes'][i],request['edit_limits_degrees'][i],times,request['window_s'],request['contact_time_s'])
        worlds=model.world(np.zeros(model.size));reader=AnimationSampler(rig.document,rig.binary,0)
        np.testing.assert_array_equal(worlds,np.array([reader.sample(t) for t in times]))
        points.append([rig.vertices(w)@actor['rotation'].T+actor['translation'] for w in worlds])
        supports.append(finger_support(model,BoundSkin(rig),times));scales.append(np.repeat(model.limits/np.sqrt(3),3))
        clips.append(dict(path=str(path),sha256=clip['sha256']))
    verify_scale(request['scale'],np.concatenate(scales))
    value=compile_window(times,samples,[a['faces'] for a in actors],list(zip(*points)),list(zip(*supports)))
    output.mkdir();(output/'implementation').mkdir();methods={}
    names=set(request['implementation'])|{'audit_window_triangle_controls.py','window_triangle_objective.py','replay_finger_proposal.py'}
    for name in sorted(names):
        path=ROOT/'scripts'/name;methods[name]=sha256(path);shutil.copyfile(path,output/'implementation'/name)
    save(output/'request.json',dict(at=now(),inputs=files,implementation=methods,study=str(study),prepared=str(prepared_folder),
        clips=clips,window_s=request['window_s'],audit_times_s=times.tolist(),selected_nodes=request['selected_nodes'],
        edit_limits_degrees=request['edit_limits_degrees'],scale=request['scale'],contact_time_s=request['contact_time_s']))
    save(output/'triangles.json',value)
    for path,digest in files.items():
        if sha256(path)!=digest:raise ValueError('Window audit input changed')
    save(output/'result.json',dict(at=now(),status='complete',outputs={p.name:sha256(p) for p in output.iterdir() if p.is_file()},
        all_crossing_pairs=value['all_crossing_pairs'],potentially_editable_pairs=value['potentially_editable_pairs'],
        unaffected_pairs=value['all_crossing_pairs']-value['potentially_editable_pairs'],quality_approved=False))
    print(value['summary'],flush=True)


if __name__=='__main__':
    from threadpoolctl import threadpool_limits
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('study',type=Path);parser.add_argument('prepared',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args()
    with threadpool_limits(limits=1):run(args.study,args.prepared,args.output)
