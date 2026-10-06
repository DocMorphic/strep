"""Bounded root-translation projection for explicitly authored transition supports.

Append a variant; retain original clips, support/floor/rate limits and failed
evidence. This is a root-only proposal, not leg IK or a feasibility solver.
"""
import argparse
import copy
from pathlib import Path
import shutil
import tempfile
import numpy as np
from scipy.spatial.transform import Rotation
from threadpoolctl import threadpool_limits
from action_worker_lock import worker_lock
from gltf_tools import append_accessor,authored_animation,write_glb
from native_rig_transfer import preserves_target
from native_support_clock import NativeSupportSampler
from native_support_skin import NativeSupportSkin
from native_scene_contacts import fields,scalar
from native_transition_curve import rates
import native_rig_transition as transition
from rig_asset import RigAsset
from strep import read,save,sha256,now

SCHEMA='strep-native-transition-root-support-v1'
SCRIPT_ROOT=Path(__file__).resolve().parent
METHODS=tuple(dict.fromkeys(transition.METHODS+('native_transition_root_support.py',)))


def root_fractions(rig,skin,root):
    descendants=[]
    for n in range(len(rig.parents)):
        node=n
        while node>=0 and node!=root:node=rig.parents[node]
        descendants.append(node==root)
    # Match the Float64 pose/skin evaluator while retaining raw stored weights.
    # Float32 accumulation can round a mixed eight-slot response differently.
    return np.sum(skin.weights*np.asarray(descendants)[skin.nodes],axis=1,dtype=float)


def hermite(a,b,va,vb,t,d):
    u=t/d
    return (2*u**3-3*u**2+1)*a+(u**3-2*u**2+u)*d*va+(-2*u**3+3*u**2)*b+(u**3-u**2)*d*vb


