"""Reference-relative humanoid motion reflection, without reflecting the mesh.

An explicit involutive hierarchy map swaps counterpart motion. Each destination
keeps its own reference proportions and bone axes, including asymmetric rigs.
"""
import copy
import numpy as np
from rig_transition import localize, compose
from rig_loop import encode
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from scipy.spatial.transform import Rotation
from strep import read, save, sha256, now


def descendants(parents, root):
    found=[]
    for node in range(len(parents)):
        ancestor=node
        while ancestor>=0 and ancestor!=root: ancestor=parents[ancestor]
        if ancestor==root: found.append(node)
    return found


def correspondence(rig, root, pairs):
    if type(root) is not int or root not in rig.joints:
        raise ValueError('Choose a skin root')
    nodes=descendants(rig.parents,root)
    if not isinstance(pairs,dict) or set(pairs)!={str(n) for n in nodes}:
        raise ValueError('Explicit correspondence required for every root descendant')
    partner={int(n):v for n,v in pairs.items()}
    if any(type(v) is not int or v not in nodes for v in partner.values()):
        raise ValueError('Counterpart must be a node in the same subtree')
    if partner[root]!=root or any(partner[partner[n]]!=n for n in nodes):
        raise ValueError('Correspondence must be involutive with a fixed root')
    for n in nodes:
        if n!=root and partner[rig.parents[n]]!=rig.parents[partner[n]]:
            raise ValueError('Counterpart hierarchy mismatch at node '+str(n))
        if (n in rig.joints)!=(partner[n] in rig.joints):
            raise ValueError('Skin joints must map to skin joints')
    return partner


def draft_correspondence(rig, mapping):
    """Explicit saved roles plus exact side-name matches; hierarchy validates it.

    Returned map is a reviewable draft, not inferred anatomical ground truth.
    Unmatched descendants are self-mapped; incompatible branches reject early.
    """
    root=mapping['Hips'];nodes=descendants(rig.parents,root)
    names={}
    for n in nodes:
        name=rig.document['nodes'][n].get('name','')
        if name in names: raise ValueError('Ambiguous names need an explicit correspondence')
        names[name]=n
    pairs={str(n):n for n in nodes}
    # Saved roles are explicit correspondence, and take precedence over labels
    # such as Cesium's asymmetric L__4_/R bone names.
    for role,node in mapping.items():
        opposite='Right'+role[4:] if role.startswith('Left') else 'Left'+role[5:] if role.startswith('Right') else role
        if opposite not in mapping:raise ValueError('Missing mapped counterpart: '+role)
        pairs[str(node)]=mapping[opposite]
    for name,n in names.items():
        if n in mapping.values():continue
        candidate=None
        for left,right in [('Left','Right'),('_l','_r'),('_L','_R'),('.L','.R')]:
            if left=='Left':
                if name.startswith(left):candidate=right+name[len(left):]
                elif name.startswith(right):candidate=left+name[len(right):]
            elif name.endswith(left):candidate=name[:-len(left)]+right
            elif name.endswith(right):candidate=name[:-len(right)]+left
            if candidate is not None:break
        if candidate is not None:
            if candidate not in names:raise ValueError('Missing side counterpart: '+name)
            pairs[str(n)]=names[candidate]
    correspondence(rig,root,pairs)
    return pairs


def reflection(normal, point):
    normal=np.asarray(normal,dtype=float);point=np.asarray(point,dtype=float)
    if normal.shape!=(3,) or point.shape!=(3,) or not np.isfinite(normal).all() or not np.isfinite(point).all():
        raise ValueError('Finite plane normal and point required')
    if abs(np.linalg.norm(normal)-1)>1e-8 or abs(normal[1])>1e-8:
        raise ValueError('Use a unit horizontal normal for a vertical mirror plane')
    return np.eye(3)-2*np.outer(normal,normal),point


def rigid(value):
    """Project accepted nominal unit-scale float drift, never actual scaled rigs."""
    value=np.asarray(value,dtype=float)
    if not np.isfinite(value).all() or not np.allclose(value[...,3,:],[0,0,0,1],atol=1e-8,rtol=0):
        raise ValueError('Finite affine transforms required')
    rotations=value[...,:3,:3]
    if not np.allclose(rotations@rotations.swapaxes(-1,-2),np.eye(3),atol=1e-5,rtol=0) or not np.allclose(np.linalg.det(rotations),1,atol=1e-5,rtol=0):
        raise ValueError('Rigid unit-scale transforms required')
    result=value.copy()
    result[...,:3,:3]=Rotation.from_matrix(rotations.reshape(-1,3,3)).as_matrix().reshape(rotations.shape)
    return result


