import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from assemble_scene_pair_reserve import run
from strep import ROOT,read,save,sha256
from test_reserve_publication_geometry import rows


def complete(folder,artifacts):
    save(folder/'result.json',dict(status='complete',request_sha256=sha256(folder/'request.json'),
        **{key:sha256(folder/name) for name,key in artifacts.items()}))


def fixture(root):
    study=root/'study';study.mkdir();(study/'source').mkdir();(study/'implementation').mkdir()
    original,candidate,summary=rows();index={}
    for row in original:
        name=f"sample-{row['sample']:03d}.json";save(study/'source'/name,row);index[name]=sha256(study/'source'/name)
    save(study/'source-index.json',index)
    methods={}
    for name in ['coupled_pair_proposal.py','conic_root_descent.py']:
        (study/'implementation'/name).write_bytes((ROOT/'scripts'/name).read_bytes());methods[name]=sha256(study/'implementation'/name)
    prepared=root/'prepared.json';save(prepared,{'fixture':True})
    save(study/'request.json',dict(angular_motion=True,prepared_request=str(prepared),inputs={str(prepared):sha256(prepared)},implementation=methods))
    save(study/'solver.json',{});np.savez(study/'linearization.npz',gaps=np.array([-.02]),radii=np.array([1.]))
    complete(study,{'source-index.json':'source_index_sha256','linearization.npz':'linearization_sha256','solver.json':'solver_sha256'})
    audit=root/'audit';audit.mkdir();(audit/'implementation').mkdir();(audit/'trial-0').mkdir()
    actors=[];cases=[];motion=[];angular=[]
    geometry=root/'geometry';geometry.mkdir();(geometry/'implementation').mkdir()
    for i,name in enumerate(['A','B']):
        path=audit/'trial-0'/f'actor-{i}.glb';path.write_bytes(('candidate-'+name).encode());digest=sha256(path)
        actors.append(dict(actor=name,path=path.name,sha256=digest,preserved=True,rate_failures=0))
        rates={k:dict(exceeding_observations=0,tolerance=1e-5) for k in ['angular_speed_rad_s','angular_acceleration_rad_s2']}
        motion.append(dict(actor=name,positional=dict(failures=0),angular=rates));angular.append(dict(actor=name,rates=rates))
        for version in ['input','candidate']:
            target=geometry/f'{version}-actor-{i}.glb';target.write_bytes(path.read_bytes() if version=='candidate' else ('input-'+name).encode())
            cases.append(dict(id=version+'-'+name,path=target.name,sha256=sha256(target)))
    trial=dict(factor=1.,controls=[0.,0.,0.],actors=actors,motion_reviews=motion,bound=dict(cap=0.,distance=0.),preliminary_checks_pass=True,reasons=[])
    save(audit/'trial-0/review.json',trial);save(audit/'trials.json',[trial]);save(audit/'solver.json',dict(step=[0.,0.,0.]))
    np.savez(audit/'margins.npz',reserve=np.array([0.]))
    save(audit/'request.json',dict(study=str(study),inputs={},implementation={}))
    complete(audit,{'trials.json':'trials_sha256','solver.json':'solver_sha256','margins.npz':'margins_sha256'})
    save(geometry/'geometry.json',candidate);summary['geometry_sha256']=sha256(geometry/'geometry.json')
    save(geometry/'manifest.json',dict(cases=cases));save(geometry/'angular-replay.json',angular)
    (geometry/'engine').mkdir();save(geometry/'engine/verification.json',{'fixture':True})
    save(geometry/'request.json',dict(export_audit=str(audit),trial_index=0,factor=1.,inputs={},implementation={}))
    complete(geometry,{'manifest.json':'manifest_sha256','angular-replay.json':'angular_replay_sha256','engine/verification.json':'engine_verification_sha256'})
    result=read(geometry/'result.json');result.update(geometry=summary,reasons=[],accepted_local_step=True);save(geometry/'result.json',result)
    return study,audit,geometry


