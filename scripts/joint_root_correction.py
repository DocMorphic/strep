"""Window- and target-preserving root cleanup for completed authored joint edits."""
import argparse
import copy
from pathlib import Path
import shutil
import numpy as np
from threadpoolctl import threadpool_limits
from strep import ROOT, read, save, sha256, now
from authored_root_correction import Problem, POLICY, affected_nodes, serialized_cap, export, verify
from audit_authoring_intent import check_files
from verify_joint_root_correction import inspect


class JointProblem(Problem):
    def __init__(self, folder, case, policy):
        super().__init__(folder, case, policy)
        self.targets = read(folder/'joint-targets.json')
        self.envelope = np.asarray(self.targets['envelope'])
        if self.envelope.shape != (self.frames,) or not np.isfinite(self.envelope).all() or np.any((self.envelope < 0)|(self.envelope > 1)):
            raise ValueError('Invalid joint edit envelope')
        self.affected = set(affected_nodes(self.rig.parents, self.root))

    def additional_constraints(self, linear, norm, equal):
        limits, eps = self.spec['limits'], self.policy['position_tolerance_m']
        edits = self.root_positions-self.original_root
        fixed = 0
        for f, weight in enumerate(self.envelope):
            m = self.maps[2*f]
            if weight == 0:
                equal(m, np.zeros(3))
                fixed += 1
            horizontal = serialized_cap(weight*limits['root_horizontal_m'], float(np.linalg.norm(edits[f,[0,2]])), eps)
            vertical = serialized_cap(weight*limits['root_vertical_m'], float(abs(edits[f,1])), eps)
            norm(edits[f,[0,2]], m[[0,2]], horizontal)
            linear(m[1], vertical-edits[f,1])
            linear(-m[1], vertical+edits[f,1])
        for f in range(1,self.frames):
            # The original joint editor has a 1um root-step export allowance.
            cap = serialized_cap(limits['root_step_m'], float(np.linalg.norm(edits[f]-edits[f-1])), eps)
            norm(edits[f]-edits[f-1], self.maps[2*f]-self.maps[2*f-2], cap)
        for goal in self.targets['goals']:
            f, n = goal['frame'], goal['node']
            delta = self.world[2*f,n,:3,3]-goal['position_m']
            norm(delta, self.maps[2*f]*int(n in self.affected), float(np.linalg.norm(delta)))
        nodes = sorted({g['node'] for g in self.targets['goals']})
        for n in nodes:
            acceleration = np.diff(self.world[::2,n,:3,3], n=2, axis=0)*900
            for vector, matrix in zip(acceleration, self.acc_maps):
                norm(vector, matrix*int(n in self.affected), np.linalg.norm(vector))
        return dict(fixed_context_frames=fixed, joint_goals=len(self.targets['goals']),
                    goal_node_acceleration_cones=len(nodes)*(self.frames-2), envelope_root_bounds=True)


