"""Root-only convex correction retaining exact authored rotation channels.

Development adapter for completed Studio edits, with actual exported safeguards.
It preserves achieved targets; it does not repair poses, semantics or interactions.
"""
import argparse
import ast
import copy
from pathlib import Path
import shutil
import numpy as np
from scipy import sparse
from threadpoolctl import threadpool_limits
from strep import ROOT, read, save, sha256, now
from rig_asset import RigAsset, array
from rig_clip_import import AnimationSampler
from gltf_tools import append_accessor, write_glb
from audit_authoring_intent import check_files, same_rig
from conic_root_descent import solver_module


POLICY = dict(position_tolerance_m=1e-6, acceleration_tolerance_m_s2=.0036,
              preserve_patch_acceleration=True,
              preserve_serialized_budget_caps=True,
              root_correction_radius_m=.01, endpoint_fixed_frames=2,
              solver_iterations=150, solver_time_limit_s=60,
              objective_regularizer=1., minimum_energy_improvement=1e-5,
              fractions=[1., .5, .25, .125])


def serialized_cap(nominal, observed, allowance):
    """Retain only existing source precision error inside the unchanged audit bound."""
    if not all(np.isfinite(v) for v in (nominal, observed, allowance)) or min(nominal, observed, allowance) < 0:
        raise ValueError('Finite nonnegative source budget required')
    if observed > nominal+allowance:
        raise ValueError('Source exceeds the original exported root budget')
    return max(nominal, observed)


def affected_nodes(parents, root):
    selected = []
    for n in range(len(parents)):
        ancestor = n
        while ancestor >= 0 and ancestor != root:
            ancestor = parents[ancestor]
        if ancestor == root:
            selected.append(n)
    return selected


def root_weights(rig, root):
    affected = np.zeros(len(rig.parents))
    affected[affected_nodes(rig.parents, root)] = 1
    return np.concatenate([np.full(len(p['positions']), affected[p['node']]) if p['joints'] is None else
                           np.sum(affected[np.asarray(rig.joints)[p['joints']]]*p['weights'], axis=1)
                           for p in rig.primitives])


def root_channel(rig, root, frames):
    if len(rig.document.get('animations', [])) != 1:
        raise ValueError('Adapter requires one selected animation')
    animation = rig.document['animations'][0]
    matches = [c for c in animation['channels'] if c['target'] == dict(node=root, path='translation')]
    if len(matches) != 1:
        raise ValueError('A unique sampled root translation channel is required')
    channel = matches[0]
    sampler = animation['samplers'][channel['sampler']]
    times = array(rig.document, rig.binary, sampler['input'])
    if sampler.get('interpolation', 'LINEAR') != 'LINEAR' or not np.array_equal(times, np.arange(frames, dtype=np.float32)/30):
        raise ValueError('Root channel must retain the complete 30fps LINEAR key clock')
    return channel, sampler, array(rig.document, rig.binary, sampler['output'])


def export(rig, root, offsets, path):
    channel, sampler, local = root_channel(rig, root, len(offsets))
    document, binary = copy.deepcopy(rig.document), bytearray(rig.binary)
    animation = document['animations'][0]
    # New sampler rather than mutating an old one that another channel may share.
    new_sampler = copy.deepcopy(sampler)
    new_sampler['output'] = append_accessor(document, binary, local+offsets, 'VEC3')
    index = rig.document['animations'][0]['channels'].index(channel)
    animation['channels'][index]['sampler'] = len(animation['samplers'])
    animation['samplers'].append(new_sampler)
    write_glb(path, document, binary)


def load_motion(path, frames):
    rig = RigAsset.load(path)
    sampler = AnimationSampler(rig.document, rig.binary, 0)
    if abs(sampler.duration-(frames-1)/30) > 1e-5:
        raise ValueError('Motion clock changed')
    times = np.arange(2*frames-1, dtype=np.float32)/60
    world = np.asarray([sampler.sample(float(t)) for t in times])
    return rig, world