class Problem:
    def __init__(self,recipe,base):
        fields(recipe,('schema','source','label','window_s','maximum_root_translation_change_m',
            'maximum_joint_displacement_m','maximum_pose_vertex_queries'),'root support correction')
        transition.require(recipe['schema']==SCHEMA,'Root support schema required')
        fields(recipe['source'],('folder','result_sha256'),'source transition binding')
        transition.require(isinstance(recipe['source']['folder'],str) and recipe['source']['folder'],'Source transition folder required')
        self.folder=(Path(base)/recipe['source']['folder']).resolve()
        transition.require(sha256(self.folder/'result.json')==recipe['source']['result_sha256'],'Source transition result changed')
        self.source_result=transition.verify(self.folder)
        p=read(self.folder/'prepared.json');self.original=transition.Problem(read(self.folder/'recipe.json'),p['recipe_base'])
        self.rig=RigAsset.load(self.folder/'character.glb');self.index=self.source_result['animation_index']
        self.reader=NativeSupportSampler(self.rig.document,self.rig.binary,self.index)
        self.root=self.original.recipe['root_node'];self.recipe=recipe;self.skin=NativeSupportSkin(self.rig)
        root_channels=[c for c in self.reader.channels if c[:2]==(self.root,'translation')]
        transition.require(len(root_channels)==1 and root_channels[0][4]=='LINEAR','An existing LINEAR root translation track is required')
        self.channel=root_channels[0];self.times=self.channel[2].astype(float);self.source_values=self.channel[3].copy()
        transition.require(np.array_equal(self.times,self.original.times),'Root must use the complete transition clock')
        transition.require(isinstance(recipe['label'],str) and 1<=len(recipe['label'])<=160,'Correction label required')
        transition.require(isinstance(recipe['window_s'],list) and len(recipe['window_s'])==2,'Explicit edit window required')
        self.first,self.last=[scalar(t,0,self.reader.duration,'root edit endpoint') for t in recipe['window_s']]
        transition.require(self.first<self.last and self.first in self.times and self.last in self.times,'Window endpoints must be distinct native keys')
        self.limit=scalar(recipe['maximum_root_translation_change_m'],1e-6,.22,'root translation budget')
        self.displacement=scalar(recipe['maximum_joint_displacement_m'],1e-6,.22,'joint displacement budget')
        transition.require(self.original.supports,'Explicit source supports required')
        self.probes=np.unique(np.r_[self.original.probes,self.first,self.last]);self.population=len(self.probes)*(2*len(self.rig.parents)+len(self.skin.nodes))
        transition.require(type(recipe['maximum_pose_vertex_queries']) is int and 1<=recipe['maximum_pose_vertex_queries']<=1000000
            and self.population<=recipe['maximum_pose_vertex_queries'],'Complete root-correction population exceeds its budget; no truncation')
        self.fractions=root_fractions(self.rig,self.skin,self.root)
        self.parent=self.rig.parents[self.root]
        self.source_world=np.array([self.reader.sample(float(t)) for t in self.probes])
        self.source_vertices=np.array([self.rig.vertices(w) for w in self.source_world])
        self.conflicts=[]
        parent=np.tile(np.eye(3),(len(self.probes),1,1)) if self.parent<0 else self.source_world[:,self.parent,:3,:3]
        radii=np.minimum(self.limit*np.linalg.norm(parent,ord=2,axis=(1,2)),self.displacement)
        for row,ids,target,lo,hi in self.original.supports:
            for i,t in enumerate(self.probes):
                if not lo<=t<=hi:continue
                error=np.linalg.norm(self.source_vertices[i,ids]-target,axis=1)
                movable=self.first<t<self.last
                reach=self.fractions[ids]*radii[i] if movable else np.zeros(len(ids))
                bad=np.flatnonzero(error>reach+row['limits']['position_m'])
                if len(bad):
                    k=int(bad[0]);self.conflicts.append(dict(kind='support-reach' if movable else 'protected-support',id=row['id'],time_s=float(t),
                        vertex=int(ids[k]),position_error_m=float(error[k]),maximum_root_effect_m=float(reach[k]),limit_m=row['limits']['position_m']));break
        floor=self.original.recipe['floor']
        if floor is not None:
            for i,t in enumerate(self.probes):
                if not self.original.start<=t<=self.original.end:continue
                depth=floor['height_m']-self.source_vertices[i,:,1]
                reach=self.fractions*radii[i] if self.first<t<self.last else np.zeros(len(self.fractions))
                bad=np.flatnonzero(depth>reach+floor['maximum_penetration_m'])
                if len(bad):
                    k=int(bad[0]);self.conflicts.append(dict(kind='floor-reach' if self.first<t<self.last else 'protected-floor',time_s=float(t),vertex=k,
                        penetration_m=float(depth[k]),maximum_root_effect_m=float(reach[k]),limit_m=floor['maximum_penetration_m']));break

    def construct(self):
        transition.require(not self.conflicts,'Necessary root-support conflicts block a candidate')
        values=self.source_values.copy();held={};groups=[]
        # Guard both native keys bracketing each authored hold. This proposal
        # extension preserves contact timing in the request; audits use its exact interval.
        for i,t in enumerate(self.times):
            active=[]
            for row,ids,target,lo,hi in self.original.supports:
                left=max(0,int(np.searchsorted(self.times,lo,side='right'))-1);right=min(len(self.times)-1,int(np.searchsorted(self.times,hi)))
                if self.times[left]<=t<=self.times[right]:active.append((row,ids,target))
            if not active:continue
            if not self.first<t<self.last:
                # A passing fixed endpoint is retained rather than edited.
                held[i]=values[i].copy();continue
            world=self.reader.sample(float(t));points=self.rig.vertices(world)
            parent=np.eye(3) if self.parent<0 else world[self.parent,:3,:3]
            matrices=[];goals=[]
            for _,ids,target in active:
                matrices.append((self.fractions[ids,None,None]*parent[None]).reshape(-1,3));goals.append((target-points[ids]).reshape(-1))
            delta=np.linalg.lstsq(np.concatenate(matrices),np.concatenate(goals),rcond=None)[0]
            held[i]=values[i]+delta
        transition.require(len(held)>=2,'Two bracketing support keys required')
        keys=sorted(held)
        start=0
        for j in range(1,len(keys)+1):
            if j==len(keys) or keys[j]>keys[j-1]+1:
                ids=keys[start:j];transition.require(len(ids)>=2,'A supported key group needs neighboring rate samples');groups.append(ids);start=j
        first=int(np.searchsorted(self.times,self.first));last=int(np.searchsorted(self.times,self.last))
        for i,p in held.items():values[i]=p
        spans=[]
        def source_rate(i,side):
            a,b=(i-1,i) if side=='before' and i>0 else (i,i+1) if i<len(self.times)-1 else (i-1,i)
            return (self.source_values[b]-self.source_values[a])/(self.times[b]-self.times[a])
        def group_rate(ids,side):
            a,b=ids[:2] if side=='first' else ids[-2:];return (held[b]-held[a])/(self.times[b]-self.times[a])
        spans.append((first,groups[0][0],self.source_values[first],held[groups[0][0]],source_rate(first,'before'),group_rate(groups[0],'first')))
        for a,b in zip(groups[:-1],groups[1:]):spans.append((a[-1],b[0],held[a[-1]],held[b[0]],group_rate(a,'last'),group_rate(b,'first')))
        spans.append((groups[-1][-1],last,held[groups[-1][-1]],self.source_values[last],group_rate(groups[-1],'last'),source_rate(last,'after')))
        for a,b,p,q,v,w in spans:
            if a>=b:continue
            for i in range(a+1,b):values[i]=hermite(p,q,v,w,self.times[i]-self.times[a],self.times[b]-self.times[a])
        editable=(self.times>self.first)&(self.times<self.last)
        delta=values-self.source_values
        # Reserve quantization room without widening any decoded acceptance limit.
        ulp=np.max(np.abs(np.spacing(self.source_values.astype('<f4'))),axis=0).astype(float)
        radius=max(0,min(self.limit,self.displacement)-4*float(np.linalg.norm(ulp)))
        norms=np.linalg.norm(delta,axis=1);scale=np.minimum(1,radius/np.maximum(norms,1e-30))
        values[editable]=(self.source_values+delta*scale[:,None])[editable].astype('<f4')
        values[~editable]=self.source_values[~editable]
        return values

    def export(self,path):
        values=self.construct();doc=copy.deepcopy(self.rig.document);binary=bytearray(self.rig.binary)
        animation=copy.deepcopy(doc['animations'][self.index]);label=authored_animation(self.recipe['label'])
        animation['name']=label['name'];animation['extras']={**animation.get('extras',{}),**label['extras'],
            'root_support_source_animation_index':self.index,'root_support_source_glb_sha256':sha256(self.folder/'character.glb')}
        for channel in animation['channels']:
            if channel['target']==dict(node=self.root,path='translation'):
                sampler=copy.deepcopy(animation['samplers'][channel['sampler']]);sampler['output']=append_accessor(doc,binary,values,'VEC3')
                channel['sampler']=len(animation['samplers']);animation['samplers'].append(sampler)
        doc['animations'].append(animation);write_glb(path,doc,binary)

    def audit(self,path):
        rig=RigAsset.load(path);index=len(self.rig.document['animations']);transition.require(len(rig.document['animations'])==index+1 and preserves_target(self.rig,rig,{}),'Original clips/static rig/payload changed')
        reader=NativeSupportSampler(rig.document,rig.binary,index)
        transition.require(reader.duration==self.reader.duration and len(reader.channels)==len(self.reader.channels),'Clip duration or channel population changed')
        frozen=(self.times<=self.first)|(self.times>=self.last);expected=self.construct()
        for old,new in zip(self.reader.channels,reader.channels):
            transition.require(old[:2]==new[:2] and old[4]==new[4] and np.array_equal(old[2],new[2]),'Native channel identity/clock changed')
            if old[:2]==(self.root,'translation'):
                transition.require(np.array_equal(new[3],expected) and np.array_equal(old[3][frozen],new[3][frozen]),'Root values or protected keys changed')
            else:transition.require(np.array_equal(old[3],new[3]),'Unpermitted pose path changed')
        worlds=np.array([reader.sample(float(t)) for t in self.probes]);vertices=np.array([rig.vertices(w) for w in worlds])
        delta=np.linalg.norm(worlds[:,rig.joints,:3,3]-self.source_world[:,rig.joints,:3,3],axis=2)
        rotation_error=float(abs(worlds[:,:,:3,:3]-self.source_world[:,:,:3,:3]).max())
        change=float(np.linalg.norm(expected-self.source_values,axis=1).max());displacement=float(delta.max())
        support=[]
        for row,ids,target,lo,hi in self.original.supports:
            mask=(self.probes>=lo)&(self.probes<=hi);p=vertices[mask][:,ids];t=self.probes[mask]
            error=float(np.linalg.norm(p-target,axis=2).max());slip=float(np.linalg.norm(np.diff(p,axis=0)/np.diff(t)[:,None,None],axis=2).max())
            support.append(dict(id=row['id'],samples=len(t),maximum_position_error_m=error,maximum_slip_m_s=slip,passed=error<=row['limits']['position_m'] and slip<=row['limits']['relative_speed_m_s']))
        inside=(self.probes>=self.original.start)&(self.probes<=self.original.end);floor=self.original.recipe['floor']
        depth=None if floor is None else max(0,float(floor['height_m']-vertices[inside,:,1].min()))
        keys=worlds[np.searchsorted(self.probes,self.times)];v,w=rates(keys,self.times);boundaries=[]
        for t in sorted(set((self.first,self.last,self.original.start,self.original.end))):
            i=int(np.searchsorted(self.times,t))
            if not 0<i<len(self.times)-1:continue
            boundaries.append(dict(time_s=t,linear_jump_m_s=float(np.linalg.norm(v[i,rig.joints]-v[i-1,rig.joints],axis=1).max()),angular_jump_degrees_s=float(np.degrees(np.linalg.norm(w[i,rig.joints]-w[i-1,rig.joints],axis=1)).max())))
        dt=np.diff(self.times);acc=np.diff(v[:,self.root],axis=0)/((dt[1:]+dt[:-1])/2)[:,None];centers=self.times[1:-1]
        peak=float(np.linalg.norm(acc[(centers>=min(self.first,self.original.start))&(centers<=max(self.last,self.original.end))],axis=1).max())
        bridge=worlds[inside,self.root,:3,3];u=(self.probes[inside]-self.original.start)/self.original.duration
        excursion=float(np.linalg.norm(bridge-((1-u[:,None])*bridge[0]+u[:,None]*bridge[-1]),axis=1).max())
        limits=self.original.recipe['limits'];checks=dict(root_translation=change<=self.limit,joint_displacement=displacement<=self.displacement,
            rotations_unchanged=rotation_error<=1e-12,supports=all(s['passed'] for s in support),root_acceleration=peak<=limits['root_acceleration_m_s2'],root_excursion=excursion<=limits['bridge_root_excursion_m'],
            linear_boundaries=all(b['linear_jump_m_s']<=limits['linear_boundary_jump_m_s'] for b in boundaries),angular_boundaries=all(b['angular_jump_degrees_s']<=limits['angular_boundary_jump_degrees_s'] for b in boundaries))
        if floor is not None:checks['floor']=depth<=floor['maximum_penetration_m']
        root_motion=dict(space='Declared root world transform, Y-up metres; extraction not applied',node=self.root,animation_index=index,
            times_s=self.times.tolist(),positions_m=keys[:,self.root,:3,3].tolist(),rotations_xyzw=Rotation.from_matrix(keys[:,self.root,:3,:3]).as_quat().tolist())
        return dict(animation_index=index,keys=len(self.times),queries=len(self.probes),pose_vertex_population=self.population,
            maximum_root_translation_change_m=change,maximum_joint_displacement_m=displacement,maximum_rotation_matrix_change=rotation_error,
            supports=support,floor_maximum_penetration_m=depth,root_acceleration_max_m_s2=peak,bridge_root_excursion_m=excursion,
            boundaries=boundaries,checks=checks,all_declared_samples_pass=all(checks.values())),root_motion


