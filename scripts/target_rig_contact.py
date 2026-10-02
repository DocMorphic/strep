"""Bounded target-mesh floor/support fitting, retaining rejected candidates.

Contact patches are explicit vertex sets and intervals in a hash-bound editable
spec. The convenience draft uses source predictions, not confirmed annotations.
"""
import argparse
import copy
import shutil
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
from threadpoolctl import threadpool_limits
from strep import read, save, sha256, now
from rig_asset import RigAsset
from gltf_tools import sample_animation, append_accessor, write_glb, local_matrix


class SoleDraftUnsupported(ValueError):
    """The automatic sole heuristic cannot represent this otherwise valid rig."""


class SkinEvaluator:
    """Cache bind-space vertices; matches the separate RigAsset evaluator."""
    def __init__(self, rig):
        indices, local, weights = [], [], []
        for primitive in rig.primitives:
            points = np.c_[primitive['positions'], np.ones(len(primitive['positions']))]
            if primitive['joints'] is None:
                indices.append(np.full((len(points), 1), primitive['node']))
                local.append(points[:, None]); weights.append(np.ones((len(points), 1)))
            else:
                indices.append(np.asarray(rig.joints)[primitive['joints']])
                local.append(np.einsum('vkij,vj->vki', rig.inverse[primitive['joints']], points))
                weights.append(primitive['weights'])
        self.parts = list(zip(indices, local, weights))
        self.count = sum(len(x) for x in indices)

    def vertices(self, world):
        return np.concatenate([np.einsum('vkij,vkj,vk->vi', world[nodes, :3, :], points, weights)
                               for nodes, points, weights in self.parts])


def baseline(rig, frames):
    world = np.array([sample_animation(rig.document, rig.binary, 0, f) for f in range(frames)])
    local = world.copy()
    for node, parent in enumerate(rig.parents):
        if parent >= 0:
            local[:, node] = np.linalg.inv(world[:, parent]) @ world[:, node]
    return world, local


def floor_lower_bound(rig, spec, before):
    """Prove some floor requests infeasible without searching the pose space.

Vertices unaffected by every editable rotation can rise only by their weighted
root translation allowance. This optimistic bound ignores temporal/contact
restrictions; a positive failure is conclusive, zero is not feasibility proof.
"""
    edits={e['node'] for e in spec['edit_joints'].values()};root=spec['root_node']
    def ancestors(node):
        result=set()
        while node>=0:result.add(node);node=rig.parents[node]
        return result
    chains=[ancestors(n) for n in range(len(rig.parents))]
    rotated=np.array([bool(chain & edits) for chain in chains]);translated=np.array([root in chain for chain in chains])
    invariant=[];allowance=[]
    for primitive in rig.primitives:
        if primitive['joints'] is None:
            invariant.extend([not rotated[primitive['node']]]*len(primitive['positions']))
            allowance.extend([float(translated[primitive['node']])]*len(primitive['positions']))
        else:
            nodes=np.asarray(rig.joints)[primitive['joints']];weights=primitive['weights']
            invariant.extend(np.sum(weights*rotated[nodes],axis=1)<=1e-12)
            allowance.extend(np.sum(weights*translated[nodes],axis=1))
    indices=np.flatnonzero(invariant);allowance=np.asarray(allowance)[indices]*spec['limits']['root_vertical_m']
    maximum=0.;worst_frame=None;worst_vertex=None;failed=[]
    for frame,world in enumerate(before):
        if not len(indices):break
        depth=np.maximum(-(rig.vertices(world)[indices,1]+allowance),0)
        value=float(depth.max())
        if value>spec['screen']['floor_depth_m']:failed.append(frame)
        if value>maximum:
            maximum=value;worst_frame=frame;worst_vertex=int(indices[int(np.argmax(depth))])
    return dict(floor_infeasible_under_declared_edits=bool(failed),unavoidable_floor_depth_lower_bound_m=maximum,
        frames_proven_infeasible=failed,worst_frame=worst_frame,worst_vertex=worst_vertex,
        rotation_invariant_vertex_count=len(indices),scope='Optimistic bound for vertices unaffected by editable rotations, using maximal allowed upward world root translation. Zero bound does not prove feasibility.')


