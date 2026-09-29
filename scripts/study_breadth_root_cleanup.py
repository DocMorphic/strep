"""Fixed full-population root cleanup after the completed whole-support study."""
import argparse
import ast
import copy
import os
import shutil
from pathlib import Path
import numpy as np
import psutil
from threadpoolctl import threadpool_limits
from strep import ROOT,read,save,sha256,now
from authored_root_correction import POLICY,Problem,export,verify
from verify_authored_root_correction import inspect,samples
from audit_authoring_intent import check_files


def active_frames(annotations,side,frames):
    active=np.zeros(frames,bool)
    for interval in annotations['intervals']:
        if interval['joint'] not in (side+'Foot',side+'ToeBase'):continue
        a,b=interval['start_frame'],interval['end_frame_exclusive']
        if type(a)!=int or type(b)!=int or not 0<=a<b<=frames:raise ValueError('Invalid support interval')
        active[a:b]=True
    return active


class BreadthProblem(Problem):
    def additional_constraints(self,linear,norm,equal):
        guides=read(self.folder/'support.json')['guides'];annotations=read(self.folder/'contacts.json');counts={}
        for side,patch in self.spec['patches'].items():
            ids=patch['vertices']
            points=self.points[::2,ids];track=points.mean(1);height=points[:,:,1].min(1)
            weight=float(self.weights[ids].mean())
            active=active_frames(annotations,side,self.frames);guide=guides[side]
            anchors=np.asarray(guide['anchors_xz_m']);used=np.asarray(guide['weights'])>0
            if anchors.shape!=(self.frames,2) or used.shape!=(self.frames,):raise ValueError('Support guide clock mismatch')
            for f in np.flatnonzero(active):
                # Retain a low vertex as a hover witness. Use actual skin weights,
                # including serialized sums that differ slightly from one.
                vertex=ids[int(points[f,:,1].argmin())]
                linear(self.maps[2*f][1]*self.weights[vertex],max(0.,height[f])-height[f])
            for f in np.flatnonzero(active[1:]&active[:-1])+1:
                v=track[f,[0,2]]-track[f-1,[0,2]]
                norm(v,(self.maps[2*f]-self.maps[2*f-2])[[0,2]]*weight,np.linalg.norm(v))
            for f in np.flatnonzero(used):
                v=track[f,[0,2]]-anchors[f]
                norm(v,self.maps[2*f][[0,2]]*weight,np.linalg.norm(v))
            counts[side]=dict(hover=int(active.sum()),edges=int((active[1:]&active[:-1]).sum()),anchors=int(used.sum()))
        return counts


def support_audit(folder,path):
    """Decode saved GLBs afresh, without solver maps or cached vertices."""
    spec=read(folder/'contact-spec.json');annotations=read(folder/'contacts.json');guides=read(folder/'support.json')['guides']
    tracks=[]
    for asset in [folder/'candidate/character.glb',path]:
        rig,world=samples(asset,spec['frames']);vertices=np.asarray([rig.vertices(w) for w in world[::2]])
        tracks.append({side:vertices[:,patch['vertices']] for side,patch in spec['patches'].items()})
    rows=[]
    for side in spec['patches']:
        a,b=[t[side] for t in tracks];old,new=[p.mean(1)[:,[0,2]] for p in [a,b]]
        mask=active_frames(annotations,side,spec['frames']);steps=mask[1:]&mask[:-1]
        used=np.asarray(guides[side]['weights'])>0;anchors=np.asarray(guides[side]['anchors_xz_m'])
        heights=[np.maximum(0.,p[:,:,1].min(1)) for p in [a,b]]
        speeds=[np.linalg.norm(np.diff(p,axis=0),axis=1)*30 for p in [old,new]]
        errors=[np.linalg.norm(p-anchors,axis=1) for p in [old,new]]
        row=dict(side=side,active_frames=int(mask.sum()),support_steps=int(steps.sum()),draft_frames=int(used.sum()),
            hover_excess_m=float((heights[1]-heights[0])[mask].max()) if mask.any() else 0.,
            speed_excess_m_s=float((speeds[1]-speeds[0])[steps].max()) if steps.any() else 0.,
            anchor_excess_m=float((errors[1]-errors[0])[used].max()) if used.any() else 0.,
            hover_before_m=float(heights[0][mask].max()) if mask.any() else None,
            hover_after_m=float(heights[1][mask].max()) if mask.any() else None,
            speed_before_m_s=float(speeds[0][steps].max()) if steps.any() else None,
            speed_after_m_s=float(speeds[1][steps].max()) if steps.any() else None)
        # Match the existing root audit's metre tolerance and two-endpoint edge allowance.
        row['passed']=row['hover_excess_m']<=1e-6 and row['speed_excess_m_s']<=60e-6 and row['anchor_excess_m']<=1e-6
        rows.append(row)
    return dict(rows=rows,passed=all(r['passed'] for r in rows),source_sha256=sha256(folder/'candidate/character.glb'),candidate_sha256=sha256(path),quality_approved=False)