def test_assembly_retains_exact_clips_and_full_evidence(tmp_path):
    study,audit,geometry=fixture(tmp_path);out=tmp_path/'out';run(audit,geometry,out)
    result=read(out/'result.json');assert result['selected']=='candidate' and not result['quality_approved']
    assert result['provenance_method']=='assembled_completed_reserve_and_geometry'
    assert sha256(out/'candidate/actor-0.glb')==sha256(audit/'trial-0/actor-0.glb')
    assert sha256(out/'candidate/geometry.json')==sha256(geometry/'geometry.json')
    assert sha256(out/'linearization.npz')==sha256(study/'linearization.npz')
    assert {c['id'] for c in read(out/'manifest.json')['cases']}=={'input-A','input-B','candidate-A','candidate-B'}
    for path,digest in read(out/'request.json')['inputs'].items():assert sha256(path)==digest
    with pytest.raises(ValueError,match='Fresh'):run(audit,geometry,out)


@pytest.mark.parametrize('fault',['unfinished','geometry','clip','factor','angular','summary'])
def test_bad_or_unfinished_evidence_never_produces_completed_fit(tmp_path,fault):
    study,audit,geometry=fixture(tmp_path);result=read(geometry/'result.json')
    if fault=='unfinished':result['status']='processing'
    if fault=='geometry':save(geometry/'geometry.json',[])
    if fault=='clip':(geometry/'candidate-actor-0.glb').write_bytes(b'changed')
    if fault=='factor':
        request=read(geometry/'request.json');request['factor']=.5;save(geometry/'request.json',request);result['request_sha256']=sha256(geometry/'request.json')
    if fault=='angular':
        data=read(geometry/'angular-replay.json');data[0]['rates']['angular_speed_rad_s']['exceeding_observations']=1
        save(geometry/'angular-replay.json',data);result['angular_replay_sha256']=sha256(geometry/'angular-replay.json')
    if fault=='summary':result['geometry']['candidate_failed_times']=0
    save(geometry/'result.json',result);out=tmp_path/'out'
    with pytest.raises(ValueError):run(audit,geometry,out)
    assert not (out/'result.json').exists()


def test_completed_failed_geometry_keeps_sources_and_failed_attempt(tmp_path):
    study,audit,geometry=fixture(tmp_path)
    data=read(geometry/'geometry.json')
    for row in data:
        row['directions'][0]['max_depth_m']=.02;row['candidate_depth_m']=.02
    save(geometry/'geometry.json',data)
    result=read(geometry/'result.json');result['geometry'].update(candidate_peak_m=.02,geometry_sha256=sha256(geometry/'geometry.json'))
    result.update(reasons=['no_peak_improvement'],accepted_local_step=False);save(geometry/'result.json',result)
    out=tmp_path/'out';run(audit,geometry,out)
    assert read(out/'result.json')['selected'] is None
    assert {c['id'] for c in read(out/'manifest.json')['cases']}=={'input-A','input-B'}
    trial=read(out/'trials.json')[0]
    assert not trial['accepted_local_step'] and trial['reasons']==['no_peak_improvement']
    assert (out/'candidate/actor-0.glb').is_file()


@pytest.mark.parametrize('changed', [False, True])
def test_new_review_request_must_preserve_original_request_bytes(tmp_path, changed):
    study,audit,geometry=fixture(tmp_path);alias=tmp_path/'review-request.json'
    alias.write_bytes(Path(read(study/'request.json')['prepared_request']).read_bytes())
    if changed: save(alias, {'fixture':False})
    out=tmp_path/'out'
    if changed:
        with pytest.raises(ValueError,match='review copy differs'): run(audit,geometry,out,alias)
        assert not out.exists()
    else:
        run(audit,geometry,out,alias)
        request=read(out/'request.json')
        assert request['prepared_request']==str(alias.resolve())
        assert request['inputs'][str(alias.resolve())]==sha256(alias)


