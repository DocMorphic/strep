"""Immutable Studio jobs for contact-target-preserving root dynamics cleanup."""
import argparse
import ast
import copy
import os
from pathlib import Path
import shutil
import zipfile
import hashlib
import numpy as np
import psutil
from scipy.spatial.transform import Rotation
from threadpoolctl import threadpool_limits
from strep import ROOT, read, save, sha256, now
from rig_contact_authoring import source
from authored_root_correction import POLICY, Problem, export, verify, load_motion
from verify_authored_root_correction import inspect as independent_inspect
from audit_authoring_intent import check_files
from joint_root_correction import JointProblem
from verify_joint_root_correction import inspect as joint_inspect


def validate(payload):
    fields = {'schema', 'job', 'variant', 'glb_sha256', 'label'}
    if not isinstance(payload, dict) or set(payload) != fields or payload['schema'] != 'strep-rig-dynamics-v1':
        raise ValueError('Choose a source clip, version and correction name')
    if not isinstance(payload['label'], str) or not 1 <= len(payload['label'].strip()) <= 160:
        raise ValueError('Name the corrected clip')
    snapshot = source(payload['job'], payload['variant'])
    folder, result, request, report, glb = snapshot
    if sha256(glb) != payload['glb_sha256']:
        raise ValueError('Selected clip changed')
    if report['fps'] != 30 or not 3 <= report['frames'] <= 900:
        raise ValueError('Root cleanup requires a 30fps clip of at most 900 frames')
    if result['kind'] == 'contact_edit' and payload['variant'] == 'corrected':
        baseline, recipe = folder/'transfer/character.glb', folder/'contact-spec.json'
        if sha256(recipe) != request['authored_spec_sha256'] or sha256(baseline) != request['input_glb_sha256']:
            raise ValueError('Original contact recipe or root reference changed')
        history = dict(source_job=folder.name, status=result.get('correction_status', 'unverified'),
                       source_glb_sha256=sha256(glb), result_sha256=sha256(folder/'result.json'))
    elif result['kind'] == 'joint_edit' and payload['variant'] == 'transfer':
        check_files(folder, request['input_files'])
        baseline, recipe = folder/'input/character.glb', folder/'joint-spec.json'
        if sha256(baseline) != request['input_glb_sha256']:
            raise ValueError('Original joint edit reference changed')
        history = dict(kind='joint_edit', source_job=folder.name, status=result.get('joint_edit_status','unverified'),
            source_glb_sha256=sha256(glb), result_sha256=sha256(folder/'result.json'))
    elif result['kind'] == 'dynamics_edit' and payload['variant'] in ('input', 'transfer'):
        if read(folder/'freeze.json')['request_sha256'] != sha256(folder/'request.json'):
            raise ValueError('Saved correction request changed')
        baseline, recipe = folder/'baseline/character.glb', folder/'original-contact-spec.json'
        for path in (baseline, recipe):
            if sha256(path) != request['files'][path.relative_to(folder).as_posix()]:
                raise ValueError('Saved original correction context changed')
        history = copy.deepcopy(request['inherited_contact'])
        if history.get('kind') == 'joint_edit':
            check_files(folder, {n:request['files'][n] for n in ('joint-spec.json','joint-targets.json','joint-edit.json')})
    else:
        raise ValueError('Select a corrected mesh-contact edit, joint-edit candidate or previous root-cleanup result. Finger-only edits keep their fixed body context.')
    spec = read(recipe)
    if spec['glb_sha256'] != sha256(baseline) or (spec['frames'], spec['fps'], spec['root_node']) != (report['frames'], report['fps'], report['root_node']):
        raise ValueError('Contact targets do not match the original root reference')
    timeline = glb.parent/'timeline.json'
    if timeline.exists() and 'period_frames' in read(timeline):
        raise ValueError('Clean up a finite clip before constructing its loop')
    return snapshot, baseline, recipe, history


def implementation_snapshot(folder):
    dest = folder/'implementation'
    dest.mkdir()
    pending, seen = [Path(__file__).name], set()
    while pending:
        name = pending.pop()
        if name in seen:
            continue
        seen.add(name)
        path = ROOT/'scripts'/name
        shutil.copyfile(path, dest/name)
        for node in ast.walk(ast.parse(path.read_text(encoding='utf-8-sig'))):
            modules = ([node.module] if isinstance(node, ast.ImportFrom) else
                       [a.name for a in node.names] if isinstance(node, ast.Import) else [])
            for module in modules:
                child = (module or '').split('.')[0]+'.py'
                if (ROOT/'scripts'/child).exists():
                    pending.append(child)
    return {n: sha256(dest/n) for n in sorted(seen)}