def snapshot(output):
    dest=output/'implementation';dest.mkdir();pending=[Path(__file__).name];seen=set()
    while pending:
        name=pending.pop()
        if name in seen:continue
        seen.add(name);path=ROOT/'scripts'/name;shutil.copyfile(path,dest/name)
        for node in ast.walk(ast.parse(path.read_text(encoding='utf-8-sig'))):
            modules=[node.module] if isinstance(node,ast.ImportFrom) else [a.name for a in node.names] if isinstance(node,ast.Import) else []
            for module in modules:
                child=(module or '').split('.')[0]+'.py'
                if (ROOT/'scripts'/child).is_file():pending.append(child)
    return {n:sha256(dest/n) for n in sorted(seen)}


def prepare(study,output):
    if output.exists():raise ValueError('Preserve existing study')
    protocol=read(study/'protocol.json');results=read(study/'results.json')
    if read(study/'pipeline.json')['status']!='complete' or read(study/'completion.json')['results_sha256']!=sha256(study/'results.json'):raise ValueError('Completed source study required')
    if read(study/'freeze.json')['protocol_sha256']!=sha256(study/'protocol.json'):raise ValueError('Source protocol changed')
    if len(protocol['cases'])!=24 or [c['id'] for c in protocol['cases']]!=[r['id'] for r in results['rows']]:raise ValueError('Require full ordered 24-case population')
    if any(r['status']!='complete' for r in results['rows']):raise ValueError('Source population incomplete')
    output.mkdir(parents=True);cases=[]
    for case,row in zip(protocol['cases'],results['rows']):
        origin=study/'takes'/case['id'];folder=output/'takes'/case['id'];folder.mkdir(parents=True)
        proof=read(origin/'verification.json')
        if sha256(origin/'verification.json')!=row['verification_sha256'] or not proof['bounds_and_preservation_passed']:raise ValueError('Source proof changed')
        for variant,key in [('input','source_sha256'),('candidate','candidate_sha256')]:
            if sha256(origin/variant/'character.glb')!=proof[key]:raise ValueError('Source export changed')
            (folder/variant).mkdir();shutil.copyfile(origin/variant/'character.glb',folder/variant/'character.glb')
        shutil.copyfile(origin/'spec.json',folder/'contact-spec.json');shutil.copyfile(origin/'input/contacts.json',folder/'contacts.json')
        save(folder/'support.json',read(origin/'request.json')['support'])
        spec=read(folder/'contact-spec.json')
        if spec['contacts'] or spec['glb_sha256']!=proof['source_sha256']:raise ValueError('Unexpected source contact schema')
        save(folder/'result.json',dict(frames=spec['frames'],fps=spec['fps'],root_node=spec['root_node']))
        files={p.relative_to(folder).as_posix():sha256(p) for p in folder.rglob('*') if p.is_file()}
        cases.append(dict(id=case['id'],family=case['motion']['family'],action=case['motion']['case'],rig=case['rig'],seed=case['motion']['seed'],frames=spec['frames'],source='input',candidate='candidate',files=files,
            original_root_peak_m_s2=proof['metrics']['input']['root_acceleration_max_m_s2'],prior_root_peak_m_s2=proof['metrics']['candidate']['root_acceleration_max_m_s2']))
    policy=copy.deepcopy(POLICY);policy['minimum_relative_energy_improvement']=.001
    resources=[ROOT/'reports/conic-solver-bootstrap-v1.json',ROOT/'.cache/godot/4.7.2-stable/Godot_v4.7.2-stable_win64_console.exe']
    save(output/'request.json',dict(at=now(),source=str(study),source_protocol_sha256=sha256(study/'protocol.json'),source_results_sha256=sha256(study/'results.json'),cases=cases,policy=policy,
        resources={str(p):sha256(p) for p in resources},
        implementation=snapshot(output),selection='All 24 completed whole-support cases in unchanged order, eight actions and three rigs, seed1301; development only.',
        scope='Root translation cleanup with unchanged rotations, original edit limits, floor and whole-clip foot acceleration guards; additionally preserve predicted support hover, horizontal speed and drafted anchors. No action/scene/partner/quality approval.'))
    save(output/'freeze.json',dict(request_sha256=sha256(output/'request.json')))
    save(output/'results.json',dict(rows=[dict(id=c['id'],status='pending') for c in cases],quality_approved=False))
    save(output/'pipeline.json',dict(status='prepared',at=now()))


