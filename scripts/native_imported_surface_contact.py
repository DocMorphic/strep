"""Replay authored surface normals/side conditions on bound imported skin.

Uses actual headless producer observations, including reloaded object resources.
No engine is executed here; source winding supplies the canonical orientation.
"""
import argparse
import json
from pathlib import Path
import shutil
import numpy as np
from threadpoolctl import threadpool_limits
from action_worker_lock import worker_lock
from native_object_scene_engine import load as object_load, METHODS as ENGINE_METHODS, require
from verify_native_actor_scene_engine import load as actor_load
from native_surface_contact import evaluate as surface_evaluate, policy_for, METHODS as SURFACE_METHODS
from native_scene_contacts import fields
from strep import ROOT,read,save,sha256,now

METHODS = tuple(dict.fromkeys(ENGINE_METHODS+SURFACE_METHODS+(
    'verify_native_actor_scene_engine.py','verify_native_object_scene_engine.py','native_imported_surface_contact.py')))
SCHEMA = 'strep-native-imported-surface-contact-v1'
FILES = ('result.json','pipeline.json','request.json','observations.npz')
SCOPE = ('Complete authored contact clocks, winding-derived incident-face normals and explicit target '
         'normals on raw imported CPU skin and saved object-resource poses. Canonical source topology '
         'after checked imported correspondence; no anatomical/outward-volume, force, physics, GPU, '
         'real-time playback, collision, native-rate-cap or human-quality approval.')


class ImportedContactScene:
    """Make point and full-surface observations use the same imported trajectory."""
    def __init__(self,scene,actor,objects):
        require(actor.scene is scene and objects.scene is scene,'Imported observations must use the exact scene instance')
        self.scene,self.actor,self.objects = scene,actor,objects

    def __getattr__(self,name):
        return getattr(self.scene,name)

    def evaluate(self):
        return self.scene.evaluate(actor_points=self.actor.actor_points,object_poses=self.objects.object_poses)


def evaluate(scene,policy,digest,actor,providers):
    """Preserve native results and separately audit every declared imported mode."""
    policy_for(policy,scene,digest)
    expected = {'default-import','native-authoring'} if scene.objects else {'native-authoring'}
    require(isinstance(providers,dict) and set(providers) == expected,'Complete explicit imported object modes required')
    reports = {}; arrays = {}
    native,data = surface_evaluate(scene,policy,digest)
    reports['source-native'] = native
    arrays.update({'source-native_'+k:v for k,v in data.items()})
    for mode in ('default-import','native-authoring'):
        if mode not in providers: continue
        provider = providers[mode]
        wrapped = ImportedContactScene(scene,actor,provider)
        report,data = surface_evaluate(wrapped,policy,digest,actor_vertices=actor.actor_vertices,
                                       object_poses=provider.object_poses)
        report.update(imported_observations_checked=True,raw_imported_weights_renormalized=False,
            canonical_source_winding_used=True,object_pose_mode=mode if scene.objects else None,
            actor_pose_mode='native-authoring',real_time_playback_verified=False)
        reports[mode] = report; arrays.update({mode+'_'+k:v for k,v in data.items()})
    counts = {}
    for mode,report in reports.items():
        points = [p for c in report['contacts'] for sample in c['samples'] for p in sample['points']]
        counts[mode] = dict(contact_samples=sum(len(c['samples']) for c in report['contacts']),points=len(points),
            unavailable_normals=sum(not (p['source_normal']['available'] and p['target_normal']['available']) for p in points),
            failed_orientation_or_side_points=sum(not p['passed'] for p in points),
            point_contacts_pass=report['point_contacts_pass'],surface_contacts_pass=report['surface_contacts_pass'])
    return dict(schema=SCHEMA,status='complete',reports=reports,counts=counts,
        native_and_imported_surface_contacts_pass=bool(reports['source-native']['surface_contacts_pass']
            and reports['native-authoring']['surface_contacts_pass']),
        default_comparison_preserved=bool(scene.objects),original_selected=True,
        anatomical_review_pending=True,engine_executed=False,geometry_queries_rerun=False,
        collision_verified=False,native_rate_caps_checked=False,real_time_playback_verified=False,
        gpu_render_checked=False,human_reviewed=False,quality_approved=False,training_admitted=False,
        release_approved=False,scope=SCOPE),arrays