def prepare_animated_node(document, node):
    """glTF animation targets must use TRS, including newly edited helper bones."""
    entry=document['nodes'][node];reference=local_matrix(entry)
    entry.pop('matrix',None)
    entry.update(translation=reference[:3,3].tolist(),rotation=Rotation.from_matrix(reference[:3,:3]).as_quat().tolist(),scale=[1,1,1])


def regions(rig, mapping):
    """Three sole patches per side using default-pose geometry and skin weights."""
    points = rig.vertices(rig.reference)
    patches = {}
    for side in ('Left', 'Right'):
        roles = [side + 'Foot', side + 'ToeBase']
        if any(role not in mapping for role in roles):
            raise SoleDraftUnsupported('Automatic sole draft needs mapped foot and toe-base roles')
        joints = [rig.joints.index(mapping[role]) for role in roles]
        membership = np.concatenate([np.zeros(len(p['positions'])) if p['joints'] is None else
            np.sum(np.where(np.isin(p['joints'], joints), p['weights'], 0), axis=1) for p in rig.primitives])
        region = np.flatnonzero(membership >= .65)
        if len(region) < 12:
            raise SoleDraftUnsupported('Too few weighted foot vertices for a sole draft; author patches explicitly')
        sole = region[points[region, 1] <= points[region, 1].min() + .003]
        if len(sole) < 6:
            raise SoleDraftUnsupported('No sufficiently flat reference sole; author patches explicitly')
        forward = rig.reference[mapping[side + 'ToeBase'], :3, 3] - rig.reference[mapping[side + 'Foot'], :3, 3]
        forward[1] = 0
        if np.linalg.norm(forward) < 1e-5:
            raise SoleDraftUnsupported('Cannot infer horizontal sole direction')
        forward /= np.linalg.norm(forward)
        lateral = np.cross([0, 1, 0], forward)
        along, across = points[sole] @ forward, points[sole] @ lateral
        heel = sole[along <= np.quantile(along, .25)]
        front = along >= np.quantile(along, .65)
        divider = np.median(across[front])
        for name, vertices in [('heel', heel), ('fore-a', sole[front & (across <= divider)]), ('fore-b', sole[front & (across > divider)])]:
            if not len(vertices):
                raise SoleDraftUnsupported('Empty sole patch; author patches explicitly')
            patches[side + '-' + name] = dict(vertices=vertices.tolist(), side=side,
                source_role=side + ('Foot' if name == 'heel' else 'ToeBase'))
    return patches


def draft(folder, path):
    folder = Path(folder); report = read(folder / 'report.json')
    if report.get('source_kind')=='gltf_animation':
        raise SoleDraftUnsupported('Existing animation has no source contact predictions; author mesh contacts explicitly')
    if sha256(folder / 'character.glb') != report['glb_sha256'] or sha256(report['source']) != report['source_sha256']:
        raise ValueError('Transfer/source checksum changed')
    rig = RigAsset.load(folder / 'character.glb')
    from rig_contact_tracks import signals
    masks,_=signals(report)
    world, _ = baseline(rig, report['frames']); skin = SkinEvaluator(rig)
    patches = regions(rig, report['mapping'])
    trajectories = {name: [] for name in patches}
    for matrix in world:
        vertices = skin.vertices(matrix)
        for name, patch in patches.items():
            trajectories[name].append(vertices[patch['vertices']].mean(axis=0))
    contacts = []
    for name, patch in patches.items():
        mask = masks[patch['source_role']]
        edges = np.diff(np.r_[False, mask, False].astype(int))
        for start, end in zip(np.flatnonzero(edges == 1), np.flatnonzero(edges == -1)):
            target = np.median(np.array(trajectories[name])[start:end], axis=0)
            target[1] = .0015
            contacts.append(dict(patch=name, start_frame=int(start), end_frame_exclusive=int(end), target_position_m=target.tolist()))
    spec = dict(schema='strep-target-contact-v1', glb_sha256=report['glb_sha256'], fps=report['fps'], frames=report['frames'],
        provenance='Drafted from inherited model foot/toe predictions and reference sole geometry; not independently confirmed contacts',
        root_node=report['root_node'], patches=patches, contacts=contacts,
        edit_joints={role: dict(node=report['mapping'][role], limit_degrees=35 if 'Shin' in role else 25 if 'ToeBase' not in role else 15)
                     for side in ('Left', 'Right') for role in [side + part for part in ('Leg', 'Shin', 'Foot', 'ToeBase')]},
        limits=dict(root_horizontal_m=.04, root_vertical_m=.12, root_step_m=.015, joint_step_degrees=5),
        screen=dict(floor_depth_m=.005, contact_error_m=.02),
        objective=dict(contact_weight=12., floor_weight=4., rotation_prior_m_per_radian=.035,
                       root_prior=1., temporal_weight=.5), max_nfev=120)
    save(path, spec); return spec


