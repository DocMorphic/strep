"""Read-only skin-influence and posed-box drafts for arbitrary contact regions.

Bone weights describe deformation ownership, never anatomical contact truth.
"""
import math
from pathlib import Path
import numpy as np
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from strep import sha256

SCHEMA='strep-rig-patch-selection-v1'
LIMIT=256


def select(rig,world,node,include_children,minimum_weight,box_world_m=None):
    if type(node) is not int or node not in rig.joints:raise ValueError('Choose a skin bone')
    if type(include_children) is not bool:raise ValueError('Child-bone selection must be explicit')
    if type(minimum_weight) not in (int,float) or not math.isfinite(minimum_weight) or not 0<minimum_weight<=1:
        raise ValueError('Minimum bone influence must be within (0, 1]')
    if box_world_m is not None:
        if type(box_world_m) is not dict or set(box_world_m)!={'min','max'}:raise ValueError('Box needs min/max XYZ coordinates')
        for value in box_world_m.values():
            if type(value) is not list or len(value)!=3 or any(type(x) not in (int,float) or not math.isfinite(x) for x in value):
                raise ValueError('Box needs finite XYZ coordinates')
        if any(a>b for a,b in zip(box_world_m['min'],box_world_m['max'])):raise ValueError('Box minimum exceeds maximum')
    selected={node}
    if include_children:
        for joint in rig.joints:
            parent=joint
            while parent>=0 and parent!=node:parent=rig.parents[parent]
            if parent==node:selected.add(joint)
    slots=[i for i,joint in enumerate(rig.joints) if joint in selected]
    points=rig.vertices(world);ids=[];offset=0
    for primitive in rig.primitives:
        count=len(primitive['positions'])
        if primitive['joints'] is not None:
            weight=np.where(np.isin(primitive['joints'],slots),primitive['weights'],0).sum(axis=1)
            mask=weight>=minimum_weight
            if box_world_m is not None:
                posed=points[offset:offset+count]
                mask&=np.all((posed>=box_world_m['min'])&(posed<=box_world_m['max']),axis=1)
            ids.extend((offset+np.flatnonzero(mask)).tolist())
        offset+=count
    bounds=None if not ids else dict(min=points[ids].min(axis=0).tolist(),max=points[ids].max(axis=0).tolist())
    return dict(selected_nodes=sorted(selected),matched_count=len(ids),vertex_count=len(points),
        vertices=ids if len(ids)<=LIMIT else [],bounds_world_m=bounds,selection_limit=LIMIT,
        can_apply=0<len(ids)<=LIMIT,requires_review=True,anatomy_verified=False,quality_approved=False)


def inspect_request(payload):
    from rig_contact_authoring import source
    required={'schema','source_job','variant','glb_sha256','frame','node','include_children','minimum_weight','box_world_m'}
    if type(payload) is not dict or set(payload)!=required or payload['schema']!=SCHEMA:
        raise ValueError('Explicit source-bound bone-region selection required')
    _,_,_,report,glb=source(payload['source_job'],payload['variant'])
    digest=sha256(glb)
    if payload['glb_sha256']!=digest:raise ValueError('Bone-region source version changed')
    frame=payload['frame']
    if type(frame) not in (int,float) or not math.isfinite(frame) or not 0<=frame<=report['frames']-1:
        raise ValueError('Choose a frame inside the selected clip')
    rig=RigAsset.load(glb);sampler=AnimationSampler(rig.document,rig.binary,0)
    world=sampler.sample(float(np.float32(frame/report['fps'])))
    result=select(rig,world,payload['node'],payload['include_children'],payload['minimum_weight'],payload['box_world_m'])
    if sha256(glb)!=digest:raise ValueError('Bone-region source changed during inspection')
    return dict(result,schema=SCHEMA,selector=dict(payload),method_sha256=sha256(Path(__file__)),
        scope='Skin deformation ownership and optional posed world-space box. No anatomical surface, support schedule, solver feasibility or motion-quality approval.')
