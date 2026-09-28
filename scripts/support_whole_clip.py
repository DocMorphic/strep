"""Experimental combined support correction, starting directly from raw transfer."""
import copy
import shutil
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from threadpoolctl import threadpool_limits
from strep import read,save,sha256
from rig_asset import RigAsset
from target_rig_contact import baseline
from rig_contact_authoring import empty_spec
from rig_clearance_fit import foot_regions,native_heights
from breadth_contact_fit import support_guides
from support_reference_fit import SupportReferenceFitter
from support_clip_boundary import retain_end_support
from support_clip_start import retain_start_support
from relax_whole_support import relax
from rig_loop import encode
from build_soma_preview import ASSET


def run(source,output):
    source,output=Path(source).resolve(),Path(output).resolve()
    if output.exists():raise ValueError('Preserve earlier candidate')
    report=read(source/'report.json')
    if sha256(source/'character.glb')!=report['glb_sha256'] or sha256(report['source'])!=report['source_sha256']:
        raise ValueError('Changed source')
    output.mkdir(parents=True);shutil.copytree(source,output/'input')
    rig=RigAsset.load(source/'character.glb');before,local=baseline(rig,report['frames'])
    regions=foot_regions(rig,report['mapping']);surfaces=np.array([rig.vertices(w) for w in before])
    native=native_heights(dict(np.load(report['source'],allow_pickle=False)),dict(np.load(ASSET,allow_pickle=False)))
    targets={k:np.maximum(0,h*report['scale_from_mean_leg_lengths']+report['world_offset_m'][1]) for k,h in native.items()}
    spec=empty_spec(report);spec['patches']={k:dict(vertices=v.tolist()) for k,v in regions.items()}
    spec['contacts']=[];spec['max_nfev']=80
    spec['provenance']='Combined whole-clip correction with draft clip-boundary handling and root-curvature prior. Predicted contacts remain unconfirmed.'
    draft=support_guides(report,native,surfaces,regions)
    support=retain_start_support(retain_end_support(draft,len(before)),len(before))
    request=dict(method='whole_support_curvature_10',input_glb_sha256=report['glb_sha256'],native_motion_sha256=report['source_sha256'],
        native_skin_sha256=sha256(ASSET),targets_m={k:v.tolist() for k,v in targets.items()},
        raw_native_heights_m={k:v.tolist() for k,v in native.items()},support=support,support_weight=40.,max_sweeps=6,root_curvature_weight=10.,initialization='zero edits on raw transferred input',original_support_draft=draft,
        horizontal_reference_weight='30 * sqrt(1 - drafted_support_weight) / sqrt(patch_vertex_count)',human_approved=False)
    save(output/'request.json',request);save(output/'spec.json',spec)
    fitter=SupportReferenceFitter(rig,spec,local,targets,np.ones(len(before)),surfaces,guides=support['guides'],support_weight=40.)
    with threadpool_limits(limits=1):
        parameters,solver,convergence=relax(fitter,np.zeros((len(before),len(fitter.bounds))),curvature_weight=10.,sweeps=6,
            progress=lambda sweep,change:save(output/'pipeline.json',dict(status='fitting',sweep=sweep,max_parameter_change=change,quality_approved=False)))
    after=np.array([fitter.pose(f,x)[0] for f,x in enumerate(parameters)])
    dest=output/'candidate';dest.mkdir()
    animated={c['target']['node'] for c in rig.document['animations'][0]['channels']}|set(fitter.nodes)
    times,roundtrip=encode(rig,after,animated,report['root_node'],dest/'character.glb','Experimental combined whole-clip correction')
    for name in ['inventory.json','rig-profile.json','contacts.json']:shutil.copyfile(source/name,dest/name)
    root=report['root_node']
    save(dest/'root-motion.json',dict(node=root,times_s=times.tolist(),positions_m=after[:,root,:3,3].tolist(),
        rotations_xyzw=Rotation.from_matrix(after[:,root,:3,:3]).as_quat().tolist(),space='Corrected pelvis world track; no root extraction'))
    result=copy.deepcopy(report);result.update(glb_sha256=sha256(dest/'character.glb'),human_approved=False,
        correction_method='whole_support_curvature_10',parent_glb_sha256=report['glb_sha256'],target_mesh_floor_depth_max_m=roundtrip['floor_depth_max_m'])
    save(dest/'report.json',result)
    np.savez_compressed(output/'fit.npz',before=before,after=after,parameters=parameters)
    save(output/'solver.json',solver);save(output/'fit-summary.json',dict(convergence=convergence,export=roundtrip,quality_approved=False))
    save(output/'pipeline.json',dict(status='complete',quality_approved=False))
    return output
