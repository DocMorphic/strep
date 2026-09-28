"""Unapproved support-aware surface correction of a complete rig transfer."""
import copy
import shutil
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from threadpoolctl import threadpool_limits
from strep import read, save, sha256
from rig_asset import RigAsset
from target_rig_contact import baseline
from rig_contact_authoring import empty_spec
from rig_contact_tracks import signals
from rig_clearance_fit import ClearanceFitter, foot_regions, native_heights
from rig_loop import encode
from build_soma_preview import ASSET


def support_guides(report, native, surfaces, regions):
    """Conservative candidate intervals, not authored/confirmed contacts.

    Retain model foot/toe support only while native foot surface is within
    30mm of the floor. Require four frames; fade the penalty at both edges.
    Horizontal anchors are the median first three target surface centroids.
    No scene or physical support is inferred for other motion contexts.
    """
    masks, origin = signals(report)
    guides = {}; intervals = []
    for side, ids in regions.items():
        native_height = np.asarray(native[side])
        active = (masks[side+'Foot'] | masks[side+'ToeBase']) & (np.abs(native_height) <= .03)
        centroid = surfaces[:, ids][:, :, [0, 2]].mean(axis=1)
        anchors = centroid.copy(); weights = np.zeros(len(active))
        changes = np.diff(np.r_[False, active, False].astype(int))
        for a, b in zip(np.flatnonzero(changes == 1), np.flatnonzero(changes == -1)):
            if b-a < 4:
                continue
            anchors[a:b] = np.median(centroid[a:a+3], axis=0)
            phase = np.minimum(np.arange(1, b-a+1), np.arange(b-a, 0, -1)) / 3
            weights[a:b] = np.sin(np.minimum(phase, 1)*np.pi/2)**2
            intervals.append(dict(side=side, start_frame=int(a), end_frame_exclusive=int(b),
                                  anchor_xz_m=anchors[a].tolist()))
        guides[side] = dict(anchors_xz_m=anchors.tolist(), weights=weights.tolist())
    return dict(origin=origin, confirmed=False, intervals=intervals, guides=guides,
                native_height_gate_m=.03, minimum_frames=4, edge_fade_frames=3,
                limitations='Predicted support may be wrong. Foot-region centroid is not an anatomical sole contact point; pivot/rolling support may legitimately move.')


class SupportClearanceFitter(ClearanceFitter):
    def __init__(self, *args, guides, support_weight, **kwargs):
        super().__init__(*args, **kwargs)
        if not np.isfinite(support_weight) or support_weight < 0:
            raise ValueError('Invalid support weight')
        self.support_weight = support_weight
        self.support_guides = guides
        for side in self.spec['patches']:
            g = guides[side]
            a, w = np.asarray(g['anchors_xz_m']), np.asarray(g['weights'])
            if a.shape != (len(self.local), 2) or w.shape != (len(self.local),) or not np.isfinite(a).all() or not np.isfinite(w).all() or np.any((w<0)|(w>1)):
                raise ValueError('Invalid support guide')

    def objective_pair(self, frame, values, neighbors):
        positions, jac = self.surface_jacobian(frame, values)
        residual, derivative = self.objective_from_surface(frame, values, neighbors, positions, jac)
        extra, derivatives = [], []
        for side, patch in self.spec['patches'].items():
            guide = self.support_guides[side]
            scale = self.support_weight * np.sqrt(guide['weights'][frame])
            ids = patch['vertices']
            extra.append((positions[ids][:, [0,2]].mean(axis=0)-guide['anchors_xz_m'][frame])*scale)
            derivatives.append(jac[ids][:, [0,2]].mean(axis=0)*scale)
        return np.r_[residual, np.concatenate(extra)], np.vstack([derivative, *derivatives])


def run(source, output, method):
    if method not in ('clearance', 'support'):
        raise ValueError('Unknown comparison method')
    source, output = Path(source).resolve(), Path(output).resolve()
    if output.exists():
        raise ValueError('Preserve earlier candidate attempts')
    report = read(source/'report.json')
    if sha256(source/'character.glb') != report['glb_sha256'] or sha256(report['source']) != report['source_sha256']:
        raise ValueError('Changed input transfer or native motion')
    output.mkdir(parents=True)
    shutil.copytree(source, output/'input')
    rig = RigAsset.load(source/'character.glb'); before, local = baseline(rig, report['frames'])
    regions = foot_regions(rig, report['mapping'])
    surfaces = np.array([rig.vertices(w) for w in before])
    native = native_heights(dict(np.load(report['source'], allow_pickle=False)), dict(np.load(ASSET, allow_pickle=False)))
    targets = {k: np.maximum(0, h*report['scale_from_mean_leg_lengths']+report['world_offset_m'][1]) for k,h in native.items()}
    spec = empty_spec(report); spec['patches'] = {k:dict(vertices=v.tolist()) for k,v in regions.items()}
    spec['contacts'] = []; spec['max_nfev'] = 80
    spec['provenance'] = 'Full-clip development correction. Surface-height correspondence and optional predicted support drift penalty; not confirmed contacts.'
    support = support_guides(report, native, surfaces, regions)
    request = dict(method=method, input_glb_sha256=report['glb_sha256'], native_motion_sha256=report['source_sha256'],
                   native_skin_sha256=sha256(ASSET), targets_m={k:v.tolist() for k,v in targets.items()},
                   raw_native_heights_m={k:v.tolist() for k,v in native.items()}, support=support,
                   support_weight=40. if method=='support' else 0., max_sweeps=6, human_approved=False)
    save(output/'request.json', request); save(output/'spec.json', spec)
    fitter = SupportClearanceFitter(rig, spec, local, targets, np.ones(len(before)), surfaces,
                                   guides=support['guides'], support_weight=request['support_weight'])
    with threadpool_limits(limits=1):
        parameters, solver, convergence = fitter.solve(output, max_sweeps=request['max_sweeps'])
    after = np.array([fitter.pose(f, x)[0] for f,x in enumerate(parameters)])
    dest = output/'candidate'; dest.mkdir()
    animated = {c['target']['node'] for c in rig.document['animations'][0]['channels']} | set(fitter.nodes)
    times, roundtrip = encode(rig, after, animated, report['root_node'], dest/'character.glb', 'Experimental '+method+' correction')
    for name in ('inventory.json','rig-profile.json','contacts.json'):
        shutil.copyfile(source/name, dest/name)
    root = report['root_node']
    save(dest/'root-motion.json', dict(node=root, times_s=times.tolist(), positions_m=after[:,root,:3,3].tolist(),
        rotations_xyzw=Rotation.from_matrix(after[:,root,:3,:3]).as_quat().tolist(),
        space='Corrected pelvis world track; no root extraction'))
    result = copy.deepcopy(report)
    result.update(glb_sha256=sha256(dest/'character.glb'), human_approved=False,
                  correction_method=method, parent_glb_sha256=report['glb_sha256'],
                  target_mesh_floor_depth_max_m=roundtrip['floor_depth_max_m'])
    save(dest/'report.json', result)
    np.savez_compressed(output/'fit.npz', before=before, after=after, parameters=parameters)
    save(output/'solver.json', solver)
    save(output/'fit-summary.json', dict(convergence=convergence, export=roundtrip, quality_approved=False))
    save(output/'pipeline.json', dict(status='complete', quality_approved=False))
    return output
