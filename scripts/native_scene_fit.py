"""Bounded native scene proposals, retaining originals pending scene/engine review."""
import argparse
import copy
from pathlib import Path
import shutil
import sys
import numpy as np
import scipy
from scipy.spatial.transform import Rotation
from native_scene_contacts import SceneContacts, METHODS as CONTACT_METHODS, scalar
from native_scene_edit import SceneEdits
from native_support_clock import NativeSupportSampler
from rig_asset import RigAsset
from sampled_motion_caps import features, measures, SampledMotionCaps
from native_support_feasibility import colors, colored_jacobian, direction, merit
from engine_contact_sampling import frame_populations, contract_sha256
from action_worker_lock import worker_lock
from threadpoolctl import threadpool_limits
from strep import ROOT, read, save, sha256, now

METHODS = sorted(set(CONTACT_METHODS) | {'native_scene_edit.py','native_scene_fit.py',
    'native_scene_norms.py','native_scene_conic.py','native_scene_storage.py','native_scene_restore.py','native_scene_resume.py','native_scene_geometry.py',
    'native_surface_model.py','native_partner_surface_rows.py','native_surface_lift.py',
    'native_surface_contact.py','native_contact_norms.py',
    'triangle_primitive_depth.py','triangle_crossing.py','convex_partner_surface.py',
    'timed_rotation_edit.py','sampled_motion_caps.py','native_support_feasibility.py','action_worker_lock.py',
    'native_foot_plant.py','native_leg_floor.py','native_support_spec.py','native_contact_diagnostics.py',
    'native_leg_smoothing.py','elbow_swivel.py','two_bone_waypoint.py','contact_rate_path.py',
    'contact_locked_native.py','absolute_rate_peaks.py','native_engine_clock.py',
    'native_support_orientation.py','native_support_path.py','native_support_peak_limits.py',
    'native_support_rates.py','native_support_swivel.py'})


