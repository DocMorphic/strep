"""Explicit, audited input version for static near-unit scale roundoff only."""
import argparse,copy,shutil
from pathlib import Path
import numpy as np
from strep import ROOT,sha256,save,now
from rig_asset import RigAsset
from native_support_clock import NativeSupportSampler
from native_engine_clock import audit_clock
from gltf_tools import write_glb,local_matrix

STATIC_SCALE_ROUNDOFF=5e-7
GEOMETRY_CHANGE_LIMIT_M=1e-5
SOURCE_DIR=Path(__file__).resolve().parent


def normalized_document(rig,reader):
    """Static eligibility only; full sampled geometry is checked by prepare."""
    if reader.scale_key_drift or any(p=='scale' and np.any(v!=1.) for _,p,_,v,_ in reader.channels):
        raise ValueError('Animated scale cannot be normalized by static input preparation')
    document=copy.deepcopy(rig.document);changes=[]
    for i,node in enumerate(document['nodes']):
        if 'matrix' in node:
            matrix=local_matrix(node)[:3,:3]
            if not np.allclose(matrix.T@matrix,np.eye(3),atol=1e-10,rtol=0):
                raise ValueError('Matrix scale/shear cannot be normalized by static input preparation')
        if 'scale' not in node:continue
        scale=np.asarray(node['scale'],float)
        if np.max(abs(scale-1))>STATIC_SCALE_ROUNDOFF:raise ValueError('Static scale exceeds roundoff preparation limit')
        if np.any(scale!=1.):
            changes.append(dict(node=i,name=node.get('name'),original_scale=scale.tolist(),prepared_scale=[1.,1.,1.]))
            node['scale']=[1.,1.,1.]
    return document,changes


def assessment(rig,reader):
    try:
        _,changes=normalized_document(rig,reader)
        return dict(eligible=True,static_node_changes=len(changes),geometry_check_pending=True,
            maximum_geometry_change_m=GEOMETRY_CHANGE_LIMIT_M)
    except ValueError as exc:
        return dict(eligible=False,static_node_changes=None,geometry_check_pending=False,reason=str(exc))


def prepare(source,output):
    source,output=Path(source).resolve(),Path(output).resolve()
    if output.exists() or output.parent!=ROOT/'reports':raise ValueError('Fresh immediate reports output required')
    names=('native_support_rigid_input.py','rig_asset.py','native_support_clock.py','rig_clip_import.py','native_engine_clock.py','gltf_tools.py','strep.py')
    methods={n:sha256(SOURCE_DIR/n) for n in names}
    digest=sha256(source);rig=RigAsset.load(source)
    if len(rig.document.get('animations',[]))!=1:raise ValueError('One chosen native animation required')
    reader=NativeSupportSampler(rig.document,rig.binary,0)
    document,changes=normalized_document(rig,reader)
    normalized=RigAsset(document,rig.binary);current=NativeSupportSampler(document,rig.binary,0)
    times=audit_clock(reader.duration,[c[2] for c in reader.channels],[],0.)
    diagnostics=[]
    for time in [None,*times.tolist()]:
        a=rig.reference if time is None else reader.sample(float(time))
        b=normalized.reference if time is None else current.sample(float(time))
        rotations=b[:,:3,:3]
        if not np.allclose(rotations.transpose(0,2,1)@rotations,np.eye(3),atol=1e-7,rtol=0) or not np.allclose(np.linalg.det(rotations),1.,atol=1e-7,rtol=0):
            raise ValueError('Prepared input does not satisfy unchanged rigid transform limits')
        delta=normalized.vertices(b)-rig.vertices(a)
        diagnostics.append(dict(time_s=time,maximum_vertex_distance_m=float(np.linalg.norm(delta,axis=1).max()),
            maximum_bone_position_distance_m=float(np.linalg.norm(b[:,:3,3]-a[:,:3,3],axis=1).max()),
            maximum_basis_element_change=float(abs(b[:,:3,:3]-a[:,:3,:3]).max())))
    maximum=max(d['maximum_vertex_distance_m'] for d in diagnostics)
    if maximum>GEOMETRY_CHANGE_LIMIT_M:raise ValueError('Prepared input exceeds geometry change budget')
    if sha256(source)!=digest:raise ValueError('Source changed during rigid input preparation')
    for n,h in methods.items():
        if sha256(SOURCE_DIR/n)!=h:raise ValueError('Preparation implementation changed')
    output.mkdir();archive=output/'implementation';archive.mkdir()
    for n in names:shutil.copyfile(SOURCE_DIR/n,archive/n)
    save(output/'request.json',dict(at=now(),inputs={str(source):digest},implementation=methods,
        static_scale_roundoff_limit=STATIC_SCALE_ROUNDOFF,maximum_geometry_change_m=GEOMETRY_CHANGE_LIMIT_M,
        scope='Explicit new input version; static near-unit TRS scales only. Original motion and failed fitting evidence remain immutable. No solver gate, geometry, inverse bind or animation-key tolerance is widened.'))
    shutil.copyfile(source,output/'input.glb');write_glb(output/'prepared.glb',document,rig.binary)
    exported=RigAsset.load(output/'prepared.glb')
    assert exported.binary==rig.binary and exported.document['meshes']==rig.document['meshes'] and exported.document['skins']==rig.document['skins'] and exported.document['animations']==rig.document['animations']
    save(output/'comparison.json',dict(changes=changes,samples=diagnostics,maximum_vertex_distance_m=maximum,
        inverse_binds_preserved=True,mesh_data_preserved=True,native_animation_bytes_preserved=True,quality_approved=False))
    for n,h in methods.items():
        if sha256(SOURCE_DIR/n)!=h or sha256(archive/n)!=h:raise ValueError('Preparation implementation changed')
    if sha256(source)!=digest:raise ValueError('Source changed during rigid input preparation')
    outputs={p.name:sha256(p) for p in output.iterdir() if p.is_file()}
    result=dict(at=now(),status='complete',changes=len(changes),sampled_poses=len(times),maximum_vertex_distance_m=maximum,
        source_sha256=digest,prepared_sha256=sha256(output/'prepared.glb'),outputs=outputs,quality_approved=False)
    save(output/'result.json',result);return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('source',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args();print(prepare(args.source,args.output))
