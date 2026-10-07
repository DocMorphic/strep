"""Run buffered proposals against every original actual-export and scene gate.

This development fixture runner requires authenticated archived studies.
It is not model inference, production-rig approval or a portable installer.
"""
from pathlib import Path
import sys,json,argparse
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from buffered_component_trial_preflight import preflight
from action_worker_lock import worker_lock


def eligible(record):
    """Only an actually passing changed export may enter full-scene assessment.

Empirical affine margins are proposal diagnostics, not actual acceptance
conditions. Passing those margins never excuses a failing stored export.
    """
    return (record['anchor_export_hashes_match'] is False
        and all(record[key] is True for key in ('original_step_box_pass', 'native_conditions_pass',
            'parameter_conditions_pass', 'actual_material_depth_ceiling_pass',
            'actual_legacy_triangle_ceiling_pass', 'actual_integral_improved'))
        and record['reference_bounds']['passed'] is True
        and all(type(record[key]) is int and record[key] == 0 for key in
            ('failed_native_rows', 'vector_norm_failures', 'failed_contact_rows',
             'actual_guard_failures', 'actual_positive_component_failures')))


def run(request_path):
    if not __debug__:
        raise RuntimeError('Scientific assertions must be enabled; do not use optimized Python')
    checked=preflight(request_path)
    if checked['status']!='ready-for-numerical-validation':
        return checked
    with worker_lock():
        checked=preflight(request_path)
        if checked['status']!='ready-for-numerical-validation':
            return checked
        return _execute(checked)


