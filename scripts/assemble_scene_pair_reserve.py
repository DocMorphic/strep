"""Package completed reserve/geometry evidence for ordinary Studio replay and import."""
import argparse
import copy
from pathlib import Path
import shutil
import numpy as np
from strep import ROOT,read,save,sha256,now
from diagnose_scene_pair_limits import load_bound_study
from audit_refined_pair_geometry import selected_trial
from reserve_publication_geometry import checked_summary


def bind_completed(folder, artifacts, files, methods):
    result,request=read(folder/'result.json'),read(folder/'request.json')
    if result['status']!='complete': raise ValueError('Completed evidence required')
    for name,key in [('request.json','request_sha256'),*artifacts]:
        path=folder/name
        if sha256(path)!=result[key]: raise ValueError('Completed artifact changed: '+name)
        files[str(path)]=result[key]
    files[str(folder/'result.json')]=sha256(folder/'result.json')
    for path,digest in request['inputs'].items():
        if sha256(path)!=digest or (path in files and files[path]!=digest): raise ValueError('Completed input binding changed')
        files[path]=digest
    for name,digest in request['implementation'].items():
        path=(folder/'implementation'/name).resolve()
        if path.parent!=(folder/'implementation').resolve() or sha256(path)!=digest: raise ValueError('Completed method changed')
        if name in methods and methods[name][1]!=digest: raise ValueError('Incompatible method snapshots: '+name)
        methods[name]=(path,digest);files[str(path)]=digest
    return request,result