def load(contacts,geometry_policy,actor_dir,object_dir):
    spec = read(contacts)
    if spec['objects']:
        require(object_dir is not None,'Declared objects require the actual object producer')
        scene,_,actor,providers,times,bindings = object_load(contacts,geometry_policy,actor_dir,object_dir)
    else:
        require(object_dir is None,'Actor-only audit cannot invent an object producer')
        scene,_,actor,times,bindings = actor_load(contacts,geometry_policy,actor_dir)
        providers = {'native-authoring':actor}
    return scene,actor,providers,times,bindings


def run(contacts,surface_policy,geometry_policy,actor_dir,output,*,object_dir=None):
    contacts,surface_policy,geometry_policy,actor_dir,output = [Path(p).resolve() for p in (
        contacts,surface_policy,geometry_policy,actor_dir,output)]
    object_dir = None if object_dir is None else Path(object_dir).resolve()
    require(not output.exists(),'Fresh imported surface audit output required')
    with worker_lock(),threadpool_limits(limits=1):
        scene,actor,providers,times,bindings = load(contacts,geometry_policy,actor_dir,object_dir)
        bindings[str(surface_policy)] = sha256(surface_policy); bindings.update(scene.inputs)
        policy = read(surface_policy); policy_for(policy,scene,bindings[str(contacts)])
        require(not any(Path(p).is_relative_to(output) for p in bindings),'Output cannot contain its own source input')
        methods = {n:sha256(ROOT/'scripts'/n) for n in METHODS}
        output.mkdir(parents=True); archive = output/'implementation'; archive.mkdir()
        save(output/'pipeline.json',dict(at=now(),status='processing',stage='imported-surface-contacts'))
        try:
            for n in methods: shutil.copyfile(ROOT/'scripts'/n,archive/n)
            snapshots = {}
            for i,(path,h) in enumerate(bindings.items()):
                dest = output/'input'/f'{i}{Path(path).suffix}'; dest.parent.mkdir(exist_ok=True); shutil.copyfile(path,dest)
                require(sha256(dest) == h,'Surface input snapshot changed')
                snapshots[path] = dict(path=dest.relative_to(output).as_posix(),sha256=h)
            request = dict(at=now(),schema=SCHEMA,contacts=str(contacts),surface_policy=str(surface_policy),
                geometry_policy=str(geometry_policy),actor_dir=str(actor_dir),object_dir=None if object_dir is None else str(object_dir),
                inputs_sha256=bindings,source_snapshots=snapshots,implementation_sha256=methods,
                engine_observation_times_s=times.tolist())
            save(output/'request.json',request)
            result,arrays = evaluate(scene,policy,bindings[str(contacts)],actor,providers)
            np.savez_compressed(output/'observations.npz',**arrays)
            scene.check_inputs()
            load(contacts,geometry_policy,actor_dir,object_dir)  # Recheck every producer resource/receipt after measurement.
            for path,h in bindings.items():
                require(sha256(path) == sha256(output/snapshots[path]['path']) == h,'Imported surface source changed')
            for n,h in methods.items(): require(sha256(ROOT/'scripts'/n) == sha256(archive/n) == h,'Imported surface method changed')
            result.update(request_sha256=sha256(output/'request.json'),observations_sha256=sha256(output/'observations.npz'))
            save(output/'result.json',result); save(output/'pipeline.json',dict(at=now(),status='complete',original_selected=True))
            return result
        except Exception as exc:
            save(output/'pipeline.json',dict(at=now(),status='failed',error=str(exc),original_selected=True)); raise


