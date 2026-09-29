"""Measure inferred source-support drift on decoded exports, without approval."""
import argparse
from pathlib import Path
import numpy as np
from strep import ROOT, read, save, sha256
from build_soma_preview import ASSET
from floor_contact import Surface
from gltf_tools import read_glb
from rig_clip_import import AnimationSampler
from support_contact_v5 import infer_support, CONFIG
from support_contact_v8 import select_inferred_supports
from contact_spec import apply_overrides

TOLERANCE_M = .005


def sample_target(contact, frame):
    """Do not invent a material-point track across a changing inferred vertex."""
    a, b = int(np.floor(frame)), int(np.ceil(frame))
    if not contact['active'][a] or not contact['active'][b]:
        return None, 'outside_active_interval'
    if contact['vertex_ids'][a] != contact['vertex_ids'][b]:
        return None, 'vertex_identity_changes'
    t = frame-a
    return (int(contact['vertex_ids'][a]), (1-t)*contact['targets'][a]+t*contact['targets'][b]), None


def summarize(rows, skipped):
    failures = sum(row['error_m'] > TOLERANCE_M for row in rows)
    coverage_gaps = sum(row['reason'] == 'vertex_identity_changes' for row in skipped)
    return dict(samples=len(rows), failures=failures,
                maximum_error_m=max((row['error_m'] for row in rows), default=None),
                vertex_identity_gaps=coverage_gaps,
                sampled_point_preservation_passed=bool(rows) and failures == 0 and coverage_gaps == 0)


def run(study, output, regions=None):
    study, output = Path(study).resolve(), Path(output).resolve()
    if output.exists():raise ValueError('Fresh support audit output required')
    protocol, result = read(study/'protocol.json'), read(study/'result.json')
    if result['status'] != 'complete':raise ValueError('Completed fit required')
    for file, key in [('protocol.json','protocol_sha256'), ('recipe.json','recipe_sha256'),
                      ('source.glb','source_glb_sha256'), ('candidate.glb','candidate_glb_sha256'),
                      ('authored-scene.json','authored_scene_sha256'), ('motion.npz','candidate_sha256')]:
        if sha256(study/file) != result[key]:raise ValueError('Changed artifact: '+file)
    for path, digest in protocol['inputs'].items():
        if sha256(path) != digest:raise ValueError('Changed study input')
    for file in ['support_contact_v5.py','contact_spec.py','floor_contact.py']:
        if sha256(ROOT/'scripts'/file) != protocol['implementation'][file]:
            raise ValueError('Support inference implementation changed')
    recipe, scene = read(study/'recipe.json'), read(study/'authored-scene.json')
    source_path=ROOT/scene['actors'][protocol['actor']]['motion']
    if sha256(source_path) != sha256(study/'source-motion.npz'):raise ValueError('Changed source copy')
    if protocol['inputs'].get(str(ASSET)) != sha256(ASSET):raise ValueError('Study mesh not bound')
    source=dict(np.load(source_path,allow_pickle=False));skin=dict(np.load(ASSET,allow_pickle=False))
    contacts=infer_support(source,skin)
    if recipe['contact_spec'] is not None:
        contacts=apply_overrides(contacts,source,skin,recipe['contact_spec'],CONFIG['fade_frames'],CONFIG['clearance_m'])
    regions=list(protocol.get('preserve_support_regions',[]) if regions is None else regions)
    if not regions:raise ValueError('Select support regions for measurement')
    select_inferred_supports(contacts,regions)
    surface=Surface(skin);frames=len(source['root_positions']);variants={}
    for label in ['source','candidate']:
        doc,binary=read_glb(study/(label+'.glb'));sampler=AnimationSampler(doc,binary,0);joints=doc['skins'][0]['joints']
        if [doc['nodes'][j]['name'] for j in joints] != list(map(str,skin['rig_joint_names'])):raise ValueError('Rig mismatch')
        if abs(sampler.duration-(frames-1)/30)>1e-5:raise ValueError('Duration mismatch')
        rows=[];skipped=[]
        for frame in np.arange((frames-1)*4+1)/4:
            matrices=sampler.sample(frame/30)[joints]
            for name in regions:
                sample,reason=sample_target(contacts[name],frame)
                if sample is None:
                    skipped.append(dict(region=name,frame=float(frame),reason=reason));continue
                vertex,target=sample
                point=surface.vertices(matrices[:,:3,:3],matrices[:,:3,3],np.array([vertex]))[0]
                rows.append(dict(region=name,frame=float(frame),vertex=vertex,target_m=target.tolist(),
                                 position_m=point.tolist(),error_m=float(np.linalg.norm(point-target))))
        variants[label]=dict(**summarize(rows,skipped),rows=rows,skipped=skipped)
    report=dict(result_sha256=sha256(study/'result.json'),auditor_sha256=sha256(__file__),
                source_motion_sha256=sha256(source_path),mesh_sha256=sha256(ASSET),regions=regions,
                requested_by_fit=protocol.get('preserve_support_regions',[]),tolerance_m=TOLERANCE_M,
                variants=variants,quality_approved=False,
                scope='120 Hz decoded actor-native source-support point drift. Inferred low/slow intervals are hypotheses; changing vertex identities are coverage gaps. No sole-orientation, force, balance, semantic or motion-quality approval.')
    save(output,report)
    print({name:{key:value for key,value in row.items() if key not in ['rows','skipped']} for name,row in variants.items()},flush=True)
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('study',type=Path);parser.add_argument('output',type=Path)
    parser.add_argument('--region',action='append')
    args=parser.parse_args();run(args.study,args.output,args.region)
