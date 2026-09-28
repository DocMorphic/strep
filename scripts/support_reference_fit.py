"""Separate planted-support anchoring from preservation of original foot drift.

Experimental: the support labels are still model predictions. This changes
only horizontal reference weighting; pose/root budgets remain unchanged.
"""
import copy
from pathlib import Path
import shutil
import numpy as np
from scipy.spatial.transform import Rotation
from threadpoolctl import threadpool_limits
from breadth_contact_fit import SupportClearanceFitter, support_guides
from strep import read, save, sha256
from rig_asset import RigAsset
from target_rig_contact import baseline
from rig_contact_authoring import empty_spec
from rig_clearance_fit import foot_regions, native_heights
from rig_loop import encode
from build_soma_preview import ASSET


def reference_pair(positions, jacobian, reference, vertices, support_weight):
    if not np.isfinite(support_weight) or not 0 <= support_weight <= 1:
        raise ValueError('Support blend must be between zero and one')
    ids=np.asarray(vertices)
    scale=30.*np.sqrt(1-support_weight)/np.sqrt(len(ids))
    residual=((positions[ids][:,[0,2]]-reference[ids][:,[0,2]])*scale).ravel()
    derivative=(jacobian[ids][:,[0,2]]*scale).reshape(-1,jacobian.shape[-1])
    return residual, derivative


class SupportReferenceFitter(SupportClearanceFitter):
    def __init__(self,rig,spec,local,targets,envelope,horizontal_reference,**kwargs):
        self.unplanted_reference=np.asarray(horizontal_reference)
        super().__init__(rig,spec,local,targets,envelope,None,**kwargs)

    def objective_from_surface(self,frame,values,neighbors,positions,full_jac):
        residual,derivative=super().objective_from_surface(frame,values,neighbors,positions,full_jac)
        extra=[reference_pair(positions,full_jac,self.unplanted_reference[frame],patch['vertices'],
                              self.support_guides[side]['weights'][frame]) for side,patch in self.spec['patches'].items()]
        return np.concatenate([residual,*[r for r,j in extra]]),np.vstack([derivative,*[j for r,j in extra]])


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
    spec['provenance']='Development support/reference weighting comparison; predicted contacts are not confirmed annotations.'
    support=support_guides(report,native,surfaces,regions)
    request=dict(method='support_reference',input_glb_sha256=report['glb_sha256'],native_motion_sha256=report['source_sha256'],
        native_skin_sha256=sha256(ASSET),targets_m={k:v.tolist() for k,v in targets.items()},
        raw_native_heights_m={k:v.tolist() for k,v in native.items()},support=support,support_weight=40.,max_sweeps=6,
        horizontal_reference_weight='30 * sqrt(1 - drafted_support_weight) / sqrt(patch_vertex_count)',human_approved=False)
    save(output/'request.json',request);save(output/'spec.json',spec)
    fitter=SupportReferenceFitter(rig,spec,local,targets,np.ones(len(before)),surfaces,guides=support['guides'],support_weight=40.)
    with threadpool_limits(limits=1):parameters,solver,convergence=fitter.solve(output,max_sweeps=6)
    after=np.array([fitter.pose(f,x)[0] for f,x in enumerate(parameters)])
    dest=output/'candidate';dest.mkdir()
    animated={c['target']['node'] for c in rig.document['animations'][0]['channels']}|set(fitter.nodes)
    times,roundtrip=encode(rig,after,animated,report['root_node'],dest/'character.glb','Experimental support/reference correction')
    for name in ['inventory.json','rig-profile.json','contacts.json']:shutil.copyfile(source/name,dest/name)
    root=report['root_node']
    save(dest/'root-motion.json',dict(node=root,times_s=times.tolist(),positions_m=after[:,root,:3,3].tolist(),
        rotations_xyzw=Rotation.from_matrix(after[:,root,:3,:3]).as_quat().tolist(),space='Corrected pelvis world track; no root extraction'))
    result=copy.deepcopy(report);result.update(glb_sha256=sha256(dest/'character.glb'),human_approved=False,
        correction_method='support_reference',parent_glb_sha256=report['glb_sha256'],target_mesh_floor_depth_max_m=roundtrip['floor_depth_max_m'])
    save(dest/'report.json',result)
    np.savez_compressed(output/'fit.npz',before=before,after=after,parameters=parameters)
    save(output/'solver.json',solver);save(output/'fit-summary.json',dict(convergence=convergence,export=roundtrip,quality_approved=False))
    save(output/'pipeline.json',dict(status='complete',quality_approved=False))
    return output