def verify(folder):
    """Reconstruct all surface/contact observations; never repeat geometry queries."""
    folder = Path(folder).resolve()
    with worker_lock(),threadpool_limits(limits=1):
        before = {n:sha256(folder/n) for n in FILES}
        require(read(folder/'pipeline.json')['status'] == 'complete','Complete surface audit required')
        request,result = read(folder/'request.json'),read(folder/'result.json')
        fields(request,('at','schema','contacts','surface_policy','geometry_policy','actor_dir','object_dir',
                        'inputs_sha256','source_snapshots','implementation_sha256','engine_observation_times_s'),
               'imported surface request')
        require(request['schema'] == SCHEMA and result['request_sha256'] == sha256(folder/'request.json'),
                'Bound complete imported surface request required')
        require(set(request['implementation_sha256']) == set(METHODS),'Complete surface implementation required')
        for n,h in request['implementation_sha256'].items():
            require(sha256(ROOT/'scripts'/n) == sha256(folder/'implementation'/n) == h,'Archived imported surface method changed')
        for path,h in request['inputs_sha256'].items():
            snap = request['source_snapshots'][path]; saved = (folder/snap['path']).resolve()
            require(saved.is_relative_to(folder) and sha256(saved) == snap['sha256'] == sha256(path) == h,'Surface source/snapshot changed')
        require(set(request['source_snapshots']) == set(request['inputs_sha256']),'Complete imported surface snapshots required')
        contacts,policy,geometry,actors = [Path(request[n]).resolve() for n in ('contacts','surface_policy','geometry_policy','actor_dir')]
        objects = None if request['object_dir'] is None else Path(request['object_dir']).resolve()
        scene,actor,providers,times,bindings = load(contacts,geometry,actors,objects)
        bindings[str(policy)] = sha256(policy); bindings.update(scene.inputs)
        require(bindings == request['inputs_sha256'] and times.tolist() == request['engine_observation_times_s'],
                'Complete original imported surface bindings/clock required')
        rebuilt,arrays = evaluate(scene,read(policy),sha256(contacts),actor,providers)
        require(sha256(folder/'observations.npz') == result['observations_sha256'],'Surface observation archive changed')
        with np.load(folder/'observations.npz',allow_pickle=False) as saved:
            require(set(saved.files) == set(arrays),'Complete surface observation population required')
            for n,value in arrays.items():
                require(saved[n].dtype == value.dtype and saved[n].shape == value.shape
                        and saved[n].tobytes() == value.tobytes(),'Replayed imported surface array differs: '+n)
        rebuilt.update(request_sha256=sha256(folder/'request.json'),observations_sha256=sha256(folder/'observations.npz'))
        require(json.dumps(rebuilt,sort_keys=True,allow_nan=False) == json.dumps(result,sort_keys=True,allow_nan=False),
                'Replayed complete imported surface result differs')
        scene.check_inputs(); load(contacts,geometry,actors,objects)
        for path,h in request['inputs_sha256'].items():
            require(sha256(path) == sha256(folder/request['source_snapshots'][path]['path']) == h,
                    'Surface source/snapshot changed during replay')
        for n,h in request['implementation_sha256'].items():
            require(sha256(ROOT/'scripts'/n) == sha256(folder/'implementation'/n) == h,'Surface replay method changed')
        require({n:sha256(folder/n) for n in FILES} == before,'Surface evidence changed during replay')
        return dict(schema='strep-native-imported-surface-contact-replay-v1',status='complete',
            result_sha256=sha256(folder/'result.json'),complete_normals_points_and_decisions_recomputed=True,
            counts=result['counts'],geometry_queries_rerun=False,engine_executed=False,
            shared_surface_kernel=True,quality_approved=False,release_approved=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); sub = parser.add_subparsers(dest='command',required=True)
    audit = sub.add_parser('audit')
    for n in ('contacts','surface_policy','geometry_policy','actor_dir','output'): audit.add_argument(n,type=Path)
    audit.add_argument('--object-dir',type=Path)
    replay = sub.add_parser('verify'); replay.add_argument('folder',type=Path)
    args = parser.parse_args()
    if args.command == 'audit': run(args.contacts,args.surface_policy,args.geometry_policy,args.actor_dir,args.output,object_dir=args.object_dir)
    else: print(verify(args.folder))