def _execute(checked):
    import copy,shutil,time,traceback
    import numpy as np
    from scipy import sparse
    from threadpoolctl import threadpool_limits
    from native_stored_pair_job import Job,METHODS as JOB_METHODS
    from native_scene_contacts import SceneContacts
    from native_stored_pair_model import centered_problem
    from native_material_witness_guides import MaterialWitnessGuides
    from native_component_trajectory_model import ComponentTrajectoryModel,observe,deficits
    from native_component_trajectory_margin_step import direction
    from native_empirical_material_margins import EmpiricalMaterialMargins,validate as validate_margins
    from native_triangle_separation_guards import SeparationGuards
    from native_scene_geometry import faces_for,evaluate_to_archive,METHODS as GEOMETRY_METHODS
    from native_scene_norms import rows
    from native_scene_conic import solver_identity
    from native_key_control_support import effective_basis
    from native_uniform_control_increment import parameter_rows
    from native_surface_model import surface_points,geometry_score
    from triangle_crossing import audit
    from convex_partner_surface import penetration
    from strep import read,save,sha256,now
    started=time.monotonic()
    MODEL=Path(checked['source_paths']['model']).parent
    BASE=Path(checked['source_paths']['trial']).parent
    CAL=Path(checked['source_paths']['calibration']).parent
    OUT=Path(checked['output']);REQUEST=MODEL/'job.json'
    prior=checked['source_reports']['model'];baseline=checked['source_reports']['trial']
    calibration=checked['source_reports']['calibration'];bindings=checked['inputs_sha256']
    for name,digest in prior['methods_sha256'].items():
        if sha256(ROOT/'scripts'/name)!=digest:
            raise ValueError('Changed bound derivative source: '+name)
    for name,digest in baseline['methods_sha256'].items():
        if sha256(ROOT/'scripts'/name)!=digest:
            raise ValueError('Changed bound trial source: '+name)
    identity_roles=['job.json','guides.json','witnesses.json','material-system.npz','material-jacobian.npz']
    identity_binding={name:baseline['files_sha256'][name] for name in identity_roles}
    import hashlib
    material_identity=hashlib.sha256(json.dumps(identity_binding,sort_keys=True).encode()).hexdigest()
    if calibration['material_model_binding']!=identity_binding or calibration['material_model_sha256']!=material_identity:
        raise ValueError('Empirical calibration belongs to a different anchor or material model')
    with np.load(CAL/'calibration.npz',allow_pickle=False) as z:
        margin_policy=EmpiricalMaterialMargins(z['margins_m'].copy(),z['actual_gaps_m'].copy(),
            z['affine_gaps_m'].copy(),read(CAL/'policy.json'))
    validate_margins(margin_policy,material_model_sha256=material_identity,required_rows=1710)
    job=Job(REQUEST);x=job.value.copy()
    assert job.request==read(BASE/'job.json') and sha256(REQUEST)==identity_binding['job.json']
    methods={n:sha256(ROOT/'scripts'/n) for n in sorted(set(JOB_METHODS)|set(GEOMETRY_METHODS)|set(prior['methods_sha256'])|{
        'native_component_trajectory_step.py','native_component_trajectory_margin_step.py','native_empirical_material_margins.py',
        'buffered_component_trial_preflight.py','run_buffered_component_trajectory_trial.py',
        'native_material_witness_guides.py','native_triangle_separation_guards.py','native_uniform_control_increment.py','native_key_control_support.py'})}
    if shutil.disk_usage(OUT.parent).free<=checked['required_disk_free_bytes']:
        raise RuntimeError('Storage reserve changed after archive validation; scientific output not created')
    OUT.mkdir();(OUT/'implementation').mkdir();shutil.copyfile(__file__,OUT/'driver.py')
    for n in methods:shutil.copyfile(ROOT/'scripts'/n,OUT/'implementation'/n)
    save(OUT/'job.json',job.request)
    save(OUT/'preflight.json',{k:v for k,v in checked.items() if k!='source_reports'})
    def phase(name,**kw):
        kw.pop('status',None)
        save(OUT/'pipeline.json',dict(status=name if name in ('complete','failed') else 'processing',phase=name,at=now(),**kw));print(name,kw,flush=True)
    with threadpool_limits(limits=1):
      try:
        scene=SceneContacts(read(MODEL/'guide-scene.json'),MODEL)
        centered,decoded,centering=centered_problem(job.problem,x,job.files,scene,read(MODEL/'guide-policy.json'),sha256(MODEL/'guide-scene.json'),source_policy=job.policy)
        native=rows(job.problem,x,decoded);assert np.all(native.residual()<=0) and job.reference_bounds(job.files,decoded)['passed']
        with np.load(MODEL/'native-system.npz',allow_pickle=False) as z:
            for k in ('vectors','caps','scales'):np.testing.assert_array_equal(getattr(native,k),z[k])
            np.testing.assert_array_equal(x,z['controls'])
            np.testing.assert_array_equal(job.problem.times,z['times_s'])
            np.testing.assert_array_equal(job.problem.lower,z['lower']);np.testing.assert_array_equal(job.problem.upper,z['upper'])
        with np.load(MODEL/'anchor.npz',allow_pickle=False) as z:
            base={n:z[n].copy() for n in ('A','B')};full={n:z[n+'_guide'].copy() for n in ('A','B')}
            times=z['guide_times_s'].tolist();all_times=z['times_s'].tolist()
        np.testing.assert_array_equal(job.geometry_times,all_times)
        with np.load(MODEL/'component-system.npz',allow_pickle=False) as z:
            trajectory=ComponentTrajectoryModel(z['gaps_m'].copy(),sparse.load_npz(MODEL/'component-jacobian.npz'),z['clearances_m'].copy(),
                z['weights_s'].copy(),read(MODEL/'component-groups.json'),read(MODEL/'component-coverage.json'))
        nj=sparse.load_npz(MODEL/'native-jacobian.npz');names=['A','B']
        faces={n:faces_for(a['rig'])[0] for n,a in job.scene.actors.items()}
        topology=read(MODEL/'component-topology.json');event=.5000000149011612
        # Reuse only fully replayed material and guard models at this exact anchor.
        guides,witnesses=read(BASE/'guides.json'),read(BASE/'witnesses.json')
        observer=MaterialWitnessGuides(job.problem,guides,allow_duplicate_descriptors=True)
        with np.load(BASE/'material-system.npz',allow_pickle=False) as z:
            points,mg,mc=[z[k].copy() for k in ('points','gaps_m','clearances_m')]
        np.testing.assert_array_equal(mc,observer.clearances)
        actual_points_at_anchor,actual_gaps_at_anchor=observer.observe(decoded)
        np.testing.assert_array_equal(points,actual_points_at_anchor)
        np.testing.assert_array_equal(mg,actual_gaps_at_anchor)
        mj=sparse.load_npz(BASE/'material-jacobian.npz')
        with np.load(BASE/'guard-system.npz',allow_pickle=False) as z:
            guard=SeparationGuards(z['gaps_m'].copy(),sparse.load_npz(BASE/'guard-jacobian.npz'),
                z['clearances_m'].copy(),read(BASE/'guards.json'),read(BASE/'guard-partition.json'))
        assert len(guides)==1710 and mj.shape==(1710,90) and len(guard.gaps_m)==3636
        assert guard.report['complete_triangle_pairs']==571824
        queries=read(BASE/'initial-frame-queries.json')
        save(OUT/'initial-frame-queries.json',queries)
        for name in ('guides.json','witnesses.json','material-system.npz','material-jacobian.npz',
                     'guard-system.npz','guard-jacobian.npz','guard-partition.json','guards.json'):
            shutil.copyfile(BASE/name,OUT/name)
        shutil.copyfile(CAL/'policy.json',OUT/'empirical-policy.json')
        phase('same-pose-replayed-models-loaded',material_rows=len(mg),full_mesh_guard_rows=len(guard.gaps_m))
        event_eq=[]
        for n,actor in job.edits.actors.items():
            for e in actor['tracks']:
                basis=effective_basis(e['clock'],e['ids'],e['weights'],event)
                for c in range(3):
                    row=np.zeros(90);row[e['controls'][:,c]]=basis;event_eq.append(row)
        eqs={'original-norms':None,'event-key-preserved':np.array(event_eq),'uniform-control-increment':parameter_rows(job.edits)[0]}
        with np.load(BASE/'parameter-rows.npz',allow_pickle=False) as z:
            np.testing.assert_array_equal(eqs['event-key-preserved'],z['event'])
            np.testing.assert_array_equal(eqs['uniform-control-increment'],z['uniform'])
        np.savez_compressed(OUT/'parameter-rows.npz',event=eqs['event-key-preserved'],uniform=eqs['uniform-control-increment'])
        save(OUT/'settings.json',dict(guide_times_s=times,component_times_s=all_times,original_solver_settings_unchanged=True,
            source_model=str(MODEL),reused_stencils=180,fresh_stencils=0,material_derivative='Fixed-axis projection of all fresh eleven-frame full-skin point columns',
            comparison_fractions=job.request['settings']['fractions'],positive_component_samples=99,positive_component_rows=6336,
            strict_material_and_legacy_triangle_ceiling=True,scale_m=.005,empirical_proposal_buffer_policy=margin_policy.report))
        inside=np.array([k for k,w in enumerate(witnesses) if w['kind']=='penetrating-vertex'],int)
        tri=np.array([k for k,w in enumerate(witnesses) if w['kind']=='triangle-separation'],int)
        depth=max(0.,float((-mg[inside]).max())) if len(inside) else 0.
        ceiling=max(0.,float((observer.clearances[tri]-mg[tri]).max())) if len(tri) else 0.
        material_lower=np.empty_like(mg);material_lower[inside]=-depth;material_lower[tri]=observer.clearances[tri]-ceiling
        assert depth==baseline['initial_material_depth_ceiling_m'] and ceiling==baseline['initial_legacy_triangle_ceiling_m']
        before=deficits(trajectory,trajectory.gaps_m)['integral_m_s']
        positive_rows=np.concatenate([np.arange(g['first_row'],g['stop_row']) for g in trajectory.groups if g['starts_positive']])
        all_frames=np.searchsorted(job.problem.times,all_times);guide_frames=np.searchsorted(job.problem.times,times)
        def actual_points(worlds):
            cp,fp={},{}
            for n,actor in job.scene.actors.items():
                p,r=actor['placement'];points=[actor['rig'].vertices(worlds[n][f])@r.T+p for f in all_frames]
                cp[n]=np.array([v[topology[n]['vertex_ids']] for v in points]);fp[n]=np.array([points[all_times.index(t)] for t in times])
            return cp,fp
        def query_frame(t,vertices):
            crossing=audit(vertices['A'],faces['A'],vertices['B'],faces['B'],tolerance_m=job.policy['limits']['surface_tolerance_m'])
            depths=[dict(source=a,target=b,**penetration(vertices[a],vertices[b],faces[b],tolerance_m=job.policy['limits']['penetration_m'])) for a,b in (names,names[::-1])]
            return dict(time_s=t,surface=crossing,vertex_containment=depths,maximum_partner_depth_m=max(d['max_depth_m'] for d in depths))
        records=[];solver_records=[]
        for family,eq in eqs.items():
            phase('complete-trajectory-solve',family=family)
            def sink(sample):
                for key in ('quadratic','matrix'):sparse.save_npz(OUT/(family+'-'+key+'.npz'),sample[key])
                np.savez_compressed(OUT/(family+'-vectors.npz'),linear=sample['linear'],rhs=sample['rhs'])
                save(OUT/(family+'-capture.json'),dict(cones=sample['cones']))
            delta,info=direction(native,nj,trajectory,x,job.problem.lower,job.problem.upper,job.request['settings']['trust'],
                separation_guards=guard,material_gaps_m=mg,material_gap_jacobian=mj,material_witnesses=witnesses,
                material_clearances_m=observer.clearances,parameter_rows=eq,scale_m=.005,solver_sink=sink,
                material_margins=margin_policy,material_model_sha256=material_identity)
            item=dict(family=family,identity=solver_identity(),result=info,delta=None if delta is None else delta.tolist())
            save(OUT/(family+'-solver.json'),item);solver_records.append(item)
            phase('complete-trajectory-result',family=family,proposal_status=info['status'],solver_status=info.get('solver_status'))
            if delta is None:continue
            for k,fraction in enumerate(job.request['settings']['fractions']):
                if shutil.disk_usage(OUT).free<=(1<<30)+(3<<20):
                    raise RuntimeError('Storage reserve lost before next actual export; prior outputs retained')
                label=family+f'-fraction-{k:02d}';folder=OUT/label;folder.mkdir();value=x+fraction*delta;step=value-x;files={}
                for n in job.edits.actors:
                    path=folder/(n+'.glb');job.edits.export(n,value,path)
                    assert job.edits.audit(n,path,job.scene.actors[n]['animation_index'],value=value)['passed'];files[n]=path
                scalar,worlds=job.problem.decoded(files,value);actual_native=rows(job.problem,value,worlds);bounds=job.reference_bounds(files,worlds)
                np.testing.assert_array_equal(actual_native.caps,native.caps)
                np.testing.assert_array_equal(actual_native.scales,native.scales)
                smooth=centered.constraints(value,centered.worlds(value,quantized=False));material_points,material_gaps=observer.observe(worlds)
                cp,fp=actual_points(worlds);actual_gaps=observe(trajectory,cp);merit=deficits(trajectory,actual_gaps)
                guard_gaps=np.array([float((fp[d['actors'][0]][times.index(d['time_s']),d['left_vertex']]-fp[d['actors'][1]][times.index(d['time_s']),d['right_vertex']])@np.array(d['axis_world'])) for d in guard.descriptors])
                affine_guard=guard.gaps_m+guard.jacobian@step;affine_component=trajectory.gaps_m+trajectory.jacobian@step
                actual_depth=max(0.,float((-material_gaps[inside]).max())) if len(inside) else 0.
                actual_ceiling=max(0.,float((observer.clearances[tri]-material_gaps[tri]).max())) if len(tri) else 0.
                frame_queries=[query_frame(t,{n:fp[n][i] for n in names}) for i,t in enumerate(times)]
                parameter_error=float(abs(eq@step).max()) if eq is not None else 0.
                affine_material=mg+mj@step
                buffered_excess=float((material_lower+margin_policy.margins_m-affine_material).max())
                record=dict(label=label,family=family,fraction=fraction,maximum_actual_control_step=float(abs(step).max()),
                    parameter_maximum_absolute_residual=parameter_error,parameter_conditions_pass=parameter_error<=1e-9,
                    affine_empirical_material_maximum_excess_m=buffered_excess,affine_empirical_material_conditions_pass=buffered_excess<=0.,
                    original_step_box_pass=bool(np.all(value>=job.problem.lower) and np.all(value<=job.problem.upper) and abs(step).max()<=job.request['settings']['trust']),
                    failed_native_rows=int((scalar>0).sum()),vector_norm_failures=int((actual_native.residual()>0).sum()),
                    failed_contact_rows=int((scalar[job.problem.protected_rows:]>0).sum()),centered_failed_native_rows=int((smooth>0).sum()),
                    native_conditions_pass=bool(np.all(scalar<=0) and np.all(actual_native.residual()<=0)),reference_bounds=bounds,
                    actual_guard_failures=int((guard_gaps<guard.clearances_m).sum()),affine_guard_failures=int((affine_guard<guard.clearances_m).sum()),
                    actual_positive_component_failures=int((actual_gaps[positive_rows]<trajectory.clearances_m[positive_rows]).sum()),
                    affine_positive_component_failures=int((affine_component[positive_rows]<trajectory.clearances_m[positive_rows]).sum()),
                    actual_deficit_integral_m_s=merit['integral_m_s'],actual_deficit_sum_m=merit['sum_m'],actual_worst_component_deficit_m=merit['maximum_m'],
                    actual_integral_improved=merit['integral_m_s']<before,actual_material_depth_m=actual_depth,actual_legacy_triangle_deficit_m=actual_ceiling,
                    actual_material_depth_ceiling_pass=actual_depth<=depth,actual_legacy_triangle_ceiling_pass=actual_ceiling<=ceiling,
                    guide_frame_queries=frame_queries,guide_frame_triangle_records=sum(len(q['surface']['records']) for q in frame_queries),
                    guide_frame_maximum_partner_depth_m=max(q['maximum_partner_depth_m'] for q in frame_queries),
                    anchor_export_hashes_match=all(sha256(files[n])==sha256(job.files[n]) for n in names),
                    full_geometry_assessed=False,retained=False,quality_approved=False,release_approved=False)
                np.savez_compressed(folder/'observations.npz',controls=value,residual=scalar,centered_residual=smooth,
                    vectors=actual_native.vectors,caps=actual_native.caps,scales=actual_native.scales,
                    material_points=material_points,material_gaps_m=material_gaps,affine_material_gaps_m=affine_material,
                    original_material_row_excess_m=material_lower-material_gaps,empirical_affine_material_row_excess_m=material_lower+margin_policy.margins_m-affine_material,
                    actual_guard_gaps_m=guard_gaps,affine_guard_gaps_m=affine_guard,
                    actual_component_gaps_m=actual_gaps,affine_component_gaps_m=affine_component,per_sample_deficits_m=merit['per_sample_m'],
                    **{n+'_worlds':w for n,w in worlds.items()})
                save(folder/'result.json',record);records.append(record)
                phase('actual-complete-trajectory-export',label=label,native_failures=record['failed_native_rows'],
                    guard_failures=record['actual_guard_failures'],clear_component_failures=record['actual_positive_component_failures'],integral=record['actual_deficit_integral_m_s'])
        candidates=[r for r in records if eligible(r)]
        selected=min(candidates,key=lambda r:(r['actual_deficit_integral_m_s'],r['guide_frame_maximum_partner_depth_m'],r['guide_frame_triangle_records'])) if candidates else None
        if selected is not None:
            folder=OUT/selected['label']
            with np.load(folder/'observations.npz',allow_pickle=False) as z:worlds={n:z[n+'_worlds'].copy() for n in names}
            def progress(v):
                if v['completed_samples']%100==0 or v['completed_samples']==v['total_samples']:phase('selected-complete-geometry',**v)
            geometry,_=evaluate_to_archive(job.scene,job.policy,sha256(job.roles['source_scene']),folder/'geometry-observations.npz',progress,actor_vertices=surface_points(job.problem,worlds))
            np.testing.assert_array_equal(geometry['times_s'],job.geometry_times);save(folder/'geometry.json',geometry)
            selected.update(full_geometry_assessed=True,geometry_score=list(geometry_score(geometry)),geometry_conditions_pass=geometry['sampled_conditions_pass']);save(folder/'result.json',selected)
        job.check();assert all(sha256(p)==h for p,h in bindings.items())
        assert all(sha256(ROOT/'scripts'/n)==sha256(OUT/'implementation'/n)==h for n,h in methods.items())
        result=dict(schema='strep-buffered-component-trajectory-trial-v1',status='complete',at=now(),seconds=time.monotonic()-started,
            inputs_sha256=bindings,methods_sha256=methods,driver_sha256=sha256(__file__),
            controls=90,original_norm_rows=30450,native_samples=1707,geometry_samples=1673,
            complete_component_groups=1673,complete_component_rows=107072,positive_component_rows=6336,
            legacy_material_rows=len(guides),full_mesh_guard_rows=len(guard.gaps_m),full_mesh_triangle_pairs=571824,
            reused_complete_stencils=180,fresh_stencils=0,reused_complete_same_pose_material_and_guard_models=True,
            empirical_material_model_sha256=material_identity,empirical_policy_sha256=margin_policy.report['policy_sha256'],
            empirical_policy=copy.deepcopy(margin_policy.report),original_actual_material_ceilings_unchanged=True,
            solver_records=solver_records,records=records,
            initial_deficit_integral_m_s=before,initial_material_depth_ceiling_m=depth,initial_legacy_triangle_ceiling_m=ceiling,
            full_geometry_selection=None if selected is None else selected['label'],
            selection_rule='Changed export passing all original native/reference/trust, actual full-mesh and all99-positive component guards, actual legacy material ceilings and improved actual complete-clock integral; lowest integral then guide depth/record count.',
            original_selected=True,quality_approved=False,release_approved=False,
            files_sha256={str(p.relative_to(OUT)):sha256(p) for p in OUT.rglob('*') if p.is_file() and p.name!='pipeline.json'},
            scope='Empirically buffered distinct complete-clock component solver trial at verified56-choice anchor. All1673 times/107072 ordered pair rows, '
                'all99 clear sample groups/6336 hard rows, original native/control/trust/equalities and separately bounded legacy material ceilings. '
                'Reused complete571824-pair full-mesh affine guard partition at11 times binds verified same-pose full-skin derivatives from prior180 world calls. '
                'All three requested solver families/fractions and actual stored exports retained. Full original scene only for actual eligible changed output. '
                'Empirical endpoint buffers only; no new-pose error guarantee. No storage repair, derivative reuse across poses, source selection, exact nonlinear/between-sample certificate, engine or human approval.')
        save(OUT/'result.json',result);phase('complete',exports=len(records),full_geometry_selection=result['full_geometry_selection'])
        return result
      except BaseException as exc:
        save(OUT/'failure.json',dict(status='failed',at=now(),error=str(exc),traceback=traceback.format_exc()));phase('failed');raise


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request',required=True)
    parser.add_argument('--preflight-only',action='store_true')
    parser.add_argument('--receipt',help='Save a fresh metadata receipt without overwriting a prior one')
    args=parser.parse_args(argv)
    if args.receipt and Path(args.receipt).exists():
        raise ValueError('Receipt exists; retain the previous record')
    result=preflight(args.request) if args.preflight_only else run(args.request)
    if args.receipt:
        with Path(args.receipt).open('x',encoding='utf-8') as stream:
            json.dump(result,stream,indent=2,allow_nan=False)
            stream.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k in ('schema','status','disk_free_bytes',
        'required_disk_free_bytes','scientific_work_started','numerical_validation_complete','quality_approved','release_approved')}))
    return 2 if result['status']=='blocked-insufficient-storage' else 0


if __name__=='__main__':
    raise SystemExit(main())
