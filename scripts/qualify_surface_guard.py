"""Apply the new guard to complete, hash-bound saved mesh observations."""
import argparse
from pathlib import Path
import shutil
from strep import ROOT, read, save, sha256, now


def run(replay, output):
    from rig_asset import RigAsset, array
    from sampled_surface_guard import topology, snapshot, compare
    replay, output = Path(replay).resolve(), Path(output).resolve()
    if output.exists(): raise ValueError('Fresh qualification output required')
    result = read(replay/'result.json')
    if result['status']!='complete': raise ValueError('Completed replay required')
    inputs = {str(replay/'result.json'):sha256(replay/'result.json')}
    for name,digest in result['outputs'].items():
        path=(replay/name).resolve()
        if path.parent!=replay or sha256(path)!=digest: raise ValueError('Replay output changed')
        inputs[str(path)]=digest
    request=read(replay/'request.json')
    for path,digest in request['inputs'].items():
        if sha256(path)!=digest: raise ValueError('Replay input changed')
        inputs[path]=digest
    for name,digest in request['implementation'].items():
        path=(replay/'implementation'/name).resolve()
        if path.parent!=replay/'implementation' or sha256(path)!=digest: raise ValueError('Archived replay method changed')
        inputs[str(path)]=digest
    def bound(path):
        path=Path(path).resolve()
        if inputs.get(str(path))!=sha256(path): raise ValueError('Unbound qualification input: '+str(path))
        return read(path)
    donor=Path(request['donor']); finger=Path(request['finger_study'])
    versions=[]
    for folder in [donor,replay]:
        faces=[];counts=[]
        for clip in bound(folder/'decoded.json')['clips']:
            path=(folder/clip['path']).resolve()
            if inputs.get(str(path))!=clip['sha256'] or sha256(path)!=clip['sha256']: raise ValueError('Clip changed')
            rig=RigAsset.load(path)
            if len(rig.primitives)!=1: raise ValueError('This historical audit requires one primitive per actor')
            p=rig.primitives[0];mesh=rig.document['meshes'][rig.document['nodes'][p['node']]['mesh']]['primitives'][p['primitive']]
            faces.append(array(rig.document,rig.binary,mesh['indices']).reshape(-1,3));counts.append(len(p['positions']))
        versions.append(topology(faces,counts))
    baseline={r['time_s']:r for r in bound(finger/'geometry.json')}
    rows=[[],[]]
    for row in bound(replay/'geometry.json'):
        if [v['version'] for v in row['versions']]!=['donor','diagnostic']: raise ValueError('Paired observation order required')
        original=baseline[row['time_s']];surface=bound(finger/original['path'])
        if original['sha256']!=sha256(finger/original['path']): raise ValueError('Donor geometry changed')
        for i,version in enumerate(row['versions']):
            if i:
                surface=bound(replay/version['path'])
                if version['sha256']!=sha256(replay/version['path']): raise ValueError('Candidate geometry changed')
            if surface['counts']!=version['counts']: raise ValueError('Observation counts changed')
            rows[i].append(dict(time_s=row['time_s'],surface=surface,depths=version['full_vertex_depths']))
    original,candidate=[snapshot(m,r) for m,r in zip(versions,rows)]
    decision=compare(original,candidate)
    output.mkdir();(output/'implementation').mkdir();methods={}
    for name in ['qualify_surface_guard.py','sampled_surface_guard.py','rig_asset.py','gltf_tools.py','strep.py']:
        path=ROOT/'scripts'/name;methods[name]=sha256(path);shutil.copyfile(path,output/'implementation'/name)
    save(output/'request.json',dict(at=now(),inputs=inputs,implementation=methods,scope='New acceptance policy on saved complete observations; no fresh geometry claimed'))
    save(output/'original.json',original);save(output/'candidate.json',candidate);save(output/'decision.json',decision)
    for path,digest in inputs.items():
        if sha256(path)!=digest: raise ValueError('Qualification input changed')
    save(output/'result.json',dict(at=now(),status='complete',outputs={p.name:sha256(p) for p in output.iterdir() if p.is_file()},
        passed=decision['passed'],failed_times=sum(not r['passed'] for r in decision['samples']),
        new_proper_pair_times=sum(len(r['new_proper_pairs']) for r in decision['samples']),
        new_uncertain_pair_times=sum(len(r['new_uncertain_pairs']) for r in decision['samples']),
        collision_free_certified=False,quality_approved=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('replay',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args();run(args.replay,args.output)