def mirror(rig, world, root, pairs, normal, point):
    partner=correspondence(rig,root,pairs);F,point=reflection(normal,point)
    world=np.asarray(world,dtype=float)
    if world.ndim!=4 or world.shape[1:]!=(len(rig.parents),4,4) or not np.isfinite(world).all():
        raise ValueError('Finite full-node world transforms required')
    world=rigid(world);bind=rigid(rig.reference)
    local=localize(world,rig.parents);reference=localize(bind[None],rig.parents)[0]
    result=local.copy();rotations=world[...,:3,:3].copy()
    # A reflected rotation delta remains proper: det(F R F)=+1.
    for dst,src in partner.items():
        rotations[:,dst]=F@world[:,src,:3,:3]@bind[src,:3,:3].T@F@bind[dst,:3,:3]
    for dst,src in partner.items():
        parent=rig.parents[dst];source_parent=rig.parents[src]
        result[:,dst,:3,:3]=rotations[:,dst] if parent<0 else rotations[:,parent].swapaxes(-1,-2)@rotations[:,dst]
        if dst==root:continue
        A=bind[parent,:3,:3].T@F@bind[source_parent,:3,:3]
        result[:,dst,:3,3]=reference[dst,:3,3]+np.einsum('ij,fj->fi',A,local[:,src,:3,3]-reference[src,:3,3])
    position=point+np.einsum('ij,fj->fi',F,world[:,root,:3,3]-point)
    parent=rig.parents[root]
    result[:,root,:3,3]=position if parent<0 else np.einsum('fij,fj->fi',world[:,parent,:3,:3].swapaxes(-1,-2),position-world[:,parent,:3,3])
    return compose(result,rig.parents)


def swapped_role(name):
    if not isinstance(name,str):raise ValueError('Contact role must be text')
    return 'Right'+name[4:] if name.startswith('Left') else 'Left'+name[5:] if name.startswith('Right') else name


def annotations(contacts, events, frames, partner, source_hash):
    """Keep role-to-node identity; swap interval roles and invalidate intent."""
    mapped_contacts=copy.deepcopy(contacts)
    if not isinstance(contacts,dict) or not isinstance(contacts.get('mapping'),dict) or not isinstance(contacts.get('intervals'),list):
        raise ValueError('Contacts require mapping and intervals')
    mapping=contacts['mapping']
    for role,node in mapping.items():
        opposite=swapped_role(role)
        if opposite not in mapping or (node is not None and (type(node) is not int or node not in partner or mapping[opposite]!=partner[node])) or (node is None and mapping[opposite] is not None):
            raise ValueError('Contact roles disagree with counterpart nodes')
    for interval in mapped_contacts['intervals']:
        a,b=interval.get('start_frame'),interval.get('end_frame_exclusive')
        if type(a) is not int or type(b) is not int or not 0<=a<b<=frames or interval.get('joint') not in mapping:
            raise ValueError('Contact interval must use a mapped role and this clip clock')
        for key,expected in [('start_seconds',a/30),('end_seconds_exclusive',b/30)]:
            if key in interval and (type(interval[key]) not in (int,float) or not np.isfinite(interval[key]) or abs(interval[key]-expected)>1e-6):
                raise ValueError('Contact seconds disagree with frames')
        # Unknown node/point/mesh fields cannot be safely mirrored as predictions.
        if set(interval)-{'joint','start_frame','end_frame_exclusive','start_seconds','end_seconds_exclusive','provenance','requires_review'}:
            raise ValueError('Mirror accepts role prediction intervals only; preserve authored targets separately')
        interval['joint']=swapped_role(interval['joint']);interval['requires_review']=True
    mapped_contacts.update(provenance='Side-role labels swapped; source timing retained. Predictions are not confirmed mesh contact.',quality_approved=False)
    mapped_events=copy.deepcopy(events)
    if not isinstance(events,dict) or events.get('fps',30)!=30 or not isinstance(events.get('events'),list):
        raise ValueError('Events require the same 30fps clip clock')
    for event in mapped_events['events']:
        f=event.get('frame')
        if type(f) is not int or not 0<=f<frames or not isinstance(event.get('lineage',[]),list):
            raise ValueError('Event must lie inside the clip')
        if 'time_s' in event and (type(event['time_s']) not in (int,float) or not np.isfinite(event['time_s']) or abs(event['time_s']-f/30)>1e-6):
            raise ValueError('Event time disagrees with frame')
        event['requires_review']=True
        event['lineage']=event.get('lineage',[])+[dict(operation='mirror_motion',source_glb_sha256=source_hash,reason='Timing unchanged; free-text name, sidedness and scene intent require review')]
    return mapped_contacts,mapped_events