def result(problem,output):
    value=dict(schema=SCHEMA,status='complete',source_result_sha256=sha256(problem.folder/'result.json'),
        necessary_conflicts=problem.conflicts,candidate_available=not bool(problem.conflicts),original_selected=True,
        **{n:False for n in transition.FALSE_FLAGS},
        scope='Explicit root-translation-only support projection and bounded ramps; every old clip retained. Original support/floor/rate limits unchanged. Complete sampled bridge screens and correction-window seam/rate guards, not whole-source floor/physics/action/continuous-contact approval.')
    if problem.conflicts:value.update(all_declared_samples_pass=False,checks=dict(preflight=False))
    else:
        audit,root=problem.audit(output/'character.glb');value.update(audit)
        transition.require(transition.equal(read(output/'root-motion.json'),root),'Root-motion sidecar changed')
    value.update(prepared_sha256=sha256(output/'prepared.json'),files_sha256={n:sha256(output/n) for n in (('character.glb','root-motion.json') if value['candidate_available'] else ())})
    return value


def run(recipe_path,output):
    recipe_path=Path(recipe_path).resolve();output=Path(output).resolve()
    with worker_lock(),threadpool_limits(limits=1):
        recipe=read(recipe_path);problem=Problem(recipe,recipe_path.parent);transition.require(not output.exists(),'Fresh root-correction output required')
        transition.require(not recipe_path.is_relative_to(output) and not problem.folder.is_relative_to(output),'Output contains an input')
        output.mkdir();(output/'implementation').mkdir();shutil.copyfile(recipe_path,output/'recipe.json');shutil.copyfile(problem.folder/'character.glb',output/'source.glb')
        methods={n:sha256(SCRIPT_ROOT/n) for n in METHODS}
        for n in METHODS:shutil.copyfile(SCRIPT_ROOT/n,output/'implementation'/n)
        save(output/'prepared.json',dict(schema=SCHEMA,at=now(),recipe_base=str(recipe_path.parent),recipe_original_path=str(recipe_path),
            recipe_sha256=sha256(recipe_path),source_glb_sha256=sha256(output/'source.glb'),implementation_sha256=methods))
        save(output/'pipeline.json',dict(status='processing',original_selected=True))
        try:
            if not problem.conflicts:
                problem.export(output/'character.glb');_,root=problem.audit(output/'character.glb');save(output/'root-motion.json',root)
            value=result(problem,output);save(output/'result.json',value);save(output/'completion.json',dict(result_sha256=sha256(output/'result.json')))
            save(output/'pipeline.json',dict(status='complete',original_selected=True));verify(output);return value
        except Exception as exc:
            save(output/'pipeline.json',dict(status='failed',error=str(exc),original_selected=True));raise