def validate(spec, rig):
    required = {'schema', 'glb_sha256', 'fps', 'frames', 'provenance', 'root_node', 'patches', 'contacts', 'edit_joints', 'limits', 'screen', 'objective', 'max_nfev'}
    if set(spec) != required or spec['schema'] != 'strep-target-contact-v1':
        raise ValueError('Invalid target contact specification')
    if type(spec['frames']) is not int or spec['frames'] < 2 or spec['fps'] != 30:
        raise ValueError('Contact fitting currently requires at least two 30fps frames')
    skin = SkinEvaluator(rig)
    if type(spec['root_node']) is not int or spec['root_node'] not in rig.joints:
        raise ValueError('Invalid root node')
    if not spec['patches'] or not spec['edit_joints']:
        raise ValueError('Patches and editable joints are required')
    for patch in spec['patches'].values():
        indices = patch['vertices']
        if not isinstance(indices, list) or not indices or any(type(i) is not int or not 0 <= i < skin.count for i in indices) or len(set(indices)) != len(indices):
            raise ValueError('Invalid contact patch vertices')
    occupancy = set()
    for contact in spec['contacts']:
        if set(contact) != {'patch', 'start_frame', 'end_frame_exclusive', 'target_position_m'} or contact['patch'] not in spec['patches']:
            raise ValueError('Invalid contact entry')
        a, b = contact['start_frame'], contact['end_frame_exclusive']
        if type(a) is not int or type(b) is not int or not 0 <= a < b <= spec['frames']:
            raise ValueError('Invalid contact interval')
        target = np.asarray(contact['target_position_m'])
        if target.shape != (3,) or not np.isfinite(target).all():
            raise ValueError('Invalid contact target')
        for f in range(a, b):
            if (contact['patch'], f) in occupancy:
                raise ValueError('Overlapping targets for the same patch')
            occupancy.add((contact['patch'], f))
    editable = []
    for entry in spec['edit_joints'].values():
        node, limit = entry['node'], entry['limit_degrees']
        if type(node) is not int or node not in rig.joints or node == spec['root_node'] or node in editable:
            raise ValueError('Invalid editable joint')
        parent = rig.parents[node]
        while parent != -1 and parent != spec['root_node']:
            parent = rig.parents[parent]
        if parent == -1:
            raise ValueError('Edited joints must descend from the mapped root')
        if not np.isfinite(limit) or not 0 < limit <= 90:
            raise ValueError('Joint edit limit must lie in (0,90] degrees')
        editable.append(node)
    for key, fields in [('limits', {'root_horizontal_m', 'root_vertical_m', 'root_step_m', 'joint_step_degrees'}),
                        ('screen', {'floor_depth_m', 'contact_error_m'}),
                        ('objective', {'contact_weight', 'floor_weight', 'rotation_prior_m_per_radian', 'root_prior', 'temporal_weight'})]:
        if set(spec[key]) != fields or any(not np.isfinite(v) or v <= 0 for v in spec[key].values()):
            raise ValueError(f'Invalid {key}')
    if type(spec['max_nfev']) is not int or not 1 <= spec['max_nfev'] <= 200:
        raise ValueError('Invalid solver iteration limit')
    return skin