def offset_maps(world, parents, root, frames):
    """Local root key displacement to world displacement at keys and midpoints."""
    parent = parents[root]
    maps = []
    for i in range(2*frames-1):
        rotation = np.eye(3) if parent < 0 else world[i, parent, :3, :3]
        m = sparse.lil_matrix((3, 3*frames))
        if i % 2:
            # Match float32 animation key clock exactly, not an assumed .5.
            f = i//2
            time = float(np.float32(i/60))
            first, last = float(np.float32(f/30)), float(np.float32((f+1)/30))
            w = (time-first)/(last-first)
            m[:, 3*f:3*f+3] = (1-w)*rotation
            m[:, 3*f+3:3*f+6] = w*rotation
        else:
            m[:, 3*(i//2):3*(i//2)+3] = rotation
        maps.append(m.tocsc())
    return maps


def prepare(audit, output):
    if output.exists():
        raise ValueError('Preserve existing study')
    base = read(audit/'request.json')
    complete = read(audit/'completion.json')
    if complete['request_sha256'] != sha256(audit/'request.json') or complete['failed']:
        raise ValueError('Complete successful intake audit required')
    check_files(audit, complete['files'])
    output.mkdir(parents=True)
    (output/'implementation').mkdir()
    pending, seen = [Path(__file__).name], set()
    while pending:
        name = pending.pop()
        if name in seen:
            continue
        seen.add(name)
        path = ROOT/'scripts'/name
        shutil.copyfile(path, output/'implementation'/name)
        for node in ast.walk(ast.parse(path.read_text(encoding='utf-8-sig'))):
            modules = ([node.module] if isinstance(node, ast.ImportFrom) else
                       [a.name for a in node.names] if isinstance(node, ast.Import) else [])
            for module in modules:
                child = (module or '').split('.')[0]+'.py'
                if (ROOT/'scripts'/child).exists():
                    pending.append(child)
    bootstrap = ROOT/'reports/conic-solver-bootstrap-v1.json'
    save(output/'request.json', dict(at=now(), policy=POLICY, intake=str(audit),
         intake_sha256=sha256(audit/'completion.json'), jobs=base['jobs'], cases=base['cases'],
         implementation={n: sha256(output/'implementation'/n) for n in sorted(seen)},
         solver_bootstrap_sha256=sha256(bootstrap),
         scope='All 15 completed authored edits from frozen intake. Root translation component only. Whole-clip acceleration of every declared patch is constrained, including inactive intervals and release boundaries. Joint and posture jobs retain fixed body/root as no-ops. Contact targets/rotation channels/geometry remain explicit. No quality promotion.'))
    print('Prepared', len(base['cases']), 'cases', flush=True)


class Problem:
    def additional_constraints(self, linear, norm, equal):
        """Specialized authoring adapters may add stricter constraints."""
        return {}

    def __init__(self, folder, case, policy):
        self.folder, self.case, self.policy = folder, case, policy
        check_files(folder, case['files'])
        result = read(folder/'result.json')
        self.frames, self.root = result['frames'], result['root_node']
        if result['fps'] != 30:
            raise ValueError('30fps required')
        self.source = folder/case['candidate']/'character.glb'
        self.rig, self.world = load_motion(self.source, self.frames)
        before_rig, before = load_motion(folder/case['source']/'character.glb', self.frames)
        same_rig(self.rig, before_rig)
        self.original_root = before[::2, self.root, :3, 3]
        root_channel(self.rig, self.root, self.frames)
        self.maps = offset_maps(self.world, self.rig.parents, self.root, self.frames)
        self.weights = root_weights(self.rig, self.root)
        self.spec = read(folder/'contact-spec.json')
        if self.spec['glb_sha256'] != sha256(folder/case['source']/'character.glb'):
            raise ValueError('Original authored target binding changed')
        self.points = np.asarray([self.rig.vertices(w) for w in self.world])
        self.width = 3*self.frames
        self.root_positions = self.world[::2, self.root, :3, 3]
        self.acceleration = np.diff(self.root_positions, n=2, axis=0)*900
        self.acc_maps = [(self.maps[2*f+4]-2*self.maps[2*f+2]+self.maps[2*f])*900 for f in range(self.frames-2)]
        self.contacts = []
        for c in self.spec['contacts']:
            ids = self.spec['patches'][c['patch']]['vertices']
            track = self.points[::2, ids].mean(axis=1)
            self.contacts.append(dict(spec=c, ids=ids, track=track, weight=float(self.weights[ids].mean())))

    def propose(self):
        clarabel = solver_module()
        mats, rhs, cones = [], [], []
        initial_margins = []

        def linear(matrix, bound):
            mats.append(sparse.csc_matrix(matrix))
            rhs.append(np.atleast_1d(bound))
            cones.append(clarabel.NonnegativeConeT(len(np.atleast_1d(bound))))
            initial_margins.extend(np.atleast_1d(bound).tolist())

        def norm(vector, matrix, cap):
            vector = np.atleast_1d(vector)
            scale = max(float(cap), 1e-4)
            mats.append(sparse.vstack([sparse.csc_matrix((1, self.width)), -matrix], format='csc')/scale)
            rhs.append(np.r_[cap, vector]/scale)
            cones.append(clarabel.SecondOrderConeT(len(vector)+1))
            initial_margins.append(float((cap-np.linalg.norm(vector))/scale))

        def equal(matrix, value):
            mats.append(sparse.csc_matrix(matrix))
            rhs.append(np.atleast_1d(value))
            cones.append(clarabel.ZeroConeT(len(np.atleast_1d(value))))

        active = self.weights > 1e-12
        for i, (points, matrix) in enumerate(zip(self.points, self.maps)):
            # Equivalent to every affected vertex retaining its original depth
            # or remaining above the floor. Static geometry cannot move.
            minimum = float(np.max((-np.maximum(0, -points[active, 1])-points[active, 1])/self.weights[active]))
            linear(-matrix[1], -minimum)
        lim = self.spec['limits']
        edits = self.root_positions-self.original_root
        retained_caps = []
        def budget(nominal, observed, allowance):
            cap = serialized_cap(nominal, observed, allowance) if self.policy.get('preserve_serialized_budget_caps', False) else nominal
            if cap > nominal:
                retained_caps.append(cap-nominal)
            return cap
        for f in range(self.frames):
            m = self.maps[2*f]
            eps = self.policy['position_tolerance_m']
            horizontal = budget(lim['root_horizontal_m'], float(np.linalg.norm(edits[f, [0, 2]])), eps)
            vertical = budget(lim['root_vertical_m'], float(abs(edits[f, 1])), eps)
            norm(edits[f, [0, 2]], m[[0, 2]], horizontal)
            linear(m[1], vertical-edits[f, 1])
            linear(-m[1], vertical+edits[f, 1])
            norm(np.zeros(3), m, self.policy['root_correction_radius_m'])
            if f:
                step = budget(lim['root_step_m'], float(np.linalg.norm(edits[f]-edits[f-1])), 2*eps)
                norm(edits[f]-edits[f-1], m-self.maps[2*f-2], step)
            if f < 2 or f >= self.frames-2:
                mats.append(m)
                rhs.append(np.zeros(3))
                cones.append(clarabel.ZeroConeT(3))
        for v, matrix in zip(self.acceleration, self.acc_maps):
            norm(v, matrix, np.linalg.norm(v))
        patch_cones = 0
        if self.policy.get('preserve_patch_acceleration', False):
            # Include all declared geometry, even patches without an active
            # target interval. This protects release/approach dynamics too.
            for patch in self.spec['patches'].values():
                ids = patch['vertices']
                track = self.points[::2, ids].mean(axis=1)
                weight = float(self.weights[ids].mean())
                acceleration = np.diff(track, n=2, axis=0)*900
                for vector, matrix in zip(acceleration, self.acc_maps):
                    norm(vector, matrix*weight, np.linalg.norm(vector))
                    patch_cones += 1
        for contact in self.contacts:
            c, track, weight = contact['spec'], contact['track'], contact['weight']
            for f in range(c['start_frame'], c['end_frame_exclusive']):
                vector = track[f]-c['target_position_m']
                norm(vector, self.maps[2*f]*weight, np.linalg.norm(vector))
                if f > c['start_frame']:
                    vector = track[f]-track[f-1]
                    norm(vector, (self.maps[2*f]-self.maps[2*f-2])*weight, np.linalg.norm(vector))
        additional = self.additional_constraints(linear, norm, equal)
        a = sparse.vstack(self.acc_maps, format='csc')
        v = self.acceleration.ravel()
        p = (a.T@a+sparse.eye(self.width)*self.policy['objective_regularizer']).tocsc()
        q = np.asarray(a.T@v).ravel()
        # Common objective scale avoids enormous curvature without changing optimum.
        scale = max(float(abs(p.diagonal()).max()), 1.)
        settings = clarabel.DefaultSettings()
        settings.verbose = False
        settings.max_iter = self.policy['solver_iterations']
        settings.time_limit = self.policy['solver_time_limit_s']
        settings.tol_gap_abs = settings.tol_gap_rel = settings.tol_feas = 1e-9
        if hasattr(settings, 'max_threads'):
            settings.max_threads = 1
        solver = clarabel.DefaultSolver(sparse.triu(p/scale).tocsc(), q/scale,
            sparse.vstack(mats, format='csc'), np.concatenate(rhs), cones, settings)
        result = solver.solve()
        record = dict(status=str(result.status), iterations=result.iterations,
                      solve_time_s=result.solve_time, variables=self.width, rows=sum(len(r) for r in rhs),
                      patch_acceleration_cones=patch_cones,
                      additional_constraints=additional,
                      retained_serialized_budget_caps=len(retained_caps),
                      largest_retained_budget_excess_m=max(retained_caps, default=0.),
                      initial_minimum_constraint_margin=float(min(initial_margins)),
                      primal_residual=getattr(result, 'r_prim', None), dual_residual=getattr(result, 'r_dual', None))
        offsets = np.asarray(result.x).reshape(self.frames, 3)
        if str(result.status) not in ('Solved', 'AlmostSolved') or not np.isfinite(offsets).all():
            return None, record
        return offsets, record


def verify(problem, path):
    """Decode actual GLB; do not reuse solver matrices for acceptance."""
    p = problem
    rig, world = load_motion(path, p.frames)
    same_rig(p.rig, rig)
    points = np.asarray([rig.vertices(w) for w in world])
    position_eps = p.policy['position_tolerance_m']
    root = world[::2, p.root, :3, 3]
    delta = root-p.root_positions
    edits = root-p.original_root
    acceleration = np.diff(root, n=2, axis=0)*900
    norms = np.linalg.norm(acceleration, axis=1)
    source_norms = np.linalg.norm(p.acceleration, axis=1)
    limits = p.spec['limits']
    floor_excess = float(np.max(np.maximum(0, -points[:, :, 1])-np.maximum(0, -p.points[:, :, 1])))
    rotations_error = float(np.abs(world[:, :, :3, :3]-p.world[:, :, :3, :3]).max())
    # Verify all unrelated channel semantics, including local translations.
    old_animation, new_animation = p.rig.document['animations'][0], rig.document['animations'][0]
    channels_preserved = len(old_animation['channels']) == len(new_animation['channels'])
    for old, new in zip(old_animation['channels'], new_animation['channels']):
        if old['target'] != new['target']:
            channels_preserved = False
            continue
        if old['target'] == dict(node=p.root, path='translation'):
            continue
        os, ns = old_animation['samplers'][old['sampler']], new_animation['samplers'][new['sampler']]
        channels_preserved &= os == ns
        for key in ('input', 'output'):
            channels_preserved &= np.array_equal(array(p.rig.document, p.rig.binary, os[key]), array(rig.document, rig.binary, ns[key]))
    contacts = []
    for item in p.contacts:
        c = item['spec']
        a, b = c['start_frame'], c['end_frame_exclusive']
        track = points[::2, item['ids']].mean(axis=1)
        original = item['track']
        error = np.linalg.norm(track[a:b]-c['target_position_m'], axis=1)
        old_error = np.linalg.norm(original[a:b]-c['target_position_m'], axis=1)
        edge = np.linalg.norm(np.diff(track[a:b], axis=0), axis=1)
        old_edge = np.linalg.norm(np.diff(original[a:b], axis=0), axis=1)
        contacts.append(dict(patch=c['patch'], start_frame=a, end_frame_exclusive=b,
            source_error_max_m=float(old_error.max()), candidate_error_max_m=float(error.max()),
            error_cap_excess_m=float((error-old_error).max()),
            edge_cap_excess_m=float((edge-old_edge).max()) if len(edge) else 0.))
    checks = dict(rotation_channels_preserved=bool(channels_preserved and rotations_error < 1e-12),
        floor_at_keys_and_midpoints=floor_excess <= position_eps,
        authored_contact_positions=all(c['error_cap_excess_m'] <= position_eps for c in contacts),
        authored_contact_edges=all(c['edge_cap_excess_m'] <= position_eps for c in contacts),
        original_root_horizontal=float(np.linalg.norm(edits[:, [0, 2]], axis=1).max()) <= limits['root_horizontal_m']+position_eps,
        original_root_vertical=float(np.abs(edits[:, 1]).max()) <= limits['root_vertical_m']+position_eps,
        original_root_steps=float(np.linalg.norm(np.diff(edits, axis=0), axis=1).max()) <= limits['root_step_m']+2*position_eps,
        correction_radius=float(np.linalg.norm(delta, axis=1).max()) <= p.policy['root_correction_radius_m']+position_eps,
        endpoints=float(np.abs(delta[[0, 1, -2, -1]]).max()) <= position_eps,
        no_new_root_acceleration_peak=bool(np.max(norms-source_norms) <= p.policy['acceleration_tolerance_m_s2']))
    energy_before, energy_after = float(np.square(source_norms).sum()), float(np.square(norms).sum())
    patches = []
    if p.policy.get('preserve_patch_acceleration', False):
        for name, patch in p.spec['patches'].items():
            ids = patch['vertices']
            old = np.linalg.norm(np.diff(p.points[::2, ids].mean(axis=1), n=2, axis=0)*900, axis=1)
            new = np.linalg.norm(np.diff(points[::2, ids].mean(axis=1), n=2, axis=0)*900, axis=1)
            patches.append(dict(patch=name, source_peak_m_s2=float(old.max()), candidate_peak_m_s2=float(new.max()),
                source_p95_m_s2=float(np.percentile(old, 95)), candidate_p95_m_s2=float(np.percentile(new, 95)),
                maximum_frame_excess_m_s2=float((new-old).max())))
        checks['whole_clip_patch_acceleration'] = all(item['maximum_frame_excess_m_s2'] <= p.policy['acceleration_tolerance_m_s2'] for item in patches)
    return dict(at=now(), glb_sha256=sha256(path), checks=checks, all_preservation_checks_passed=all(checks.values()),
        root_acceleration_before=dict(max=float(source_norms.max()), p95=float(np.percentile(source_norms, 95)), energy=energy_before),
        root_acceleration_after=dict(max=float(norms.max()), p95=float(np.percentile(norms, 95)), energy=energy_after),
        objective_improved=energy_after < energy_before-max(p.policy['minimum_energy_improvement'],
            p.policy.get('minimum_relative_energy_improvement',0.)*energy_before),
        max_root_displacement_m=float(np.linalg.norm(delta, axis=1).max()),
        root_acceleration_cap_excess_m_s2=float(np.max(norms-source_norms)),
        rotation_matrix_max_error=rotations_error, floor_cap_excess_m=floor_excess, contacts=contacts, patches=patches,
        quality_approved=False)


def run(output):
    request = read(output/'request.json')
    if (output/'completion.json').exists():
        raise ValueError('Preserve completed study')
    check_files(ROOT/'scripts', request['implementation'])
    check_files(output/'implementation', request['implementation'])
    if sha256(ROOT/'reports/conic-solver-bootstrap-v1.json') != request['solver_bootstrap_sha256']:
        raise ValueError('Solver bootstrap changed')
    rows = []
    with threadpool_limits(limits=1):
        for case in request['cases']:
            dest = output/case['id']
            dest.mkdir(exist_ok=False)
            folder = Path(request['jobs'])/case['id']
            try:
                check_files(folder, case['files'])
                if case['kind'] != 'contact_edit':
                    row = dict(id=case['id'], status='fixed_body_noop', reason='Joint/finger authoring retains body/root context. Root-only cleanup does not alter requested joint or finger poses.',
                               selected_sha256=sha256(folder/case['candidate']/'character.glb'), quality_approved=False)
                else:
                    problem = Problem(folder, case, request['policy'])
                    offsets, proposal = problem.propose()
                    save(dest/'proposal.json', proposal)
                    if offsets is None:
                        row = dict(id=case['id'], status='no_solver_proposal', solver=proposal, quality_approved=False)
                    else:
                        np.save(dest/'proposed-local-root-offsets.npy', offsets)
                        attempts, chosen = [], None
                        for fraction in request['policy']['fractions']:
                            name = 'candidate-'+str(fraction)
                            path = dest/(name+'.glb')
                            export(problem.rig, problem.root, offsets*fraction, path)
                            audit = verify(problem, path)
                            save(dest/(name+'-audit.json'), audit)
                            accepted = audit['all_preservation_checks_passed'] and audit['objective_improved']
                            attempts.append(dict(fraction=fraction, path=path.name, audit=name+'-audit.json', accepted=accepted))
                            if accepted:
                                chosen = path
                                break
                        row = dict(id=case['id'], status='candidate_preserved' if chosen else 'no_accepted_candidate', attempts=attempts,
                                   selected=str(chosen) if chosen else str(problem.source),
                                   selected_sha256=sha256(chosen or problem.source), quality_approved=False)
                check_files(folder, case['files'])
            except Exception as error:
                row = dict(id=case['id'], status='failed', error=str(error), quality_approved=False)
            save(dest/'result.json', row)
            rows.append(row)
            save(output/'pipeline.json', dict(at=now(), completed=len(rows), planned=len(request['cases']), last=row))
            print(case['id'], row['status'], row.get('error', ''), flush=True)
    check_files(ROOT/'scripts', request['implementation'])
    save(output/'completion.json', dict(at=now(), request_sha256=sha256(output/'request.json'), rows=rows,
         files={p.relative_to(output).as_posix(): sha256(p) for p in output.glob('*/*') if p.is_file() and p.parent.name != 'implementation'},
         quality_approved=False, scope='Root component candidates and no-ops only. No engine verification or general pose correction established by this run.'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['prepare', 'run'])
    parser.add_argument('output', type=Path)
    parser.add_argument('--intake', type=Path, default=ROOT/'reports/authoring-intent-audit-v1')
    args = parser.parse_args()
    if args.command == 'prepare':
        prepare(args.intake.resolve(), args.output.resolve())
    else:
        run(args.output.resolve())