def prepare(payload, folder):
    (previous, result, original, report, glb), baseline, recipe, history = validate(payload)
    folder = Path(folder)
    folder.mkdir(exist_ok=False)
    shutil.copytree(previous/'source', folder/'source', ignore=shutil.ignore_patterns('implementation'))
    (folder/'input').mkdir()
    (folder/'baseline').mkdir()
    shutil.copyfile(glb, folder/'input/character.glb')
    shutil.copyfile(baseline, folder/'baseline/character.glb')
    shutil.copyfile(recipe, folder/'original-contact-spec.json')
    if history.get('kind') == 'joint_edit':
        for name in ('joint-spec.json','joint-targets.json','joint-edit.json'):
            shutil.copyfile(previous/name,folder/name)
        if result['kind'] == 'joint_edit':
            spec=read(recipe)
            for i,support in enumerate(read(folder/'joint-targets.json')['supports']):
                name='joint-support-'+str(i)
                if name in spec['patches']:raise ValueError('Support name collision')
                spec['patches'][name]=dict(vertices=support['vertices'])
                spec['contacts'].append(dict(patch=name,start_frame=support['start_frame'],
                    end_frame_exclusive=support['end_frame_exclusive'],target_position_m=support['target_position_m']))
            save(folder/'original-contact-spec.json',spec)
    for name in ('contacts.json', 'events.json', 'timeline.json', 'inventory.json', 'rig-profile.json', 'contact-review.json'):
        path = glb.parent/name
        if not path.exists():
            path = previous/'transfer'/name
        if path.exists():
            shutil.copyfile(path, folder/'input'/name)
    native = 'character.glb' if report.get('source_kind') == 'gltf_animation' else 'motion.npz'
    report.update(source=str((folder/'source'/native).resolve()), character=str((folder/'source/character.glb').resolve()))
    if report.get('timeline_edited'):
        report['contact_annotations_file'] = str((folder/'input/contacts.json').resolve())
    save(folder/'input/report.json', report)
    rebound = read(folder/'original-contact-spec.json')
    rebound['glb_sha256'] = sha256(glb)
    save(folder/'input/contact-spec.json', rebound)
    save(folder/'dynamics-edit.json', payload)
    # Explicit internal clip inventory for the generic solver; no provisional
    # result.json is exposed to Studio before the job actually finishes.
    save(folder/'solver-input.json', dict(frames=report['frames'], fps=report['fps'], root_node=report['root_node']))
    if sha256(folder/'input/character.glb') != payload['glb_sha256'] or sha256(folder/'source/character.glb') != original['asset_id'] or sha256(folder/'source/rig-profile.json') != original['profile_id']:
        raise ValueError('Source changed while preparing the correction')
    implementation = implementation_snapshot(folder)
    files = {p.relative_to(folder).as_posix(): sha256(p) for p in folder.rglob('*') if p.is_file() and 'implementation' not in p.parts}
    request = dict(kind='dynamics_edit', label=payload['label'].strip(), asset_id=original['asset_id'],
        profile_id=sha256(folder/'source/rig-profile.json'), source_kind=report.get('source_kind', 'soma_motion'),
        source_motion_sha256=sha256(folder/'source'/native), input_glb_sha256=sha256(glb),
        source_job=previous.name, input_variant=payload['variant'], policy=copy.deepcopy(POLICY),
        inherited_contact=history, files=files, implementation=implementation, correct_contacts=False)
    # A UI operation should exceed a small relative floor, not report a
    # float32-sized change as useful cleanup. Prior frozen jobs keep their policy.
    request['policy']['minimum_relative_energy_improvement']=.001
    save(folder/'request.json', request)
    save(folder/'freeze.json', dict(request_sha256=sha256(folder/'request.json')))
    save(folder/'pipeline.json', dict(status='starting', stage='Root cleanup inputs saved'))
    return request


def solver_workspace(folder):
    # Private solver inventory is never exposed as a completed Studio job.
    work = folder/'solver'
    work.mkdir()
    for name, origin in [('input', 'input'), ('baseline', 'baseline')]:
        (work/name).mkdir()
        shutil.copyfile(folder/origin/'character.glb', work/name/'character.glb')
    shutil.copyfile(folder/'original-contact-spec.json', work/'contact-spec.json')
    save(work/'result.json', read(folder/'solver-input.json'))
    for name in ('joint-spec.json','joint-targets.json','joint-edit.json'):
        if (folder/name).exists():shutil.copyfile(folder/name,work/name)
    files = {p.relative_to(work).as_posix(): sha256(p) for p in work.rglob('*') if p.is_file()}
    return work, dict(source='baseline', candidate='input', files=files)