class SceneProblem:
    def __init__(self, scene, edits):
        self.scene = scene; self.edits = edits; self.size = edits.size
        if self.size > 96: raise ValueError('This local proposal solver supports at most 96 control components')
        self.initial,self.lower,self.upper = edits.initial,edits.lower,edits.upper
        self.uniform = np.arange(int(np.floor(scene.duration*120))+1)/120
        if len(self.uniform)<3: raise ValueError('At least three uniform source-rate samples required')
        native = [c[2] for a in scene.actors.values() for c in a['sampler'].channels] + [o['times'] for o in scene.objects.values()]
        all_times = [self.uniform] + native; self.rows = []
        for entry in scene.rows:
            row = entry['authored']; a,b = row['interval_s']
            populations = frame_populations([a,b]) if row['mode']=='hold' else []
            clock = np.unique(np.concatenate([np.array([a,b])] + native + [p['times_s'] for p in populations]))
            clock = clock[(clock>=a)&(clock<=b)]; all_times.append(clock)
            self.rows.append(dict(entry=entry,times=clock,populations=populations))
        self.times = np.unique(np.concatenate(all_times)); self.rate_ids = np.searchsorted(self.times,self.uniform)
        self.source_world = {n:np.array([a['sampler'].sample(float(t)) for t in self.times]) for n,a in scene.actors.items()}
        self.caps = {}
        for n in edits.actors:
            actor = scene.actors[n]
            self.caps[n] = SampledMotionCaps(features(self.source_world[n][self.rate_ids],actor['rig'].joints),
                self.uniform,np.linspace(0,scene.duration,5),tolerance=1e-5)
        for r in self.rows:
            row = r['entry']['authored']; target = row['target']; r['ids'] = np.searchsorted(self.times,r['times'])
            if target['space']=='object': r['object_pose'] = scene.object_poses(target['object'],r['times'])

    def worlds(self, value, *, quantized=True):
        return {n:self.edits.worlds(n,value,self.times,quantized=quantized) if n in self.edits.actors else w
            for n,w in self.source_world.items()}

    @property
    def protected_rows(self):
        """All edit, displacement and source-rate rows preceding contacts."""
        return sum(sum(len(e['ids']) for e in a['tracks'])
            +len(self.uniform)*len(self.scene.actors[n]['rig'].joints)
            +sum(c.size for c in self.caps[n].caps) for n,a in self.edits.actors.items())

    def skin_points(self, name, ids, worlds, times, reduction):
        actor = self.scene.actors[name]; skin = actor['skin']; w = worlds[name][times]
        points = np.einsum('fvkij,vkj,vk->fvi',w[:,skin.nodes[ids],:3,:],skin.points[ids],skin.weights[ids])
        p,r = actor['placement']; points = points @ r.T + p
        return points.mean(axis=1,keepdims=True) if reduction=='centroid' else points

    def constraints(self, value, worlds=None):
        value = self.edits.controls(value); worlds = self.worlds(value) if worlds is None else worlds; result = []
        for n,a in self.edits.actors.items():
            # Control vectors impose cumulative source-relative native-key bounds.
            for entry in a['tracks']:
                delta = entry['weights'] @ value[entry['controls']]
                result.append(np.linalg.norm(delta,axis=1)-1)
            joints = self.scene.actors[n]['rig'].joints; old = self.source_world[n][self.rate_ids]
            current = worlds[n][self.rate_ids]
            d = np.linalg.norm(current[:,joints,:3,3]-old[:,joints,:3,3],axis=2)
            result.append(((d-a['displacement'])/a['displacement']).ravel())
            cap = self.caps[n]
            for v,c in zip(measures(features(current,joints),cap.dt),cap.caps):
                result.append(((v-c-cap.tolerance)/np.maximum(c,.001)).ravel())
        for data in self.rows:
            entry = data['entry']; row = entry['authored']; target = row['target']; space = target['space']; ids = data['ids']
            effector = self.skin_points(row['actor'],entry['ids'],worlds,ids,row['reduction'])
            if space=='actor': goal = self.skin_points(target['actor'],entry['target_ids'],worlds,ids,target['reduction'])
            elif space=='world': goal = np.repeat(entry['target_ids'][None],len(ids),axis=0)
            else:
                p,r = data['object_pose']; goal = np.einsum('fij,vj->fvi',r,entry['target_ids'])+p[:,None]
            error = effector-goal
            if space=='object': error = np.einsum('fvi,fij->fvj',error,r)
            limit = row['limits']['position_m']
            result.append(((np.linalg.norm(error,axis=2)-limit)/max(limit,.0001)).ravel())
            for pop in data['populations']:
                clock = pop['times_s']; sample_ids = np.searchsorted(data['times'],clock)
                if len(clock)<2: result.append(np.array([1.])); continue
                limit = row['limits']['relative_speed_m_s']
                speed = np.linalg.norm(np.diff(error[sample_ids],axis=0),axis=2)*pop['rate_hz']
                result.append(((speed-limit)/max(limit,.001)).ravel())
        return np.concatenate(result)

    def model(self,value): return self.constraints(value)

    def decoded(self, files, value):
        worlds = dict(self.source_world)
        for name,path in files.items():
            rig = RigAsset.load(path); actor = self.scene.actors[name]
            sampler = NativeSupportSampler(rig.document,rig.binary,actor['animation_index'])
            worlds[name] = np.array([sampler.sample(float(t)) for t in self.times])
        return self.constraints(value,worlds),worlds


def optimize(problem,evaluate,iterations,trust):
    x = problem.initial.copy(); current = evaluate(x,'start'); history = []; radius = trust
    # Conservative dense dependencies; no derivative coloring omissions.
    pattern = np.ones((len(current),problem.size),bool); groups = colors(pattern)
    for iteration in range(1,iterations+1):
        before = merit(current)
        if before[0]==0: break
        jac = colored_jacobian(problem.model,x,problem.lower,problem.upper,pattern,groups,step=1e-5)
        delta,info = direction(x,current,jac,problem.lower,problem.upper,radius); accepted = None; probes = []
        info['trust_control_fraction'] = info.pop('trust_radians')
        if delta is not None:
            for backoff in range(10):
                fraction = .5**backoff; z = np.clip(x+fraction*delta,problem.lower,problem.upper)
                g = evaluate(z,f'{iteration}-{backoff}'); score = merit(g)
                passed = score[0]<before[0]-1e-12 or abs(score[0]-before[0])<=1e-12 and score[1]<before[1]-1e-15
                probes.append(dict(fraction=fraction,merit=list(score),accepted=bool(passed)))
                if passed: x=z; current=g; accepted=fraction; break
        history.append(dict(iteration=iteration,before=list(before),after=list(merit(current)),selected_fraction=accepted,
            probes=probes,linear_step=info))
        print(history[-1]['iteration'],history[-1]['after'],flush=True)
        if accepted is None:
            radius *= .25
            if radius<1e-8: break
    return x,dict(history=history,maximum_iterations=iterations,trust_control_fraction=trust,
        final_merit=list(merit(current)),difference_step_control_fraction=1e-5,conservative_dense_dependencies=True)