def verify(output):
    output=Path(output).resolve();p=read(output/'prepared.json')
    fields(p,('schema','at','recipe_base','recipe_original_path','recipe_sha256','source_glb_sha256','implementation_sha256'),'root correction preparation')
    transition.require(p['schema']==SCHEMA and set(p['implementation_sha256'])==set(METHODS),'Complete root correction methods required')
    for n,h in p['implementation_sha256'].items():transition.require(sha256(SCRIPT_ROOT/n)==sha256(output/'implementation'/n)==h,'Root correction methods changed')
    transition.require(sha256(p['recipe_original_path'])==sha256(output/'recipe.json')==p['recipe_sha256'],'Root correction recipe changed')
    problem=Problem(read(output/'recipe.json'),p['recipe_base'])
    transition.require(sha256(output/'source.glb')==sha256(problem.folder/'character.glb')==p['source_glb_sha256'],'Root correction source changed')
    transition.require(read(output/'pipeline.json')==dict(status='complete',original_selected=True),'Completed correction required')
    if not problem.conflicts:
        with tempfile.TemporaryDirectory(prefix='strep-root-support-replay-') as temporary:
            expected=Path(temporary)/'character.glb';problem.export(expected)
            transition.require(sha256(expected)==sha256(output/'character.glb'),'Root correction construction changed')
    else:transition.require(not (output/'character.glb').exists() and not (output/'root-motion.json').exists(),'Conflicting source cannot publish a candidate')
    value=result(problem,output);transition.require(transition.equal(read(output/'result.json'),value),'Root correction measurements or decisions changed')
    transition.require(read(output/'completion.json')==dict(result_sha256=sha256(output/'result.json')),'Root correction completion changed')
    return value


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('recipe',type=Path);parser.add_argument('output',type=Path);args=parser.parse_args()
    print(run(args.recipe,args.output))