class Fitter:
    def __init__(self, rig, spec, local):
        self.rig, self.spec, self.local = rig, spec, local
        self.skin = validate(spec, rig)
        self.nodes = [v['node'] for v in spec['edit_joints'].values()]
        self.angles = np.radians([v['limit_degrees'] for v in spec['edit_joints'].values()])
        def depth(n):
            return 0 if rig.parents[n] < 0 else depth(rig.parents[n]) + 1
        self.order = sorted(range(len(rig.parents)), key=depth)
        lim = spec['limits']
        self.bounds = np.r_[[lim['root_horizontal_m']/np.sqrt(2), lim['root_vertical_m'], lim['root_horizontal_m']/np.sqrt(2)], np.repeat(self.angles/np.sqrt(3), 3)]
        self.steps = np.r_[np.full(3, lim['root_step_m']/np.sqrt(3)), np.full(len(self.nodes)*3, np.radians(lim['joint_step_degrees'])/np.sqrt(3))]
        self.active = [[c for c in spec['contacts'] if c['start_frame'] <= f < c['end_frame_exclusive']] for f in range(spec['frames'])]

    def pose(self, frame, values):
        local = self.local[frame].copy()
        deltas = Rotation.from_rotvec(values[3:].reshape(-1, 3)).as_matrix()
        for node, delta in zip(self.nodes, deltas):
            local[node, :3, :3] = local[node, :3, :3] @ delta
        world = np.empty_like(local)
        root = self.spec['root_node']
        for node in self.order:
            parent = self.rig.parents[node]
            parent_world = np.eye(4) if parent < 0 else world[parent]
            if node == root:
                local[node, :3, 3] += np.linalg.solve(parent_world[:3, :3], values[:3])
            world[node] = parent_world @ local[node]
        return world, local

    def residual(self, frame, values, previous):
        objective = self.spec['objective']; world, _ = self.pose(frame, values)
        vertices = self.skin.vertices(world)
        residual = []
        for contact in self.active[frame]:
            ids = self.spec['patches'][contact['patch']]['vertices']
            residual.extend((vertices[ids].mean(axis=0) - contact['target_position_m']) * objective['contact_weight'])
        residual.extend(np.minimum(vertices[:, 1], 0) * objective['floor_weight'])
        residual.extend(values[:3] * objective['root_prior'])
        residual.extend(values[3:] * objective['rotation_prior_m_per_radian'])
        residual.extend((values[:3]-previous[:3]) * objective['temporal_weight'])
        residual.extend((values[3:]-previous[3:]) * objective['rotation_prior_m_per_radian'] * objective['temporal_weight'])
        return np.array(residual)

    def fit_frame(self, frame, previous):
        lower, upper = -self.bounds, self.bounds
        if frame:
            lower, upper = np.maximum(lower, previous-self.steps), np.minimum(upper, previous+self.steps)
        result = least_squares(lambda x: self.residual(frame, x, previous), np.clip(previous, lower+1e-10, upper-1e-10),
            bounds=(lower, upper), max_nfev=self.spec['max_nfev'], ftol=1e-5, xtol=1e-5, gtol=1e-5)
        return result