class StudioProblem(Problem):
    def __init__(self,folder,request):
        work,case=solver_workspace(folder)
        super().__init__(work,case,request['policy'])


class StudioJointProblem(JointProblem):
    def __init__(self,folder,request):
        work,case=solver_workspace(folder)
        super().__init__(work,case,request['policy'])


def variant_files(folder, name, path, report, source_report, source_input):
    dest = folder/name
    dest.mkdir(exist_ok=True)
    if path.resolve() != (dest/'character.glb').resolve():
        shutil.copyfile(path, dest/'character.glb')
    for sidecar in ('contacts.json', 'events.json', 'timeline.json', 'inventory.json', 'rig-profile.json', 'contact-review.json'):
        if (source_input/sidecar).exists() and source_input != dest:
            shutil.copyfile(source_input/sidecar, dest/sidecar)
    rig, world = load_motion(dest/'character.glb', report['frames'])
    integer = world[::2]
    root = report['root_node']
    save(dest/'root-motion.json', dict(node=root, space='Mapped pelvis world transform in metres; engine root extraction not applied',
        times_s=(np.arange(len(integer), dtype=np.float32)/30).tolist(), positions_m=integer[:, root, :3, 3].tolist(),
        rotations_xyzw=Rotation.from_matrix(integer[:, root, :3, :3]).as_quat().tolist()))
    if name == 'input':
        return source_report  # Preserve the frozen selected-input report and recipe.
    kept = ('character','character_sha256','source','source_sha256','source_kind','profile_sha256','frames','fps',
            'last_key_time_s','sample_coverage_s','root_node','mapping','timeline_edited')
    current = {k: source_report[k] for k in kept if k in source_report}
    current.update(glb_sha256=sha256(dest/'character.glb'), edit_parent_glb_sha256=sha256(source_input/'character.glb'),
        target_mesh_floor_depth_max_m=max(max(0., -float(rig.vertices(w)[:, 1].min())) for w in integer),
        human_approved=False, engine_import=None, animation_name='Root dynamics cleanup',
        limitations=['Target-preserving root translation only; source failures and unconfirmed contact/event annotations remain.'])
    if current.get('timeline_edited'):
        current['contact_annotations_file'] = str((dest/'contacts.json').resolve())
    save(dest/'report.json', current)
    spec = read(folder/'original-contact-spec.json')
    spec['glb_sha256'] = current['glb_sha256']
    save(dest/'contact-spec.json', spec)
    return current


