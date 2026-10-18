"""Model-free complete native scene observations from supplied saved poses.

Independent of guidance/decoder/autograd code; baseline skin/primitive libraries
are shared. Discrete vertex observations are not full collision or approval.
"""
import numpy as np
from floor_contact import Surface
from object_geometry import Geometry


def observe_scene_motion(plan,skin,rotations,positions):
    n=plan.get('frames');r=np.asarray(rotations);p=np.asarray(positions);surface=Surface(skin)
    if (plan.get('schema')!='strep-authored-scene-guidance-v1' or type(n) is not int or not 3<=n<=300
            or surface.names!=plan['joint_names'] or len(surface.names)!=77 or len(skin['bind_vertices'])!=plan['vertices']
            or r.shape!=(n,77,3,3) or p.shape!=(n,77,3) or not np.isfinite(r).all() or not np.isfinite(p).all()):
        raise ValueError('Complete compiled native scene, original skin and matching finite poses required')
    normal=np.asarray(plan['floor_normal']);offset=plan['floor_offset_m'];floor=[];objects=[[] for _ in plan['primitives']];contacts=[{} for _ in plan['contacts']];speeds=[];accelerations=[];previous=[]
    def append(index,name,value):contacts[index].setdefault(name,[]).append(float(value))
    for f in range(n):
        v=surface.vertices(r[f],p[f]);depth=np.maximum(0,offset-v@normal);floor.append([depth.max(),np.count_nonzero(depth>0),depth@depth])
        for i,obj in enumerate(plan['primitives']):
            d=Geometry.parse(obj['geometry']).penetration_depth(v,np.asarray(obj['positions_m'][f]),np.asarray(obj['rotations'][f]));objects[i].append([d.max(),np.count_nonzero(d>0),d@d])
        for i,c in enumerate(plan['contacts']):
            if not c['start_frame']<=f<=c['end_frame']:continue
            j=f-c['start_frame'];append(i,'position',np.linalg.norm(v[c['vertex']]-c['targets_m'][j]))
            if 'normal_directions' in c:
                faces=np.asarray(c['normal_faces']);ids,remap=np.unique(faces,return_inverse=True);centered=surface.vertices(r[f],p[f]-p[f,0],ids)[remap.reshape(-1,3)]
                sn=np.cross(centered[:,1]-centered[:,0],centered[:,2]-centered[:,0]).sum(0);length=np.linalg.norm(sn);sn=sn/max(length,1e-12)
                append(i,'normal',1-np.clip(sn@c['normal_directions'][j],-1,1));append(i,'normal_degenerate',length<1e-12)
                if 'tangent_directions' in c:
                    tangent=p[f,c['knuckle_joints']].mean(0)-p[f,c['hand_joint']];tangent-=sn*(tangent@sn);length=np.linalg.norm(tangent);tangent/=max(length,1e-12)
                    append(i,'tangent',1-np.clip(tangent@c['tangent_directions'][j],-1,1));append(i,'tangent_degenerate',length<1e-12)
        if previous:speeds.append(np.linalg.norm((v-previous[-1])*30,axis=-1).max())
        if len(previous)==2:accelerations.append(np.linalg.norm((v-2*previous[-1]+previous[-2])*900,axis=-1).max())
        previous=(previous+[v])[-2:]
    result=dict(floor=np.asarray(floor).T,skin_speed_m_s=np.asarray(speeds),skin_acceleration_m_s2=np.asarray(accelerations),
        joint_speed_m_s=np.linalg.norm(np.diff(p,axis=0)*30,axis=-1).max(-1),joint_acceleration_m_s2=np.linalg.norm(np.diff(p,n=2,axis=0)*900,axis=-1).max(-1))
    if objects:result['objects']=np.transpose(np.asarray(objects),(0,2,1))
    for name in ['position','normal','tangent','normal_degenerate','tangent_degenerate']:
        values=[c[name] for c in contacts if name in c]
        if values:result['contact_'+name]=np.concatenate(values)
    return result