def audit(rig, spec, before, after, values, solver):
    # Independent evaluator: do not use the fitter's cached vertices here.
    output = {}
    for label, matrices in [('before', before), ('after', after)]:
        floor, contact_errors, all_speeds = [], [], []
        tracks = {name: [] for name in spec['patches']}
        for frame, world in enumerate(matrices):
            vertices = rig.vertices(world); floor.append(max(0., -float(vertices[:, 1].min())))
            for name, patch in spec['patches'].items():
                tracks[name].append(vertices[patch['vertices']].mean(axis=0))
        for contact in spec['contacts']:
            a, b = contact['start_frame'], contact['end_frame_exclusive']
            track = np.array(tracks[contact['patch']])[a:b]
            contact_errors.extend(np.linalg.norm(track - contact['target_position_m'], axis=1).tolist())
            all_speeds.extend((np.linalg.norm(np.diff(track[:, [0, 2]], axis=0), axis=1)*spec['fps']).tolist())
        output[label] = dict(floor_depth_max_m=max(floor), floor_frames_failed=int(np.sum(np.array(floor)>spec['screen']['floor_depth_m'])),
            patch_contact_error_max_m=max(contact_errors, default=None), patch_contact_error_p95_m=float(np.percentile(contact_errors,95)) if contact_errors else None,
            patch_predicted_support_speed_p95_m_s=float(np.percentile(all_speeds,95)) if all_speeds else None)
    root = spec['root_node']; shifts = after[:, root, :3, 3]-before[:, root, :3, 3]
    joint_changes, joint_steps = {}, {}
    for role, entry in spec['edit_joints'].items():
        node = entry['node']; parent = rig.parents[node]
        original = np.linalg.inv(before[:, parent, :3, :3]) @ before[:, node, :3, :3]
        changed = np.linalg.inv(after[:, parent, :3, :3]) @ after[:, node, :3, :3]
        delta = np.linalg.inv(original) @ changed
        joint_changes[role] = float(np.degrees(Rotation.from_matrix(delta).magnitude()).max())
        joint_steps[role] = float(np.degrees(Rotation.from_matrix(delta[:-1].transpose(0,2,1) @ delta[1:]).magnitude()).max())
    changes = dict(root_horizontal_max_m=float(np.linalg.norm(shifts[:,[0,2]],axis=1).max()),root_vertical_max_m=float(np.abs(shifts[:,1]).max()),
                   root_step_max_m=float(np.linalg.norm(np.diff(shifts,axis=0),axis=1).max()),joint_edit_degrees=joint_changes,joint_edit_step_degrees=joint_steps)
    limits = spec['limits']; flags=[]
    for key,limit_key in [('root_horizontal_max_m','root_horizontal_m'),('root_vertical_max_m','root_vertical_m'),('root_step_max_m','root_step_m')]:
        if changes[key]>limits[limit_key]+1e-6: flags.append(key+'_bound_exceeded')
    if any(v>spec['edit_joints'][role]['limit_degrees']+1e-4 for role,v in joint_changes.items()): flags.append('joint_edit_bound_exceeded')
    if any(v>limits['joint_step_degrees']+1e-4 for v in joint_steps.values()): flags.append('joint_edit_step_bound_exceeded')
    if output['after']['floor_frames_failed']: flags.append('target_mesh_floor_screen_failed')
    if output['after']['patch_contact_error_max_m'] is None or output['after']['patch_contact_error_max_m']>spec['screen']['contact_error_m']: flags.append('patch_contact_screen_failed')
    if any(not entry['success'] for entry in solver): flags.append('solver_iteration_limit_or_failure')
    return dict(**output,changes=changes,flags=flags,numerical_screen_passed=not flags,human_approved=False,
                scope='All sampled vertices versus flat floor; authored patch centroids and edit bounds. No continuous/self/object collision, force balance or semantic review.')


