"""Independent decoded root-aware block audit, without optimizer caches."""
import argparse
from pathlib import Path
import numpy as np
from strep import read,save,sha256,now
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from verify_guarded_release import run as fixed_root_audit
from audit_release_normalized import run as normalized_audit


def run(folder,output):
    if output.exists():raise ValueError('Preserve prior audit')
    request=read(folder/'request.json');freeze=read(folder/'freeze.json');envelope=read(folder/'envelope.json')
    for name,digest in freeze.items():
        if sha256(folder/name)!=digest:raise ValueError('Frozen root protocol changed')
    if read(folder/'pipeline.json')['status']!='complete':raise ValueError('Completed trial required')
    output.mkdir(parents=True)
    # Retain the original fixed-root diagnostic in full, including its expected
    # root-preservation failure. The new protocol declares root movement.
    fixed_root_audit(folder,output/'fixed-root-diagnostic.json');decoded=read(output/'fixed-root-diagnostic.json')
    normalized=normalized_audit(folder,output/'normalized.json')
    source=Path(request['source_trial']) if request.get('source_trial') else Path(request['held'])
    prior_archive=source/'take/parameters.npz' if request.get('source_trial') else source/'fit.npz'
    source_glb=source/'take/candidate/character.glb' if request.get('source_trial') else source/'candidate/character.glb'
    old=np.load(prior_archive,allow_pickle=False)['parameters'];archive=np.load(folder/'take/parameters.npz',allow_pickle=False)
    np.testing.assert_array_equal(old,archive['initial']);values=archive['parameters'];frames=request['frames'];protected=envelope['protected_columns']
    outside=[f for f in range(len(values)) if f not in frames];np.testing.assert_array_equal(old[outside],values[outside]);np.testing.assert_array_equal(old[:,protected],values[:,protected])
    solver=read(folder/'take/solver.json');free=[i for i in range(values.shape[1]) if i not in protected]
    if solver['variable_frames']!=frames or solver['free_columns']!=free:raise ValueError('Solver coordinates differ')
    expected=old.copy();selected=np.ix_(frames,free)
    if solver.get('method') in ['feasible_linear_descent','conic_descent']:
        coordinates=old[selected].ravel().copy();np.testing.assert_array_equal(coordinates,solver['starting_coordinates'])
        if len(solver['history'])>request['steps']:raise ValueError('Exceeded linear descent step count')
        for step in solver['history']:
            accepted=[]
            for attempt in step['attempts']:
                if attempt['trust'] not in request['trusts'] or len(attempt['trials'])>8:raise ValueError('Linear proposal budget differs')
                for trial in attempt['trials']:
                    if trial['accepted']:
                        delta=np.asarray(attempt['proposed_delta'])
                        if trial['fraction'] not in [.5**i for i in range(8)] or np.abs(delta).max()>attempt['trust']+1e-12:
                            raise ValueError('Linear accepted step exceeds frozen bounds')
                        accepted.append(trial['fraction']*delta)
            if len(accepted)!=int(step['accepted']):raise ValueError('Ambiguous linear accepted step')
            if accepted:coordinates+=accepted[0]
        np.testing.assert_allclose(coordinates,solver['final_coordinates'],atol=1e-14,rtol=0)
        expected[selected]=coordinates.reshape(len(frames),len(free))
    elif solver['accepted_fraction'] is not None:expected[selected]+=solver['accepted_fraction']*(np.asarray(solver['proposed_coordinates']).reshape(len(frames),len(free))-old[selected])
    np.testing.assert_allclose(values,expected,atol=1e-14,rtol=0)
    spec=read(folder/'take/spec.json');world=[]
    for path in [source_glb,folder/'take/candidate/character.glb']:
        rig=RigAsset.load(path);sampler=AnimationSampler(rig.document,rig.binary,0)
        world.append(np.array([sampler.sample(float(np.float32(f/spec['fps']))) for f in range(spec['frames'])]))
    outside_error=max((float(np.abs(world[0][f]-world[1][f]).max()) for f in outside),default=0.)
    acceleration=np.diff(world[1][:,spec['root_node'],:3,3],n=2,axis=0)*spec['fps']**2;magnitude=np.linalg.norm(acceleration,axis=1)
    caps=np.asarray(envelope['root_safety_caps_m_s2']);margin=(caps**2-magnitude**2)/np.maximum(caps**2,1.)
    checks={name:value for name,value in decoded['envelope_checks'].items() if name!='held_root_acceleration_preserved'}
    checks.update(frozen_root_acceleration_envelope=bool(np.isfinite(margin).all() and margin.min()>=-1e-8),
        strict_normalized_foot_geometry_edits=normalized['all_applicable_checks_passed'],untouched_decoded_frames=outside_error<=1e-12)
    target=request['root_target'];target_max=float(magnitude[np.asarray(target['centers'])-1].max())
    result=dict(at=now(),completion_sha256=sha256(folder/'completion.json'),implementation_sha256=sha256(__file__),
        fixed_root_diagnostic_sha256=sha256(output/'fixed-root-diagnostic.json'),normalized_sha256=sha256(output/'normalized.json'),
        root_aware_checks=checks,all_root_aware_checks_passed=all(checks.values()),root_minimum_normalized_margin=float(margin.min()),
        root_acceleration_max_m_s2=float(magnitude.max()),root_peak_center_frame=int(magnitude.argmax()+1),
        remaining_root_failure_centers=(np.flatnonzero(magnitude>envelope['root_original_limit_m_s2'])+1).tolist(),
        target_acceleration_max_m_s2=target_max,target_limit_m_s2=target['limit_m_s2'],target_passed=target_max<=target['limit_m_s2'],
        untouched_frames=len(outside),untouched_decoded_max_matrix_error=outside_error,protected_parameters_unchanged=True,accepted_parameter_reconstruction=True,
        failed_full_checks=decoded['failed_full_checks'],engine_actor_frames=decoded['engine_actor_frames'],quality_approved=False,
        scope='New predeclared root-aware protocol: root preservation is not required; frozen per-center root acceleration and original decoded edit limits are. Original fixed-root diagnostic retained, not relabeled. All remaining numerical/full/engine checks independent of optimizer caches; no human quality claim.')
    save(output/'completion.json',result);print(result)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('folder',type=Path);p.add_argument('output',type=Path);a=p.parse_args();run(a.folder.resolve(),a.output.resolve())