def run(audit,geometry,output):
    audit,geometry,output=[Path(p).resolve() for p in [audit,geometry,output]]
    if output.exists(): raise ValueError('Fresh assembled fit required')
    files={}; methods={}
    geometric,gresult=bind_completed(geometry,[('manifest.json','manifest_sha256'),('engine/verification.json','engine_verification_sha256'),
        ('angular-replay.json','angular_replay_sha256')],files,methods)
    if Path(geometric['export_audit']).resolve()!=audit: raise ValueError('Geometry belongs to another export audit')
    request,result=bind_completed(audit,[('trials.json','trials_sha256'),('solver.json','solver_sha256'),('margins.npz','margins_sha256')],files,methods)
    index=geometric['trial_index']; _,reviewed=selected_trial(audit,index)
    trials=read(audit/'trials.json')
    if reviewed['factor']!=geometric['factor']: raise ValueError('Geometry fraction differs')
    solver=read(audit/'solver.json'); step=np.asarray(solver['step'])
    for trial in trials:
        np.testing.assert_array_equal(np.asarray(trial['controls']),step*trial['factor'])
    study=Path(request['study']).resolve(); original,linear,bound=load_bound_study(study);files.update(bound)
    if not original.get('angular_motion'): raise ValueError('Original angular policy required')
    source=[read(study/'source'/n) for n in read(study/'source-index.json')]
    if sha256(geometry/'geometry.json')!=gresult['geometry']['geometry_sha256']: raise ValueError('Full geometry changed')
    files[str(geometry/'geometry.json')]=sha256(geometry/'geometry.json')
    reasons=checked_summary(source,read(geometry/'geometry.json'),gresult['geometry'])
    if reasons!=gresult['reasons'] or gresult['accepted_local_step'] != (not reasons): raise ValueError('Geometry decision differs')
    # Reconcile the independently replayed rotations against the reviewed actor bytes.
    angular=read(geometry/'angular-replay.json'); manifest=read(geometry/'manifest.json')
    if [a['actor'] for a in angular]!=[a['actor'] for a in reviewed['actors']]: raise ValueError('Angular participants differ')
    for actor in angular:
        if set(actor['rates'])!={'angular_speed_rad_s','angular_acceleration_rad_s2'} or any(r['exceeding_observations']!=0 or r['tolerance']!=1e-5 for r in actor['rates'].values()):
            raise ValueError('Passing independent angular review required')
    for actor in reviewed['actors']:
        matches=[c for c in manifest['cases'] if c['id']=='candidate-'+actor['actor']]
        if len(matches)!=1 or matches[0]['sha256']!=actor['sha256']: raise ValueError('Geometry/engine clip differs from reviewed export')
    selected='candidate' if not reasons else None
    output.mkdir();(output/'implementation').mkdir()
    for name,(path,digest) in methods.items():shutil.copyfile(path,output/'implementation'/name)
    for name in ['assemble_scene_pair_reserve.py','reserve_publication_geometry.py']:
        path=ROOT/'scripts'/name;shutil.copyfile(path,output/'implementation'/name);methods[name]=(path,sha256(path))
    shutil.copytree(study/'source',output/'source')
    for name in ['source-index.json','linearization.npz']:shutil.copyfile(study/name,output/name)
    shutil.copyfile(audit/'solver.json',output/'solver.json');shutil.copyfile(audit/'margins.npz',output/'margins.npz')
    normalized=[]
    for i,trial in enumerate(trials):
        name='candidate' if i==index else f'trial-{i}';folder=output/name;folder.mkdir()
        for actor in trial['actors']:
            path=(audit/f'trial-{i}'/actor['path']).resolve()
            if path.parent!=(audit/f'trial-{i}').resolve() or sha256(path)!=actor['sha256']: raise ValueError('Attempted export changed')
            files[str(path)]=actor['sha256'];shutil.copyfile(path,folder/actor['path'])
        row=dict(folder=name,factor=trial['factor'],controls=trial['controls'],actors=trial['actors'],bound=trial['bound'],
            angular_rates=[dict(actor=a['actor'],rates=a['angular']) for a in trial['motion_reviews']],
            geometry=copy.deepcopy(gresult['geometry']) if i==index else None,
            accepted_local_step=i==index and not reasons,reasons=reasons if i==index else trial['reasons'],quality_approved=False)
        if i!=index and not row['reasons']:row['reasons']=['full_geometry_not_evaluated']
        if i==index:shutil.copyfile(geometry/'geometry.json',folder/'geometry.json')
        save(folder/'review.json',row);normalized.append(row)
    save(output/'trials.json',normalized)
    cases=[]
    for case in manifest['cases']:
        if not case['id'].startswith('input-') and selected is None:continue
        path=(geometry/case['path']).resolve()
        if path.parent!=geometry or sha256(path)!=case['sha256']:raise ValueError('Manifest export changed')
        files[str(path)]=case['sha256'];shutil.copyfile(path,output/case['path']);cases.append(case)
    save(output/'manifest.json',dict(cases=cases,quality_approved=False))
    protocol=dict(original,at=now(),inputs=files,implementation={n:digest for n,(_,digest) in methods.items()},
        assembly=dict(export_audit=str(audit),geometry_audit=str(geometry),trial_index=index,
            scope='Copies and reconciles completed measured evidence. No refitting, regenerated motion, new mesh queries or release approval. Proposal used saved empirical margins; original acceptance limits remain unchanged.'))
    save(output/'request.json',protocol)
    for path,digest in files.items():
        if sha256(path)!=digest:raise ValueError('Assembly evidence changed')
    for name,(_,digest) in methods.items():
        if sha256(output/'implementation'/name)!=digest:raise ValueError('Copied method changed')
    save(output/'result.json',dict(at=now(),status='complete',selected=selected,trials=len(trials),quality_approved=False,
        **{n.replace('-','_')+'_sha256':sha256(output/(n+ext)) for n,ext in [('request','.json'),('source-index','.json'),('linearization','.npz'),('solver','.json'),('manifest','.json'),('trials','.json')]},
        margins_sha256=sha256(output/'margins.npz'),surface_rows=len(linear['gaps']),norm_rows=len(linear['radii']),
        provenance_method='assembled_completed_reserve_and_geometry'))
    save(output/'progress.json',dict(status='complete',selected=selected))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('audit',type=Path);p.add_argument('geometry',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    run(a.audit,a.geometry,a.output)
