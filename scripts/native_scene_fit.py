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
    'native_scene_norms.py','native_scene_conic.py',
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

    def worlds(self, value):
        return {n:self.edits.worlds(n,value,self.times) if n in self.edits.actors else w
            for n,w in self.source_world.items()}

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


def run(contacts_path,permissions_path,output,*,iterations=4,trust=.02,proposal_model='scalar',vector_difference_step=None):
    if type(iterations) is not int or not 1<=iterations<=16: raise ValueError('Choose 1-16 proposal iterations')
    if proposal_model not in ('scalar','vector'):raise ValueError('Choose scalar or vector proposal model')
    if proposal_model=='scalar' and vector_difference_step is not None:raise ValueError('Vector difference step applies only to vector proposals')
    if proposal_model=='vector':vector_difference_step = scalar(.001 if vector_difference_step is None else vector_difference_step,1e-6,.01,'vector difference step')
    conic_identity = None
    if proposal_model=='vector':
        from native_scene_conic import solver_identity
        conic_identity = solver_identity()
    trust = scalar(trust,.000001,.02,'normalized control trust')
    contacts_path,permissions_path,output = map(lambda p:Path(p).resolve(),(contacts_path,permissions_path,output))
    if output.exists(): raise ValueError('Fresh native scene fitting directory required')
    bindings = {str(p):sha256(p) for p in (contacts_path,permissions_path)}
    spec = read(contacts_path); scene = SceneContacts(spec,contacts_path.parent)
    edits = SceneEdits(read(permissions_path),scene,sha256(contacts_path)); bindings.update(scene.inputs)
    methods = {n:sha256(ROOT/'scripts'/n) for n in METHODS}
    with worker_lock(),threadpool_limits(limits=1):
        output.mkdir(parents=True); archive = output/'implementation'; archive.mkdir()
        for n in methods: shutil.copyfile(ROOT/'scripts'/n,archive/n)
        shutil.copyfile(contacts_path,output/'contacts.json'); shutil.copyfile(permissions_path,output/'permissions.json')
        snapshots = {output/'contacts.json':bindings[str(contacts_path)],output/'permissions.json':bindings[str(permissions_path)]}
        if any(sha256(p)!=h for p,h in snapshots.items()): raise ValueError('Authored request snapshot differs')
        originals = {}
        for i,(name,a) in enumerate(spec['actors'].items()):
            dest = output/'input'/f'actor-{i}.glb'; dest.parent.mkdir(exist_ok=True)
            path = (contacts_path.parent/a['glb']).resolve(); shutil.copyfile(path,dest)
            if sha256(dest)!=a['sha256']: raise ValueError('Native scene input snapshot differs')
            originals[name] = dest
        save(output/'request.json',dict(at=now(),inputs_sha256=bindings,implementation_sha256=methods,
            contacts_source_path=str(contacts_path),permissions_source_path=str(permissions_path),
            actor_snapshots={n:dict(path=p.relative_to(output).as_posix(),sha256=spec['actors'][n]['sha256']) for n,p in originals.items()},
            controls=edits.size,iterations=iterations,trust_control_fraction=trust,
            proposal_model=proposal_model,conic_solver=conic_identity,
            vector_difference_step=vector_difference_step,
            frame_contract_sha256=contract_sha256(),python=sys.version,numpy=np.__version__,scipy=scipy.__version__,
            quality_approved=False,scope='Proposal only; originals selected pending scene geometry and actual imported-skin checks.'))
        save(output/'pipeline.json',dict(status='processing')); probes = []
        try:
            problem = SceneProblem(scene,edits)
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
                record = dict(label=label,controls=value.tolist(),merit=list(merit(residual)),
                    files_sha256={p.relative_to(output).as_posix():sha256(p) for p in files.values()})
                save(folder/'probe.json',record); probes.append(record); return residual
            if proposal_model=='vector':
                from native_scene_conic import optimize as optimize_vectors
                value,optimization = optimize_vectors(problem,evaluate,iterations,trust,difference_step=vector_difference_step)
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
            for p,h in bindings.items():
                if sha256(p)!=h: raise ValueError('Native scene fitting input changed')
            for n,h in methods.items():
                if sha256(ROOT/'scripts'/n)!=h or sha256(archive/n)!=h: raise ValueError('Native scene fitting method changed')
            for n,p in originals.items():
                if sha256(p)!=spec['actors'][n]['sha256']: raise ValueError('Native scene input snapshot changed')
            if any(sha256(p)!=h for p,h in snapshots.items()): raise ValueError('Authored request snapshot changed')
            if conic_identity is not None and solver_identity()!=conic_identity:raise ValueError('Installed vector proposal solver changed')
            result = dict(status='complete',optimization=optimization,probes=probes,edits=audits,
                native_constraints_pass=bool(merit(final_constraints)[0]==0 and report['passed'] and all(a['passed'] for a in audits.values())),
                source_rate_tolerance=1e-5,source_rate_bins=4,source_rate_caps_sha256=sha256(output/'source-rate-caps.npz'),
                proposal_model=proposal_model,conic_solver=conic_identity,
                vector_difference_step=vector_difference_step,
                original_selected=True,selected_files={n:p.relative_to(output).as_posix() for n,p in originals.items()},
                proposal_files={n:str(Path(a['glb']).relative_to(output)) for n,a in proposal_spec['actors'].items()},
                contacts_result_sha256=sha256(output/'contact-audit/result.json'),
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
    p.add_argument('--proposal-model',choices=['scalar','vector'],default='scalar')
    p.add_argument('--vector-difference-step',type=float)
    a=p.parse_args(); run(a.contacts,a.permissions,a.output,iterations=a.iterations,trust=a.trust,
        proposal_model=a.proposal_model,vector_difference_step=a.vector_difference_step)