def run(contacts_path,permissions_path,output,*,iterations=4,trust=.02,proposal_model='scalar',vector_difference_step=None,storage_cells=None,restoration_steps=0,
        geometry_policy=None,resume_from=None,surface_contact_policy=None):
    if type(iterations) is not int or not 1<=iterations<=16: raise ValueError('Choose 1-16 proposal iterations')
    if proposal_model not in ('scalar','vector','storage-vector','surface-vector'):raise ValueError('Choose scalar, vector, storage-vector or surface-vector proposal model')
    if proposal_model=='scalar' and vector_difference_step is not None:raise ValueError('Vector difference step applies only to vector proposals')
    if proposal_model!='storage-vector' and storage_cells is not None:raise ValueError('Storage cells apply only to storage-vector proposals')
    if type(restoration_steps) is not int or not 0<=restoration_steps<=4:raise ValueError('Choose 0-4 decoded restoration steps')
    if proposal_model not in ('storage-vector','surface-vector') and restoration_steps:raise ValueError('Decoded restoration applies only to storage/surface-vector proposals')
    if proposal_model=='surface-vector' and geometry_policy is None:raise ValueError('Surface proposals require an explicit bound geometry policy')
    if proposal_model=='storage-vector':
        storage_cells=64 if storage_cells is None else storage_cells
        if type(storage_cells) is not int or not 1<=storage_cells<=512:raise ValueError('Choose 1-512 storage cells')
    if proposal_model in ('vector','storage-vector','surface-vector'):vector_difference_step = scalar(.001 if vector_difference_step is None else vector_difference_step,1e-6,.01,'vector difference step')
    conic_identity = None
    if proposal_model in ('vector','storage-vector','surface-vector'):
        from native_scene_conic import solver_identity
        conic_identity = solver_identity()
    trust = scalar(trust,.000001,.02,'normalized control trust')
    contacts_path,permissions_path,output = map(lambda p:Path(p).resolve(),(contacts_path,permissions_path,output))
    if output.exists(): raise ValueError('Fresh native scene fitting directory required')
    bindings = {str(p):sha256(p) for p in (contacts_path,permissions_path)}
    spec = read(contacts_path); scene = SceneContacts(spec,contacts_path.parent)
    edits = SceneEdits(read(permissions_path),scene,sha256(contacts_path)); bindings.update(scene.inputs)
    source_bindings=dict(bindings);resume=None
    if resume_from is not None:
        from native_scene_resume import ResumeState
        resume=ResumeState(resume_from,bindings[str(contacts_path)],bindings[str(permissions_path)],edits)
        edits.initial=resume.controls.copy();bindings.update(resume.bindings)
    surface_request=None
    if surface_contact_policy is not None:
        from native_surface_contact import policy_for as surface_policy_for
        surface_contact_policy=Path(surface_contact_policy).resolve();bindings[str(surface_contact_policy)]=sha256(surface_contact_policy)
        surface_request=read(surface_contact_policy);surface_policy_for(surface_request,scene,bindings[str(contacts_path)])
    if resume is not None and resume.surface_contact_policy_sha256 is not None:
        if surface_contact_policy is None or bindings[str(surface_contact_policy)]!=resume.surface_contact_policy_sha256:
            raise ValueError('Resume must retain its exact additional surface contact policy')
    geometry_request = None
    if geometry_policy is not None:
        from native_scene_geometry import policy_for
        geometry_policy = Path(geometry_policy).resolve(); bindings[str(geometry_policy)] = sha256(geometry_policy)
        geometry_request = read(geometry_policy); policy_for(geometry_request,scene,bindings[str(contacts_path)])
    methods = {n:sha256(ROOT/'scripts'/n) for n in METHODS}
    with worker_lock(),threadpool_limits(limits=1):
        output.mkdir(parents=True); archive = output/'implementation'; archive.mkdir()
        for n in methods: shutil.copyfile(ROOT/'scripts'/n,archive/n)
        resume_receipt=None if resume is None else resume.snapshot(output/'resume')
        shutil.copyfile(contacts_path,output/'contacts.json'); shutil.copyfile(permissions_path,output/'permissions.json')
        snapshots = {output/'contacts.json':bindings[str(contacts_path)],output/'permissions.json':bindings[str(permissions_path)]}
        if geometry_request is not None:
            shutil.copyfile(geometry_policy,output/'geometry-policy.json')
            snapshots[output/'geometry-policy.json'] = bindings[str(geometry_policy)]
        if surface_request is not None:
            shutil.copyfile(surface_contact_policy,output/'surface-contact-policy.json')
            snapshots[output/'surface-contact-policy.json']=bindings[str(surface_contact_policy)]
        if any(sha256(p)!=h for p,h in snapshots.items()): raise ValueError('Authored request snapshot differs')
        originals = {}
        for i,(name,a) in enumerate(spec['actors'].items()):
            dest = output/'input'/f'actor-{i}.glb'; dest.parent.mkdir(exist_ok=True)
            path = (contacts_path.parent/a['glb']).resolve(); shutil.copyfile(path,dest)
            if sha256(dest)!=a['sha256']: raise ValueError('Native scene input snapshot differs')
            originals[name] = dest
        save(output/'request.json',dict(at=now(),inputs_sha256=bindings,source_inputs_sha256=source_bindings,resume=resume_receipt,implementation_sha256=methods,
            contacts_source_path=str(contacts_path),permissions_source_path=str(permissions_path),
            actor_snapshots={n:dict(path=p.relative_to(output).as_posix(),sha256=spec['actors'][n]['sha256']) for n,p in originals.items()},
            controls=edits.size,iterations=iterations,trust_control_fraction=trust,
            proposal_model=proposal_model,conic_solver=conic_identity,
            vector_difference_step=vector_difference_step,
            storage_cells=storage_cells,
            restoration_steps=restoration_steps,
            geometry_policy_sha256=None if geometry_request is None else bindings[str(geometry_policy)],
            surface_contact_policy_sha256=None if surface_request is None else bindings[str(surface_contact_policy)],
            frame_contract_sha256=contract_sha256(),python=sys.version,numpy=np.__version__,scipy=scipy.__version__,
            quality_approved=False,scope='Proposal only; originals selected pending scene geometry and actual imported-skin checks.'))
        save(output/'pipeline.json',dict(status='processing')); probes = []
        try:
            problem = SceneProblem(scene,edits)
            if proposal_model=='surface-vector':
                from native_surface_model import include_times
                if scene.objects:raise ValueError('Surface proposals do not yet include object primitives')
                include_times(problem,policy_for(geometry_request,scene,bindings[str(contacts_path)])[0])
            if resume is not None:resume.check_caps(problem,contract_sha256())
            caps = {}
            for name,c in problem.caps.items():
                for i,v in enumerate(c.caps): caps[f'{name}_metric_{i}'] = v
            np.savez(output/'source-rate-caps.npz',times_s=problem.uniform,**caps)
            def evaluate(value,label):
                folder = output/'probes'/label; folder.mkdir(parents=True)
                files = {}
                for name in edits.actors:
                    path = folder/(name+'.glb'); edits.export(name,value,path); files[name]=path
                    audit = edits.audit(name,path,scene.actors[name]['animation_index'])
                    if not audit['passed']: raise ValueError('Probe exceeds explicit native edit bounds')
                residual,_ = problem.decoded(files,value)
                if label=='start' and resume is not None:resume.check_start(files,residual,problem.protected_rows)
                record = dict(label=label,controls=value.tolist(),merit=list(merit(residual)),
                    files_sha256={p.relative_to(output).as_posix():sha256(p) for p in files.values()})
                save(folder/'probe.json',record); probes.append(record); return residual
            contact_model=None
            if proposal_model=='surface-vector' and surface_request is not None:
                from native_contact_norms import ContactNorms
                contact_model=ContactNorms(problem,surface_request,bindings[str(contacts_path)])
            def evaluate_surface(value,label):
                residual=evaluate(value,label);folder=output/'probes'/label
                files={name:folder/(name+'.glb') for name in edits.actors}
                _,worlds=problem.decoded(files,value)
                derived_spec=copy.deepcopy(spec)
                for name in scene.actors:
                    path=files.get(name,originals[name]);derived_spec['actors'][name]['glb']=str(path)
                    derived_spec['actors'][name]['sha256']=sha256(path)
                save(folder/'contacts.json',derived_spec);digest=sha256(folder/'contacts.json')
                decoded_scene=SceneContacts(derived_spec,folder)
                derived_policy=copy.deepcopy(geometry_request);derived_policy['contacts_sha256']=digest
                save(folder/'policy.json',derived_policy)
                from native_scene_geometry import evaluate as geometry_audit
                geometry,arrays=geometry_audit(decoded_scene,derived_policy,digest)
                save(folder/'geometry.json',geometry);np.savez_compressed(folder/'geometry-observations.npz',**arrays)
                surface_observation=None
                if contact_model is not None:
                    from native_surface_contact import evaluate as surface_audit
                    surface_policy=copy.deepcopy(surface_request);surface_policy['contacts_sha256']=digest
                    surface_observation,surface_arrays=surface_audit(decoded_scene,surface_policy,digest)
                    save(folder/'surface-contact-policy.json',surface_policy);save(folder/'surface-contact.json',surface_observation)
                    np.savez_compressed(folder/'surface-contact-observations.npz',**surface_arrays)
                return dict(native=residual,worlds=worlds,scene=decoded_scene,policy=derived_policy,digest=digest,geometry=geometry,surface_contact=surface_observation)
            if proposal_model=='surface-vector':
                from native_surface_model import optimize as optimize_surfaces
                value,optimization=optimize_surfaces(problem,evaluate_surface,iterations,trust,
                    step=vector_difference_step,restoration_steps=restoration_steps,contact_model=contact_model)
            elif proposal_model in ('vector','storage-vector'):
                from native_scene_conic import optimize as optimize_vectors
                value,optimization = optimize_vectors(problem,evaluate,iterations,trust,difference_step=vector_difference_step,
                    difference_source='continuous' if proposal_model=='storage-vector' else 'stored',
                    storage_cells=storage_cells or 0,protect_source_rows=proposal_model=='storage-vector',restoration_steps=restoration_steps)
            else:value,optimization = optimize(problem,evaluate,iterations,trust)
            final_constraints = evaluate(value,'final'); proposal_spec = copy.deepcopy(spec); proposal = output/'proposal'; proposal.mkdir()
            for i,name in enumerate(spec['actors']):
                src = output/'probes/final'/(name+'.glb') if name in edits.actors else originals[name]
                dest = proposal/f'actor-{i}.glb'; shutil.copyfile(src,dest)
                proposal_spec['actors'][name]['glb']=str(dest); proposal_spec['actors'][name]['sha256']=sha256(dest)
            save(proposal/'contacts.json',proposal_spec)
            from native_scene_contacts import run as contact_audit
            report = contact_audit(proposal/'contacts.json',output/'contact-audit')
            audits = {n:edits.audit(n,Path(proposal_spec['actors'][n]['glb']),scene.actors[n]['animation_index']) for n in edits.actors}
            geometry_report = None
            if geometry_request is not None:
                from native_scene_geometry import evaluate as geometry_audit
                geometry_folder = output/'geometry-audit'; geometry_folder.mkdir()
                derived = copy.deepcopy(geometry_request)
                derived['contacts_sha256'] = sha256(proposal/'contacts.json')
                save(geometry_folder/'policy.json',derived)
                policy_digest = sha256(geometry_folder/'policy.json')
                decoded_scene = SceneContacts(proposal_spec,proposal)
                geometry_report,geometry_arrays = geometry_audit(decoded_scene,derived,derived['contacts_sha256'])
                decoded_scene.check_inputs()
                if sha256(geometry_folder/'policy.json') != policy_digest: raise ValueError('Derived geometry policy changed')
                if sha256(proposal/'contacts.json') != derived['contacts_sha256']: raise ValueError('Proposal scene changed during geometry audit')
                np.savez_compressed(geometry_folder/'observations.npz',**geometry_arrays)
                geometry_report.update(authored_policy_sha256=bindings[str(geometry_policy)],
                    derived_policy_sha256=policy_digest,contacts_sha256=derived['contacts_sha256'],
                    observations_sha256=sha256(geometry_folder/'observations.npz'),implementation_sha256=methods)
                save(geometry_folder/'result.json',geometry_report)
            surface_report=None
            if surface_request is not None:
                from native_surface_contact import evaluate as surface_audit
                surface_folder=output/'surface-contact-audit';surface_folder.mkdir()
                derived=copy.deepcopy(surface_request);derived['contacts_sha256']=sha256(proposal/'contacts.json')
                save(surface_folder/'policy.json',derived)
                surface_report,arrays=surface_audit(SceneContacts(proposal_spec,proposal),derived,derived['contacts_sha256'])
                np.savez_compressed(surface_folder/'observations.npz',**arrays)
                surface_report.update(authored_policy_sha256=bindings[str(surface_contact_policy)],derived_policy_sha256=sha256(surface_folder/'policy.json'),
                    implementation_sha256=methods,observations_sha256=sha256(surface_folder/'observations.npz'))
                save(surface_folder/'result.json',surface_report)
            for p,h in bindings.items():
                if sha256(p)!=h: raise ValueError('Native scene fitting input changed')
            for n,h in methods.items():
                if sha256(ROOT/'scripts'/n)!=h or sha256(archive/n)!=h: raise ValueError('Native scene fitting method changed')
            for n,p in originals.items():
                if sha256(p)!=spec['actors'][n]['sha256']: raise ValueError('Native scene input snapshot changed')
            if resume is not None:
                resume.check_inputs()
                for relative,h in resume_receipt['files_sha256'].items():
                    if sha256(output/'resume'/relative)!=h:raise ValueError('Resume archived snapshot changed')
            if any(sha256(p)!=h for p,h in snapshots.items()): raise ValueError('Authored request snapshot changed')
            if conic_identity is not None and solver_identity()!=conic_identity:raise ValueError('Installed vector proposal solver changed')
            result = dict(status='complete',optimization=optimization,probes=probes,edits=audits,
                resume=resume_receipt,completed_primary_iterations=len(optimization['history'])+(0 if resume is None else resume.prior_iterations),
                point_and_motion_constraints_pass=bool(merit(final_constraints)[0]==0 and report['passed'] and all(a['passed'] for a in audits.values())),
                native_constraints_pass=bool(merit(final_constraints)[0]==0 and report['passed'] and all(a['passed'] for a in audits.values())
                    and (surface_report is None or surface_report['surface_contacts_pass'])),
                surface_contact_conditions_pass=None if surface_report is None else surface_report['surface_contacts_pass'],
                surface_contact_result_sha256=None if surface_report is None else sha256(output/'surface-contact-audit/result.json'),
                source_rate_tolerance=1e-5,source_rate_bins=4,source_rate_caps_sha256=sha256(output/'source-rate-caps.npz'),
                proposal_model=proposal_model,conic_solver=conic_identity,
                vector_difference_step=vector_difference_step,
                storage_cells=storage_cells,
                restoration_steps=restoration_steps,
                original_selected=True,selected_files={n:p.relative_to(output).as_posix() for n,p in originals.items()},
                proposal_files={n:str(Path(a['glb']).relative_to(output)) for n,a in proposal_spec['actors'].items()},
                contacts_result_sha256=sha256(output/'contact-audit/result.json'),
                sampled_geometry_conditions_pass=None if geometry_report is None else geometry_report['sampled_conditions_pass'],
                geometry_result_sha256=None if geometry_report is None else sha256(output/'geometry-audit/result.json'),
                engine_playback_verified=False,collision_verified=False,actual_soma_npz_verified=False,
                quality_approved=False,training_admitted=False,release_approved=False)
            save(output/'result.json',result); save(output/'pipeline.json',dict(status='complete',original_selected=True))
            return result
        except Exception as exc:
            save(output/'pipeline.json',dict(status='failed',error=str(exc),original_selected=True)); raise


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('contacts',type=Path); p.add_argument('permissions',type=Path); p.add_argument('output',type=Path)
    p.add_argument('--iterations',type=int,default=4); p.add_argument('--trust',type=float,default=.02)
    p.add_argument('--proposal-model',choices=['scalar','vector','storage-vector','surface-vector'],default='scalar')
    p.add_argument('--vector-difference-step',type=float)
    p.add_argument('--storage-cells',type=int,help='Finite translation cell probes per iteration, storage-vector only')
    p.add_argument('--restoration-steps',type=int,default=0,help='0-4 decoded constraint restoration solves, storage/surface-vector only')
    p.add_argument('--geometry-policy',type=Path,help='Source-bound sampled scene policy; originals remain selected')
    p.add_argument('--resume-from',type=Path,help='Completed fit to replay against the exact original source and limits')
    p.add_argument('--surface-contact-policy',type=Path,help='Surface-facing acceptance audit and surface-vector proposal guidance')
    a=p.parse_args(); run(a.contacts,a.permissions,a.output,iterations=a.iterations,trust=a.trust,
        proposal_model=a.proposal_model,vector_difference_step=a.vector_difference_step,storage_cells=a.storage_cells,restoration_steps=a.restoration_steps,geometry_policy=a.geometry_policy,resume_from=a.resume_from,surface_contact_policy=a.surface_contact_policy)