def run(output):
    from action_worker_lock import worker_lock
    from run_godot_rig_import import run as import_engine
    request=read(output/'request.json')
    if read(output/'freeze.json')['request_sha256']!=sha256(output/'request.json'):raise ValueError('Frozen request changed')
    if read(output/'pipeline.json')['status']!='prepared':raise ValueError('Inspect existing attempt before any recovery')
    check_files(ROOT/'scripts',request['implementation']);check_files(output/'implementation',request['implementation'])
    for path,digest in request['resources'].items():
        if sha256(path)!=digest:raise ValueError('Frozen resource changed')
    save(output/'worker.json',dict(pid=os.getpid(),created_at=psutil.Process().create_time()))
    results=read(output/'results.json');engine=[]
    with worker_lock(),threadpool_limits(limits=1):
        for case,row in zip(request['cases'],results['rows']):
            folder=output/'takes'/case['id'];save(output/'pipeline.json',dict(status='processing',case=case['id'],at=now()));row['status']='running';save(output/'results.json',results)
            try:
                problem=BreadthProblem(folder,case,request['policy']);offsets,solver=problem.propose();save(folder/'solver.json',solver);attempts=[];selected=folder/'candidate/character.glb'
                row['status']='no_solver_proposal' if offsets is None else 'no_accepted_candidate'
                if offsets is not None:
                    np.save(folder/'offsets.npy',offsets)
                    for fraction in request['policy']['fractions']:
                        path=folder/('proposal-'+str(fraction)+'.glb');export(problem.rig,problem.root,offsets*fraction,path)
                        check=verify(problem,path);audit=inspect(problem.source,path,folder/'input/character.glb',folder/'contact-spec.json',case['frames'],request['policy']);support=support_audit(folder,path)
                        passed=check['all_preservation_checks_passed'] and check['objective_improved'] and audit['all_checks_passed'] and support['passed']
                        attempts.append(dict(fraction=fraction,verification=check,independent=audit,support=support,accepted=passed));save(folder/'attempts.json',attempts)
                        if passed:selected=path;row['status']='candidate_preserved';break
                row.update(selected=str(selected),selected_sha256=sha256(selected),solver_status=solver['status'],attempts=len(attempts))
                if attempts:row['last_audit']=attempts[-1]
                engine.append(dict(id=case['id'],path=str(selected),sha256=sha256(selected),frames=case['frames'],fps=30,sample_by_time=True))
                del problem
            except Exception as exc:
                row.update(status='failed',error=str(exc))
            save(output/'results.json',results);print(case['id'],row['status'],flush=True)
        save(output/'manifest.json',dict(cases=engine));save(output/'pipeline.json',dict(status='engine_validation',at=now()))
        import_engine(output,output/'engine')
        proof=read(output/'engine/verification.json')
        if [c['id'] for c in proof['checks']]!=[c['id'] for c in engine]:raise ValueError('Engine population mismatch')
        for actual,expected in zip(proof['checks'],engine):
            if actual['frames']!=expected['frames'] or actual['source_sha256']!=expected['sha256']:raise ValueError('Engine source/clock mismatch')
        for case in request['cases']:check_files(output/'takes'/case['id'],case['files'])
        check_files(ROOT/'scripts',request['implementation'])
        save(output/'completion.json',dict(at=now(),request_sha256=sha256(output/'request.json'),results_sha256=sha256(output/'results.json'),engine_sha256=sha256(output/'engine/verification.json'),
            selected_candidates=sum(r['status']=='candidate_preserved' for r in results['rows']),failed=sum(r['status']=='failed' for r in results['rows']),engine_actor_frames=sum(c['frames'] for c in engine),quality_approved=False))
        save(output/'pipeline.json',dict(status='complete_with_failures' if any(r['status']=='failed' for r in results['rows']) else 'complete',at=now(),quality_approved=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['prepare','run']);parser.add_argument('output',type=Path);parser.add_argument('--source',type=Path);args=parser.parse_args()
    if args.command=='prepare':prepare(args.source.resolve(),args.output.resolve())
    else:
        try:run(args.output.resolve())
        except Exception as exc:
            save(args.output/'failure.json',dict(at=now(),error=str(exc),quality_approved=False));raise
