"""Bind retained approach witnesses to joint geometry and motion linearizations."""
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from strep import ROOT,read,sha256
from gltf_tools import read_glb
from rig_asset import RigAsset
from paired_approach_basis import ApproachActor,BoundSkin
from paired_surface_witness import moving_gap,moving_gap_jacobian
from coupled_pair_proposal import motion_rows


class PairProblem:
    def __init__(self,witnesses):
        self.witnesses=Path(witnesses).resolve();self.request=read(self.witnesses/'request.json');result=read(self.witnesses/'result.json')
        if result['status']!='complete' or result['request_sha256']!=sha256(self.witnesses/'request.json'):raise ValueError('Completed witness population required')
        self.inputs={**self.request['inputs'],str(self.witnesses/'request.json'):sha256(self.witnesses/'request.json'),str(self.witnesses/'result.json'):sha256(self.witnesses/'result.json')}
        self.records=[];seen=[]
        for name,digest in result['artifacts'].items():
            path=self.witnesses/name;self.inputs[str(path)]=digest;row=read(path);seen.append(row['frame'])
            cap=max(.005,max(d['maximum_depth_m'] for d in row['directions']))
            for direction in row['directions']:
                self.records.extend(dict(frame=row['frame'],source=direction['source'],target=direction['target'],cap=cap,**record) for record in direction['records'])
        if sorted(seen)!=self.request['frames'] or len(seen)!=57:raise ValueError('Complete distinct quarter-frame approach population required')
        for file,digest in self.inputs.items():
            if sha256(file)!=digest:raise ValueError('Witness input changed')
        self.frames=np.arange(61,79.001,.25);self.windows=dict(edited_interval=[63,77],entry=[61,65],approach=[63,73],event=[73,77],exit=[75,79])
        scene=read(ROOT/'reports/paired-pose-posture-v1/body_fit_posture-seed-1301.json')['scene'];self.actors=[]
        names=['LeftShoulder','LeftArm','LeftForeArm','LeftHand']
        for actor in ['A','B']:
            folder=ROOT/'reports/paired-guarded-temporal-v4'/actor;rig=RigAsset.load(folder/'candidate.glb');ref,binary=read_glb(folder/'input.glb')
            model=ApproachActor(rig.document,rig.binary,ref,binary,names,self.frames);placement=scene['actors'][actor]['transform']
            rotation=Rotation.from_quat(placement['rotation_xyzw']).as_matrix();translation=np.asarray(placement['translation_m'])
            self.actors.append(dict(name=actor,rig=rig,model=model,skin=BoundSkin(rig),rotation=rotation,translation=translation,source=folder/'candidate.glb',reference=folder/'input.glb'))
        self.sizes=[a['model'].size for a in self.actors];self.size=sum(self.sizes)
        self.groups=[]
        for source,target in [(0,1),(1,0)]:
            records=[r for r in self.records if r['source']==source and r['target']==target]
            self.groups.append(dict(source=source,target=target,rows=records,frames=np.array([int(round((r['frame']-61)*4)) for r in records]),
                ids=np.array([r['vertex'] for r in records]),triangles=np.array([r['target_vertices'] for r in records]),
                bary=np.array([r['barycentric'] for r in records]),normals=np.array([r['normal'] for r in records]),caps=np.array([r['cap'] for r in records])))

    def linearize(self,controls):
        parts=np.split(controls,[self.sizes[0]]);world=[];derivatives=[];vectors=[];jacobians=[];radii=[];kinds=[]
        for number,(actor,part) in enumerate(zip(self.actors,parts)):
            model=actor['model'];w,j=model.world_pair(part);world.append(w);derivatives.append(j);offset=sum(self.sizes[:number])
            current=model.vectors(part).reshape(-1,3);mapping=np.kron(model.matrix,np.eye(len(model.base.nodes)*3)).reshape(-1,3,model.size)
            full=np.zeros((len(current),3,self.size));full[:,:,offset:offset+model.size]=mapping
            vectors.append(current);jacobians.append(full);radii.append(np.full(len(current),np.deg2rad(5.00005)));kinds.extend(['edit']*len(current))
            joints=model.base.joints;r=actor['rotation'];shift=actor['translation']
            positions=w[:,joints][:,:,:3,3]@r.T+shift
            pj=np.einsum('ij,tkjd->tkid',r,j[:,joints][:,:,:3,3,:])
            reference=model.base.reference_world[:,joints][:,:,:3,3]@r.T+shift
            clock=model.base.channels[model.base.nodes[0]][1]
            active=(self.frames/30>float(clock[63]))&(self.frames/30<float(clock[75]))
            value,jac,cap,order=motion_rows(positions,pj,reference,self.frames,self.windows,model.base.affected,active)
            full=np.zeros((len(value),3,self.size));full[:,:,offset:offset+model.size]=jac
            vectors.append(value);jacobians.append(full);radii.append(cap);kinds.extend(['speed' if n==1 else 'acceleration' for n in order])
        gaps=[];gap_jacobian=[];caps=[]
        for group in self.groups:
            source,target=group['source'],group['target'];a,b=self.actors[source],self.actors[target]
            frames=group['frames'];ids=group['ids'];triangles=group['triangles'];bary=group['bary'];normals=group['normals']
            points=a['skin'].evaluate(world[source],frames,ids)@a['rotation'].T+a['translation']
            target_frames=np.repeat(frames,3)
            triangle_points=(b['skin'].evaluate(world[target],target_frames,triangles.ravel())@b['rotation'].T+b['translation']).reshape(-1,3,3)
            jp=np.einsum('ij,njd->nid',a['rotation'],a['skin'].derivative(derivatives[source],frames,ids))
            jq=np.einsum('ij,njd->nid',b['rotation'],b['skin'].derivative(derivatives[target],target_frames,triangles.ravel())).reshape(-1,3,3,self.sizes[target])
            gap=moving_gap(points,triangle_points,bary,normals);derivative=moving_gap_jacobian(jp,jq,bary,normals)
            if source==1:derivative=np.c_[derivative[:,self.sizes[source]:],derivative[:,:self.sizes[source]]]
            gaps.append(gap);gap_jacobian.append(derivative);caps.append(group['caps'])
        return dict(gaps=np.concatenate(gaps),gap_jacobian=np.vstack(gap_jacobian),depth_caps=np.concatenate(caps),
                    vectors=np.concatenate(vectors),jacobians=np.concatenate(jacobians),radii=np.concatenate(radii),kinds=np.array(kinds))