def run(folder):
    folder = Path(folder).resolve()
    request = read(folder/'request.json')
    if read(folder/'freeze.json')['request_sha256'] != sha256(folder/'request.json'):
        raise ValueError('Frozen correction request changed')
    from action_worker_lock import worker_lock
    save(folder/'worker.json', dict(pid=os.getpid(), created_at=psutil.Process().create_time()))
    try:
        with worker_lock(), threadpool_limits(limits=1):
            check_files(folder, request['files'])
            check_files(ROOT/'scripts', request['implementation'])
            check_files(folder/'implementation', request['implementation'])
            save(folder/'pipeline.json', dict(status='processing', stage='Reducing root acceleration while preserving targets'))
            joint=request['inherited_contact'].get('kind')=='joint_edit'
            problem = (StudioJointProblem if joint else StudioProblem)(folder, request)
            offsets, solver = problem.propose()
            save(folder/'solver/proposal.json', solver)
            attempts, selected = [], folder/'input/character.glb'
            if offsets is not None:
                np.save(folder/'solver/proposed-offsets.npy', offsets)
                for fraction in request['policy']['fractions']:
                    path = folder/'solver'/('candidate-'+str(fraction)+'.glb')
                    export(problem.rig, problem.root, offsets*fraction, path)
                    candidate = verify(problem, path)
                    independent = independent_inspect(problem.source, path, folder/'baseline/character.glb',
                        folder/'original-contact-spec.json', problem.frames, request['policy'])
                    if joint:
                        independent=joint_inspect(folder/'solver',path,request['policy'],
                            source=folder/'input/character.glb',original=folder/'baseline/character.glb')
                    accepted = candidate['all_preservation_checks_passed'] and candidate['objective_improved'] and independent['all_checks_passed']
                    name = path.stem+'-audit.json'
                    save(folder/'solver'/name, dict(candidate=candidate, independent=independent, accepted=accepted))
                    attempts.append(dict(fraction=fraction, glb=path.name, audit=name, accepted=accepted))
                    if accepted:
                        selected = path
                        break
            check_files(folder, request['files'])
            improved = selected.parent.name == 'solver'
            audit = dict(at=now(), input_sha256=request['input_glb_sha256'], selected_sha256=sha256(selected),
                status='improved' if improved else 'input_retained', attempts=attempts, solver=solver,
                policy=request['policy'], inherited_contact=request['inherited_contact'], human_approved=False,
                scope='Root acceleration energy improvement and declared patch/target/root/channel guards. No semantic, physical, continuous collision or human approval.')
            source_report = read(folder/'input/report.json')
            input_report = variant_files(folder, 'input', folder/'input/character.glb', source_report, source_report, folder/'input')
            report = variant_files(folder, 'transfer', selected, source_report, source_report, folder/'input')
            shutil.copyfile(folder/'transfer/contact-spec.json', folder/'contact-spec.json')
            save(folder/'dynamics-audit.json', audit)
            base = '/files/rig-jobs/'+folder.name+'/'
            historical = request['inherited_contact']['status']
            failed = historical in ('rejected', 'infeasible', 'unsupported')
            review_status = 'rejected' if failed else 'unverified'
            variants = {}
            for key, label, meta in [('input','Before root cleanup', input_report),('transfer','Root cleanup candidate' if improved else 'Unchanged input', report)]:
                variants[key] = dict(label=label, glb=base+key+'/character.glb', sha256=meta['glb_sha256'],
                    root_track=base+key+'/root-motion.json', report=base+key+'/report.json', contacts=base+key+'/contacts.json',
                    contact_spec=base+key+'/contact-spec.json', source_variant='corrected')
            result = dict(kind='dynamics_edit', label=request['label'], frames=report['frames'], fps=30, root_node=report['root_node'],
                variants=variants, dynamics_status=audit['status'], dynamics_audit=base+'dynamics-audit.json',
                dynamics_recipe=base+'dynamics-edit.json', correction_status=review_status,
                inherited_correction=dict(status=review_status, source_job=request['source_job'], source_variant=request['input_variant']),
                historical_contact=request['inherited_contact'], source_kind=request['source_kind'], source_character_sha256=request['asset_id'],
                source_motion_sha256=request['source_motion_sha256'], profile=base+'source/rig-profile.json', report=base+'transfer/report.json',
                root_track=base+'transfer/root-motion.json', contacts=base+'transfer/contacts.json', contact_spec=base+'contact-spec.json',
                floor_depth_m=report['target_mesh_floor_depth_max_m'], human_approved=False, engine_import=None,
                note=('Root acceleration energy reduced; target and patch-dynamics checks retained. ' if improved else 'No verified improvement; selected input retained. ')+
                    ('Earlier contact checks failed and remain unresolved. ' if failed else 'Earlier contact results are retained as history. ')+
                    'Root translation only; action, contacts and naturalness need review.')
            if joint:
                result['authored_kind']='joint_edit'
                result['note']=result['note'].replace('Earlier contact','Earlier joint-edit')
                result['joint_targets']=base+'joint-targets.json'
                result['joint_recipe']=base+'joint-edit.json'
            if (folder/'transfer/events.json').exists():
                result['events'] = base+'transfer/events.json'
            package = folder/'character-animation.zip'
            members = {p.relative_to(folder).as_posix(): sha256(p) for p in folder.rglob('*') if p.is_file() and p.name not in ('pipeline.json','worker.json','supervisor.log')}
            with zipfile.ZipFile(package, 'w', zipfile.ZIP_DEFLATED) as archive:
                for name in sorted(members):
                    archive.write(folder/name, name)
            with zipfile.ZipFile(package) as archive:
                if {n: hashlib.sha256(archive.read(n)).hexdigest() for n in archive.namelist()} != members:
                    raise ValueError('Correction package differs from recorded files')
            result.update(package=base+'character-animation.zip', package_sha256=sha256(package))
            save(folder/'result.json', result)
            save(folder/'pipeline.json', dict(status='complete', finished_at=now(), stage='Root cleanup ready for comparison'))
    except Exception as error:
        save(folder/'pipeline.json', dict(status='failed', error=str(error), finished_at=now()))
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path)
    run(parser.parse_args().folder)
