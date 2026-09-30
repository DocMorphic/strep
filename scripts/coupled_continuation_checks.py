"""Independent exported-motion checks and cheap retained-witness screening."""
import numpy as np
from scipy.spatial.transform import Rotation
from strep import ROOT,save,sha256
from gltf_tools import read_glb
from paired_temporal_neighbor import placed_joint_positions,rotation_channels
from study_paired_guarded_temporal import decoded,motion_guard
from study_paired_temporal_neighbor import preservation
from audit_scene_joint_rates import compare_rates
from verify_paired_stage_rates import verify_rates


class ContinuationReview:
    def __init__(self,problem,initial_gaps):
        self.problem=problem;self.initial_inside=np.asarray(initial_gaps)<0
        self.caps=np.concatenate([g['caps'] for g in problem.groups]);self.baselines=[];self.references=[]
        if self.initial_inside.shape!=self.caps.shape or not self.initial_inside.any():raise ValueError('Bound initial witness population required')
        self.indices=np.arange(597)/4;self.locked=(self.indices<63)|(self.indices>=75)
        for actor in problem.actors:
            doc,world=decoded(actor['source']);positions=placed_joint_positions(world,doc['skins'][0]['joints'],actor['rotation'],actor['translation'])
            self.baselines.append((doc,world,positions));ref,binary=read_glb(actor['reference']);self.references.append(rotation_channels(ref,binary))

    def witness_vectors(self,worlds):
        vectors=[];gaps=[]
        for group in self.problem.groups:
            source,target=group['source'],group['target'];a,b=self.problem.actors[source],self.problem.actors[target]
            frames=np.array([int(round(row['frame']*4)) for row in group['rows']]);triangles=group['triangles']
            points=a['skin'].evaluate(worlds[source],frames,group['ids'])@a['rotation'].T+a['translation']
            targets=(b['skin'].evaluate(worlds[target],np.repeat(frames,3),triangles.ravel())@b['rotation'].T+b['translation']).reshape(-1,3,3)
            bary=np.maximum(group['bary'],0);bary=bary/bary.sum(1)[:,None]
            vector=points-np.einsum('ni,nij->nj',bary,targets)
            vectors.append(vector);gaps.append(np.einsum('ni,ni->n',vector,group['normals']))
        vectors=np.concatenate(vectors);gaps=np.concatenate(gaps);norms=np.linalg.norm(vectors,axis=1)
        excess=np.r_[norms[self.initial_inside]-self.caps[self.initial_inside],-gaps-self.caps]
        return vectors,dict(peak_m=float(norms[self.initial_inside].max()),maximum_cap_excess_m=float(max(0.,excess.max())),cap_failures_over_1e_6=int((excess>1e-6).sum()))

    def export_and_check(self,controls,folder):
        folder.mkdir();checks=[];worlds=[];verified=0;replay_error=0.
        for index,(actor,part) in enumerate(zip(self.problem.actors,np.split(controls,[self.problem.sizes[0]]))):
            path=folder/(actor['name']+'.glb');actor['model'].export(part,path);doc,world=decoded(path);worlds.append(world)
            source_doc,source_world,source_positions=self.baselines[index]
            positions=placed_joint_positions(world,doc['skins'][0]['joints'],actor['rotation'],actor['translation'])
            names=[doc['nodes'][j]['name'] for j in doc['skins'][0]['joints']]
            rates=compare_rates(source_positions,positions,names,dict(whole_clip=[0,149],**self.problem.windows))
            count,error=verify_rates(source_positions,positions,rates,names);verified+=count;replay_error=max(replay_error,error)
            rates_path=folder/(actor['name']+'-rates.json');save(rates_path,rates);failures=motion_guard(rates)
            body=ROOT/'reports/paired-pose-posture-v1'/f"seed-1301/{actor['name']}/body_fit/character.glb"
            proof=preservation(actor['source'],path,body,dict(selected_joints=['LeftShoulder','LeftArm','LeftForeArm','LeftHand'],frames=list(range(64,75))))
            actual,binary=read_glb(path);channels=rotation_channels(actual,binary)
            maximum=max(float(np.rad2deg((Rotation.from_quat(self.references[index][node][2]).inv()*Rotation.from_quat(q)).magnitude()).max()) for node,(_,_,q) in channels.items())
            drift=float(np.abs(world[self.locked]-source_world[self.locked]).max());np.testing.assert_allclose(world[self.locked],source_world[self.locked],atol=1e-12,rtol=0)
            checks.append(dict(actor=actor['name'],path=path.name,sha256=sha256(path),rates_sha256=sha256(rates_path),rate_failures=len(failures),
                largest_failures=sorted(failures,key=lambda x:x['change'],reverse=True)[:8],maximum_original_edit_degrees=maximum,protected_world_error=drift,preservation=proof))
        vectors,surface=self.witness_vectors(worlds);np.savez_compressed(folder/'witness-vectors.npz',vectors=vectors)
        return dict(actors=checks,surface=surface,verified_peak_values=verified,maximum_replay_error=replay_error,witness_vectors_sha256=sha256(folder/'witness-vectors.npz'))