def prepare(output):
    if output.exists():
        raise ValueError('Preserve previous study')
    output.mkdir(parents=True)
    cases = []
    for item in read(ROOT/'reports/authoring-intent-audit-v1/request.json')['cases']:
        if item['kind'] != 'joint_edit':
            continue
        source = ROOT/'reports/rig-jobs'/item['id']
        request, result = read(source/'request.json'), read(source/'result.json')
        check_files(source, item['files'])
        check_files(source, request['input_files'])
        case = output/item['id']; case.mkdir()
        for name in ('input','transfer'):
            (case/name).mkdir()
            shutil.copyfile(source/name/'character.glb',case/name/'character.glb')
        for name in ('joint-targets.json','joint-spec.json','joint-edit.json','result.json','request.json'):
            shutil.copyfile(source/name,case/name)
        spec = read(source/'joint-spec.json')
        spec['glb_sha256'] = sha256(case/'input/character.glb')
        # Joint supports are explicit retained world targets; include all of them
        # in the base patch/target/edge guards as well as inherited contacts.
        targets = read(source/'joint-targets.json')
        for i,support in enumerate(targets['supports']):
            name = 'joint-support-'+str(i)
            if name in spec['patches']:
                raise ValueError('Support name collision')
            spec['patches'][name] = dict(vertices=support['vertices'])
            spec['contacts'].append(dict(patch=name,start_frame=support['start_frame'],
                end_frame_exclusive=support['end_frame_exclusive'],target_position_m=support['target_position_m']))
        save(case/'contact-spec.json',spec)
        files = {p.relative_to(case).as_posix():sha256(p) for p in case.rglob('*') if p.is_file()}
        cases.append(dict(id=item['id'],source='input',candidate='transfer',files=files,
                          original_files=item['files'],input_files=request['input_files']))
    # Snapshot this adapter and all local imports, including independent audit.
    # Freeze every local transitive dependency before launching the study.
    import ast
    dest=output/'implementation';dest.mkdir()
    pending,seen=[Path(__file__).name],set()
    while pending:
        name=pending.pop()
        if name in seen:continue
        seen.add(name);path=ROOT/'scripts'/name;shutil.copyfile(path,dest/name)
        for node in ast.walk(ast.parse(path.read_text(encoding='utf-8-sig'))):
            modules=[node.module] if isinstance(node,ast.ImportFrom) else [a.name for a in node.names] if isinstance(node,ast.Import) else []
            for module in modules:
                child=(module or '').split('.')[0]+'.py'
                if (ROOT/'scripts'/child).exists():pending.append(child)
    save(output/'protocol.json',dict(at=now(),policy=copy.deepcopy(POLICY),cases=cases,
        implementation={n:sha256(dest/n) for n in sorted(seen)},quality_approved=False,
        scope='Both completed joint-edit jobs from frozen intake. Preserve world goals, timed context, envelope root bounds and support geometry. Development only.'))
    save(output/'freeze.json',dict(protocol_sha256=sha256(output/'protocol.json')))


def run(output):
    protocol=read(output/'protocol.json')
    if read(output/'freeze.json')['protocol_sha256']!=sha256(output/'protocol.json'):
        raise ValueError('Protocol changed')
    check_files(ROOT/'scripts',protocol['implementation']);check_files(output/'implementation',protocol['implementation'])
    rows=[]
    with threadpool_limits(limits=1):
        for case in protocol['cases']:
            folder=output/case['id'];dest=folder/'cleanup';dest.mkdir(exist_ok=False)
            p=JointProblem(folder,case,protocol['policy'])
            offsets,proposal=p.propose();save(dest/'proposal.json',proposal)
            attempts=[];selected=p.source
            if offsets is not None:
                np.save(dest/'offsets.npy',offsets)
                for fraction in protocol['policy']['fractions']:
                    path=dest/('candidate-'+str(fraction)+'.glb');export(p.rig,p.root,offsets*fraction,path)
                    base=verify(p,path)
                    audit=inspect(folder,path,protocol['policy'])
                    accepted=base['all_preservation_checks_passed'] and base['objective_improved'] and audit['all_checks_passed']
                    save(path.with_suffix('.json'),dict(base=base,joint=audit,accepted=accepted))
                    attempts.append(dict(fraction=fraction,path=str(path),accepted=accepted))
                    if accepted:selected=path;break
            check_files(folder,case['files'])
            original=ROOT/'reports/rig-jobs'/case['id'];check_files(original,case['original_files']);check_files(original,case['input_files'])
            rows.append(dict(id=case['id'],status='improved' if selected!=p.source else 'input_retained',
                selected=str(selected),selected_sha256=sha256(selected),attempts=attempts,
                original_status=read(folder/'result.json').get('joint_edit_status'),quality_approved=False))
            save(dest/'result.json',rows[-1]);print(case['id'],rows[-1]['status'],flush=True)
    save(output/'completion.json',dict(at=now(),rows=rows,protocol_sha256=sha256(output/'protocol.json'),quality_approved=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['prepare','run']);parser.add_argument('output',type=Path)
    args=parser.parse_args()
    (prepare if args.command=='prepare' else run)(args.output.resolve())