@pytest.mark.parametrize('fault', [None,'caps','kinds','width','description','binding'])
def test_refined_assembly_keeps_bound_basis_and_original_constraints(tmp_path, fault):
    from assemble_scene_pair_reserve import proposal_linearization
    study=tmp_path/'study';refinement=tmp_path/'refinement';refinement.mkdir()
    audit=tmp_path/'audit';audit.mkdir()
    original={key:np.ones((2,3) if key in ['surface_vectors','vectors'] else 2) for key in ['surface_vectors','gaps','depth_caps','vectors','radii']}
    original['kinds']=np.array(['speed','angular_speed'])
    linear={k:v.copy() for k,v in original.items()}
    linear.update(gap_jacobian=np.zeros((2,6)),surface_jacobians=np.zeros((2,3,6)),jacobians=np.zeros((2,3,6)))
    if fault=='caps':linear['radii'][0]+=.1
    if fault=='kinds':linear['kinds'][0]='edit'
    if fault=='width':linear['gap_jacobian']=np.zeros((2,3))
    np.savez(refinement/'linearization.npz',**linear)
    actors=[dict(actor='A',refined_controls=3),dict(actor='B',refined_controls=3)]
    save(refinement/'request.json',dict(study=str(study),actors=actors))
    save(audit/'request.json',dict(refinement=str(refinement)))
    files={str(p):sha256(p) for p in [refinement/'request.json',refinement/'linearization.npz',audit/'request.json']}
    request=dict(curve_actors=actors,refined_audit=str(audit),inputs=files)
    if fault=='description':request['curve_actors']=list(reversed(actors))
    if fault=='binding':files[str(refinement/'linearization.npz')]='0'*64
    if fault:
        with pytest.raises((ValueError,AssertionError)):proposal_linearization(request,study,original)
    else:
        path,found=proposal_linearization(request,study,original)
        assert path==refinement/'linearization.npz'
        assert found['jacobians'].shape[-1]==6
        np.testing.assert_array_equal(found['radii'],original['radii'])


@pytest.mark.parametrize('bad_step', [False,True])
def test_complete_refined_assembly_copies_fitted_matrix_and_curve_metadata(tmp_path,bad_step):
    study,audit,geometry=fixture(tmp_path)
    original={key:np.ones((2,3) if key in ['surface_vectors','vectors'] else 2) for key in ['surface_vectors','gaps','depth_caps','vectors','radii']}
    original['kinds']=np.array(['speed','angular_speed'])
    np.savez(study/'linearization.npz',**original)
    complete(study,{'source-index.json':'source_index_sha256','linearization.npz':'linearization_sha256','solver.json':'solver_sha256'})
    refinement=tmp_path/'refinement';refinement.mkdir();prior=tmp_path/'prior-audit';prior.mkdir()
    linear=dict(original,gap_jacobian=np.zeros((2,6)),surface_jacobians=np.zeros((2,3,6)),jacobians=np.zeros((2,3,6)))
    np.savez(refinement/'linearization.npz',**linear)
    actors=[dict(actor='A',refined_controls=3),dict(actor='B',refined_controls=3)]
    save(refinement/'request.json',dict(study=str(study),actors=actors))
    save(prior/'request.json',dict(refinement=str(refinement)))
    files={str(p):sha256(p) for p in [refinement/'request.json',refinement/'linearization.npz',prior/'request.json']}
    request=read(audit/'request.json');request.update(curve_actors=actors,refined_audit=str(prior),inputs=files)
    save(audit/'request.json',request)
    trial=read(audit/'trials.json')[0];trial['controls']=[0.]*(3 if bad_step else 6)
    save(audit/'trial-0/review.json',trial);save(audit/'trials.json',[trial]);save(audit/'solver.json',dict(step=trial['controls']))
    complete(audit,{'trials.json':'trials_sha256','solver.json':'solver_sha256','margins.npz':'margins_sha256'})
    out=tmp_path/'out'
    if bad_step:
        with pytest.raises(ValueError,match='solver step'):run(audit,geometry,out)
        assert not out.exists()
    else:
        run(audit,geometry,out)
        assert read(out/'request.json')['curve_actors']==actors
        assert sha256(out/'linearization.npz')==sha256(refinement/'linearization.npz')
        assert read(out/'result.json')['selected']=='candidate'
