"""Package a fully audited cumulative continuation for ordinary Studio replay."""
import argparse
import copy
from pathlib import Path
import shutil
import numpy as np
from strep import ROOT,read,save,sha256,now
from audit_scene_pair_continuation import reviewed_trial,improvement_reasons
from assemble_scene_pair_reserve import bind_completed
from diagnose_scene_pair_limits import load_bound_study
from reserve_publication_geometry import checked_summary


def normalized_trials(trials,selected,geometry):
    if type(selected) is not int or not 0<=selected<len(trials):raise ValueError('Selected audited trial required')
    if trials[selected]['preliminary_pass'] is not True or trials[selected]['reasons']:raise ValueError('Selected trial failed preliminary checks')
    rows=[]
    for index,trial in enumerate(trials):
        reasons=list(trial['reasons'])
        if index!=selected and not reasons:reasons=['full_geometry_not_evaluated']
        rows.append(dict(folder='candidate' if index==selected else f'trial-{index}',factor=trial['factor'],
            controls=copy.deepcopy(trial['controls']),actors=copy.deepcopy(trial['actors']),bound=copy.deepcopy(trial['bounds']),
            angular_rates=copy.deepcopy(trial['angular_rates']),geometry=copy.deepcopy(geometry) if index==selected else None,
            accepted_local_step=index==selected,reasons=reasons,quality_approved=False))
    return rows