def run(folder, spec_path, output):
    folder, spec_path, output = map(lambda p:Path(p).resolve(), (folder, spec_path, output))
    if (folder/'timeline.json').exists() and 'period_frames' in read(folder/'timeline.json'):
        from rig_periodic_contact import run as fit_periodic
        return fit_periodic(folder,spec_path,output)
    spec=read(spec_path);report=read(folder/'report.json');source=folder/'character.glb'
    if sha256(source)!=spec['glb_sha256'] or spec['frames']!=report['frames']: raise ValueError('Spec does not match source transfer')
    rig=RigAsset.load(source);before,local=baseline(rig,spec['frames']);fitter=Fitter(rig,spec,local)
    output.mkdir(parents=True,exist_ok=False);save(output/'pipeline.json',dict(status='fitting',completed_frames=0))
    save(output/'feasibility.json',floor_lower_bound(rig,spec,before))
    snapshot=output/'source-snapshot';snapshot.mkdir()
    for name in ['target_rig_contact.py','rig_asset.py','gltf_tools.py']:
        shutil.copyfile(Path(__file__).with_name(name),snapshot/name)
    shutil.copyfile(spec_path,output/'contact-spec.json')
    previous=np.zeros(len(fitter.bounds));matrices=[];locals_out=[];parameters=[];solver=[]
    with threadpool_limits(limits=1):
        for frame in range(spec['frames']):
            fit=fitter.fit_frame(frame,previous);previous=fit.x
            world,posed=fitter.pose(frame,fit.x);matrices.append(world);locals_out.append(posed);parameters.append(fit.x)
            solver.append(dict(frame=frame,success=bool(fit.success),status=int(fit.status),nfev=int(fit.nfev),cost=float(fit.cost)))
            if frame%30==0:
                save(output/'pipeline.json',dict(status='fitting',completed_frames=frame+1,frames=spec['frames']))
                print(f'{output.name}: {frame+1}/{spec["frames"]}',flush=True)
    matrices,locals_out,parameters=map(np.array,(matrices,locals_out,parameters))
    evidence=audit(rig,spec,before,matrices,parameters,solver)
    document,binary=copy.deepcopy(rig.document),bytearray(rig.binary)
    nodes=set(fitter.nodes)|{spec['root_node']}
    # Include original animation tracks so every untouched joint keeps its clip.
    nodes.update(c['target']['node'] for c in document['animations'][0]['channels'])
    times=np.arange(spec['frames'],dtype=np.float32)/spec['fps'];time_acc=append_accessor(document,binary,times,'SCALAR')
    animation=dict(name='Strep_target_contact_candidate',channels=[],samplers=[])
    for node in sorted(nodes):
        prepare_animated_node(document,node)
        q=Rotation.from_matrix(locals_out[:,node,:3,:3]).as_quat()
        for frame in range(1,len(q)):
            if q[frame]@q[frame-1]<0:q[frame]*=-1
        for path,vals,kind in [('translation',locals_out[:,node,:3,3],'VEC3'),('rotation',q,'VEC4')]:
            acc=append_accessor(document,binary,vals,kind)
            animation['channels'].append(dict(sampler=len(animation['samplers']),target=dict(node=node,path=path)))
            animation['samplers'].append(dict(input=time_acc,output=acc,interpolation='LINEAR'))
    document['animations']=[animation]
    document.setdefault('extras',{})['strep_target_contact']=dict(source_glb_sha256=spec['glb_sha256'],spec_sha256=sha256(spec_path),numerical_screen_passed=evidence['numerical_screen_passed'],human_approved=False)
    write_glb(output/'character.glb',document,binary)
    decoded=RigAsset.load(output/'character.glb');matrix_error,vertex_error=0.,0.
    for frame,expected in enumerate(matrices):
        actual=sample_animation(decoded.document,decoded.binary,0,frame)
        matrix_error=max(matrix_error,float(np.max(np.abs(actual-expected))))
        vertex_error=max(vertex_error,float(np.linalg.norm(decoded.vertices(actual)-rig.vertices(expected),axis=1).max()))
    if max(matrix_error,vertex_error)>1e-5:raise ValueError('Corrected GLB roundtrip failed')
    np.savez_compressed(output/'target-transforms.npz',global_matrices=matrices,parameters=parameters,times_s=times)
    save(output/'solver.json',solver)
    save(output/'root-motion.json',dict(space='Target pelvis world transform after bounded correction, Y-up metres',times_s=times.tolist(),positions_m=matrices[:,spec['root_node'],:3,3].tolist(),rotations_xyzw=Rotation.from_matrix(matrices[:,spec['root_node'],:3,:3]).as_quat().tolist()))
    evidence.update(created_at=now(),source_glb_sha256=spec['glb_sha256'],contact_spec_sha256=sha256(spec_path),glb_sha256=sha256(output/'character.glb'),implementation_sha256=sha256(snapshot/'target_rig_contact.py'),
        roundtrip_max_matrix_error=matrix_error,roundtrip_max_vertex_error_m=vertex_error,frames=spec['frames'],fps=spec['fps'])
    save(output/'audit.json',evidence)
    save(output/'pipeline.json',dict(status='complete',completed_frames=spec['frames'],numerical_screen_passed=evidence['numerical_screen_passed']))
    print(evidence['after'],evidence['flags'],flush=True)
    return evidence


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);commands=parser.add_subparsers(dest='command',required=True)
    draft_parser=commands.add_parser('draft');draft_parser.add_argument('--transfer',type=Path,required=True);draft_parser.add_argument('--output',type=Path,required=True)
    solve=commands.add_parser('fit');solve.add_argument('--transfer',type=Path,required=True);solve.add_argument('--spec',type=Path,required=True);solve.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.command=='draft':draft(args.transfer,args.output)
    else:run(args.transfer,args.spec,args.output)