def validate_recipe(source, recipe):
    required={'schema','source_sha256','frames','fps','root_node','counterparts','plane_normal','plane_point','label'}
    if not isinstance(recipe,dict) or set(recipe)!=required or recipe['schema']!='strep-rig-mirror-v1' or recipe['source_sha256']!=sha256(source):
        raise ValueError('Mirror recipe must bind the selected source')
    frames=recipe['frames']
    if type(frames) is not int or not 2<=frames<=901 or recipe['fps']!=30:
        raise ValueError('Finite 30fps clip of 2–901 frames required')
    if not isinstance(recipe['label'],str) or not 1<=len(recipe['label'])<=160:raise ValueError('Name the mirrored clip')
    rig=RigAsset.load(source);clock=AnimationSampler(rig.document,rig.binary,0)
    if len(rig.document['animations'])!=1 or abs(clock.duration-(frames-1)/30)>1e-5:
        raise ValueError('Select a single sampled animation with the exact recipe duration')
    correspondence(rig,recipe['root_node'],recipe['counterparts'])
    reflection(recipe['plane_normal'],recipe['plane_point'])
    return rig,clock


def write_clip(source, recipe, output, contacts=None, events=None):
    """Standalone finite export; active mesh targets need explicit re-authoring."""
    from pathlib import Path
    import shutil
    source,output=Path(source),Path(output)
    if output.exists():raise ValueError('Preserve earlier exports')
    rig,clock=validate_recipe(source,recipe);frames=recipe['frames']
    times=np.arange(frames,dtype=np.float32)/30
    world=np.array([clock.sample(float(t)) for t in times])
    root=recipe['root_node'];pairs=recipe['counterparts']
    original_contacts=read(contacts) if contacts is not None else dict(mapping={},intervals=[])
    original_events=read(events) if events is not None else dict(fps=30,events=[])
    mapped_contacts,mapped_events=annotations(original_contacts,original_events,frames,correspondence(rig,root,pairs),sha256(source))
    args=(root,pairs,recipe['plane_normal'],recipe['plane_point'])
    mirrored=mirror(rig,world,*args);twice=mirror(rig,mirrored,*args)
    error=float(np.abs(twice-rigid(world)).max())
    if error>1e-8:raise ValueError('Mirror involution verification failed')
    output.mkdir(parents=True);shutil.copyfile(source,output/'source.glb');save(output/'recipe.json',recipe)
    nodes=set(correspondence(rig,root,pairs));animated={c[0] for c in clock.channels}|nodes
    _,check=encode(rig,mirrored,animated,root,output/'character.glb',recipe['label'])
    save(output/'root-motion.json',dict(node=root,times_s=times.tolist(),positions_m=mirrored[:,root,:3,3].tolist(),
        rotations_xyzw=Rotation.from_matrix(mirrored[:,root,:3,:3]).as_quat().tolist(),space='Mapped pelvis world transform, reflected in the explicit fixed plane'))
    if contacts is not None:save(output/'source-contacts.json',original_contacts)
    if events is not None:save(output/'source-events.json',original_events)
    save(output/'contacts.json',mapped_contacts);save(output/'events.json',mapped_events)
    np.savez_compressed(output/'target-transforms.npz',global_matrices=mirrored,times_s=times)
    save(output/'audit.json',dict(at=now(),source_sha256=sha256(source),candidate_sha256=sha256(output/'character.glb'),
        frames=frames,fps=30,involution_max_matrix_error=error,source_rotation_projection_max_error=float(np.abs(rigid(world)-world).max()),export=check,quality_approved=False,
        scope='Reference-relative motion reflection on the same mesh and proportions. Asymmetric rigs need not produce reflected skin geometry. Source defects persist; scene geometry and authored mesh targets are not mirrored. Events require review.'))
    return output/'character.glb'


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source');parser.add_argument('recipe');parser.add_argument('output')
    parser.add_argument('--contacts');parser.add_argument('--events')
    options=parser.parse_args()
    print(write_clip(options.source,read(options.recipe),options.output,options.contacts,options.events))