def run(geometry,output,prepared=None):
    geometry,output=Path(geometry).resolve(),Path(output).resolve()
    if output.exists():raise ValueError('Fresh continuation review package required')
    files={};methods={}
    grequest,gresult=bind_completed(geometry,[('manifest.json','manifest_sha256'),
        ('engine/verification.json','engine_verification_sha256')],files,methods)
    if gresult['accepted_local_step'] is not True or gresult['reasons']:
        raise ValueError('Full geometry has not accepted a local continuation')
    study=Path(grequest['study']).resolve();replay=Path(grequest['replay']).resolve();index=grequest['trial_index']
    request,selected,baseline,bound=reviewed_trial(study,replay,index);files.update(bound)
    parent=Path(request['study']).resolve();original,linear,parent_files=load_bound_study(parent);files.update(parent_files)
    if not original.get('angular_motion') or not original.get('curve_actors'):raise ValueError('Original refined angular policy required')
    if grequest['previous_peak_m']!=baseline['geometry']['candidate_peak_m'] or gresult['previous_peak_m']!=grequest['previous_peak_m']:
        raise ValueError('Previous correction peak differs')
    sources=[read(parent/'source'/n) for n in read(parent/'source-index.json')]
    gpath=geometry/'geometry.json'
    if sha256(gpath)!=gresult['geometry']['geometry_sha256']:raise ValueError('Full mesh observations changed')
    files[str(gpath)]=sha256(gpath)
    if checked_summary(sources,read(gpath),gresult['geometry']) or improvement_reasons(gresult['geometry'],gresult['previous_peak_m']):
        raise ValueError('Reconciled geometry does not improve the previous correction')
    if not np.isclose(gresult['improvement_over_previous_m'],gresult['previous_peak_m']-gresult['geometry']['candidate_peak_m'],atol=1e-12,rtol=0):
        raise ValueError('Reported continuation gain differs')
    manifest=read(geometry/'manifest.json')
    for actor in selected['actors']:
        matches=[c for c in manifest['cases'] if c['id']=='candidate-'+actor['actor']]
        if len(matches)!=1 or matches[0]['sha256']!=actor['sha256']:raise ValueError('Engine/geometry candidate differs')
    prepared_path=Path(original['prepared_request']).resolve()
    if prepared is not None:
        alias=Path(prepared).resolve()
        if sha256(alias)!=sha256(prepared_path):raise ValueError('Prepared review copy differs')
        files[str(alias)]=sha256(alias);prepared_path=alias
    margins=parent/'margins.npz';parent_result=read(parent/'result.json')
    if sha256(margins)!=parent_result['margins_sha256']:raise ValueError('Original empirical margins changed')
    files[str(margins)]=sha256(margins)
    normalized=normalized_trials(read(study/'trials.json'),index,gresult['geometry'])
    output.mkdir();(output/'implementation').mkdir()
    for name,(path,digest) in methods.items():shutil.copyfile(path,output/'implementation'/name)
    for name in ['assemble_scene_pair_continuation.py','assemble_scene_pair_reserve.py','reserve_publication_geometry.py']:
        source=ROOT/'scripts'/name;shutil.copyfile(source,output/'implementation'/name);methods[name]=(source,sha256(source))
    shutil.copytree(parent/'source',output/'source')
    # Ordinary replay checks source skin against a zero-control linearization.
    # Keep the actual nonzero proposal separately, with its own identity.
    for source,name in [(parent/'source-index.json','source-index.json'),(parent/'linearization.npz','linearization.npz'),
                        (study/'linearization.npz','proposal-linearization.npz'),(study/'solver.json','solver.json'),(margins,'margins.npz')]:
        shutil.copyfile(source,output/name)
    for i,trial in enumerate(normalized):
        folder=output/trial['folder'];folder.mkdir()
        for actor in trial['actors']:
            source=(study/f'trial-{i}'/actor['path']).resolve()
            if source.parent!=study/f'trial-{i}' or sha256(source)!=actor['sha256']:raise ValueError('Attempted export differs')
            shutil.copyfile(source,folder/actor['path'])
        if i==index:shutil.copyfile(gpath,folder/'geometry.json')
        save(folder/'review.json',trial)
    save(output/'trials.json',normalized)
    for case in manifest['cases']:
        source=(geometry/case['path']).resolve()
        if source.parent!=geometry or sha256(source)!=case['sha256']:raise ValueError('Manifest clip differs')
        files[str(source)]=case['sha256'];shutil.copyfile(source,output/case['path'])
    save(output/'manifest.json',dict(cases=manifest['cases'],quality_approved=False))
    save(output/'request.json',dict(original,at=now(),prepared_request=str(prepared_path),inputs=files,
        trust_degrees=request['incremental_trust_degrees'],factors=[t['factor'] for t in normalized],
        solver_scaling=dict(scale=request['scale'],regularizer=request['regularizer']),
        implementation={n:d for n,(_,d) in methods.items()},
        assembly=dict(continuation=str(study),replay=str(replay),geometry_audit=str(geometry),trial_index=index,
            cumulative_base=request['cumulative_controls'],solver_kind='increment_from_cumulative_base',
            proposal_linearization_sha256=sha256(output/'proposal-linearization.npz'),
            scope='Original zero-control source linearization retained for ordinary replay; actual nonzero proposal stored separately. All attempted cumulative exports preserved. No new inference, geometry, engine execution or release approval.')))
    for path,digest in files.items():
        if sha256(path)!=digest:raise ValueError('Continuation package input changed')
    for name,(_,digest) in methods.items():
        if sha256(output/'implementation'/name)!=digest:raise ValueError('Continuation package snapshot changed')
    save(output/'result.json',dict(at=now(),status='complete',selected='candidate',trials=len(normalized),
        **{n.replace('-','_')+'_sha256':sha256(output/(n+ext)) for n,ext in [('request','.json'),('source-index','.json'),('linearization','.npz'),('solver','.json'),('manifest','.json'),('trials','.json'),('margins','.npz')]},
        surface_rows=len(linear['gaps']),norm_rows=len(linear['radii']),provenance_method='assembled_audited_cumulative_continuation',quality_approved=False))
    save(output/'progress.json',dict(status='complete',selected='candidate'))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('geometry',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--prepared',type=Path);a=p.parse_args();run(a.geometry,a.output,a.prepared)
