"""Reconstruct frozen collision samples and measure omissions in an exported fit."""
import argparse
from pathlib import Path
import shutil
import numpy as np
from scipy.spatial.transform import Rotation,Slerp
from threadpoolctl import threadpool_limits
from strep import ROOT,read,save,sha256,now
from build_soma_preview import ASSET
from floor_contact import Surface
from support_contact_v8 import infer_support
from contact_spec import apply_overrides
from scene_solver_context import context_primitives
from gltf_tools import read_glb
from rig_clip_import import AnimationSampler


def selected_vertices(base,previous,skin,recipe):
    """Replay V8-V12 selection from saved preprocessing, never candidate geometry."""
    surface=Surface(skin);config=recipe['config'];context=recipe['scene_context']
    spec=recipe.get('release_endpoint_guards',{}).get('solver_contact_spec',recipe['contact_spec'])
    contacts=infer_support(base,skin)
    contacts=apply_overrides(contacts,base,skin,spec,config['fade_frames'],config['clearance_m'])
    selected=set()
    for r,p in zip(base['global_rot_mats'],base['posed_joints']):
        selected.update(np.argsort(surface.vertices(r,p)[:,1])[:32].tolist())
    for c in contacts.values():selected.update(c['vertex_ids'].tolist())
    for c in context['normals']:
        faces=skin['faces'][np.any(skin['faces']==c['surface_vertex'],axis=1)]
        selected.update(faces.reshape(-1).tolist())
    objects=context_primitives(context)
    if objects:
        selected.update(range(0,len(skin['bind_vertices']),config['object_uniform_stride']))
        for motion in [base,previous]:
            for f,(r,p) in enumerate(zip(motion['global_rot_mats'],motion['posed_joints'])):
                points=surface.vertices(r,p)
                for geometry,obj in objects:
                    distances=geometry.distance_gradient(points,np.array(obj['positions_m'][f]),np.array(obj['rotations'][f]))[0]
                    selected.update(np.argsort(distances)[:config['object_near_samples']].tolist())
    for cut in context.get('partner_cuts',[]):selected.add(cut['vertex'])
    result=np.array(sorted(selected),dtype=int)
    if len(result)!=recipe['selected_vertices']:raise ValueError('Reconstructed optimization sample count mismatch')
    return result


def inflated_depth(points,position,rotation,geometry,clearance):
    if geometry.shape=='sphere':return np.maximum(0,geometry.dimensions[0]+clearance-np.linalg.norm(points-position,axis=-1))
    return np.maximum(0,(np.array(geometry.dimensions)/2+clearance-np.abs((points-position)@rotation)).min(-1))


def run(study,output):
    study=Path(study).resolve();output=Path(output).resolve();fit=study/'fit'
    summary=read(fit/'summary.json');audit=read(Path(str(study)+'-audit')/'verification.json')
    if summary['solver_version'] not in [8,9,10,11,12] or len(summary['trials'])!=1:raise ValueError('Expected one V8-V12 development scene')
    if read(study/'pipeline.json')['status']!='complete':raise ValueError('Incomplete fit')
    if audit['fit_summary_sha256']!=sha256(fit/'summary.json'):raise ValueError('Audit binding mismatch')
    for name,digest in summary['implementation'].items():
        if sha256(ROOT/'scripts'/name)!=digest or sha256(fit/'source-snapshot'/name)!=digest:raise ValueError('Selection implementation changed: '+name)
    if sha256(ASSET)!=summary['mesh_sha256']:raise ValueError('Mesh changed')
    trial=summary['trials'][0]['id'];scene=read(fit/trial/'candidate.json')['scene']
    if set(scene['actors'])!={'A'}:raise ValueError('Single actor expected')
    folder=fit/'assets'/trial/'A';recipe=read(folder/'recipe.json')['contact']
    base=dict(np.load(folder/'limb-motion.npz',allow_pickle=False));previous=dict(np.load(folder/'previous-motion.npz',allow_pickle=False));skin=dict(np.load(ASSET,allow_pickle=False))
    surface=Surface(skin);selected=selected_vertices(base,previous,skin,recipe)
    selected_mask=np.zeros(len(skin['bind_vertices']),bool);selected_mask[selected]=True
    asset=fit/scene['actors']['A']['preview_glb'];doc,binary=read_glb(asset);sampler=AnimationSampler(doc,binary,0);joints=doc['skins'][0]['joints']
    if [doc['nodes'][j]['name'] for j in joints]!=surface.names:raise ValueError('Bone order mismatch')
    measured=audit['variants']['candidate']['A']
    if sha256(asset)!=measured['glb_sha256']:raise ValueError('Export differs from audit')
    frames=np.arange((scene['frame_count']-1)*4+1)/4;clock=np.arange(scene['frame_count'])
    objects=[]
    for geometry,obj in context_primitives(recipe['scene_context']):
        positions=np.array(obj['positions_m']);rotations=np.array(obj['rotations'])
        p=np.stack([np.interp(frames,clock,positions[:,axis]) for axis in range(3)],1)
        r=Slerp(clock,Rotation.from_matrix(rotations))(frames).as_matrix()
        objects.append((geometry,obj['id'],p,r))
    dominant=skin['lbs_indices'][np.arange(len(selected_mask)),skin['lbs_weights'].argmax(1)]
    rows={name:dict(full_max_m=[],selected_max_m=[],omitted_max_m=[],full_over_10mm_vertex_samples=0,omitted_over_10mm_vertex_samples=0,objective_per_key=[],worst=None) for _,name,_,_ in objects}
    for i,frame in enumerate(frames):
        matrices=sampler.sample(float(np.float32(frame/30)))[joints];points=surface.vertices(matrices[:,:3,:3],matrices[:,:3,3])
        for geometry,name,p,r in objects:
            depths=geometry.penetration_depth(points,p[i],r[i]);row=rows[name];vertex=int(depths.argmax())
            row['full_max_m'].append(float(depths[vertex]));row['selected_max_m'].append(float(depths[selected].max()))
            row['omitted_max_m'].append(float(depths[~selected_mask].max(initial=0)))
            row['full_over_10mm_vertex_samples']+=int((depths>.01).sum());row['omitted_over_10mm_vertex_samples']+=int(((depths>.01)&~selected_mask).sum())
            if row['worst'] is None or depths[vertex]>row['worst']['depth_m']:
                row['worst']=dict(frame=float(frame),vertex=vertex,depth_m=float(depths[vertex]),included_in_solver=bool(selected_mask[vertex]),dominant_bone=surface.names[dominant[vertex]])
            if frame.is_integer():row['objective_per_key'].append(float(inflated_depth(points[selected],p[i],r[i],geometry,recipe['config']['object_clearance_m']).max()**2))
    for name,row in rows.items():
        expected=read(Path(str(study)+'-audit')/'candidate.json')['actors']['A']['objects'][name]['depth_m']
        row['audit_max_depth_discrepancy_m']=float(np.max(np.abs(np.array(row['full_max_m'])-expected)))
        if row['audit_max_depth_discrepancy_m']>2e-6:raise ValueError('Full exported geometry does not reproduce dense audit')
        row['maximum_selected_depth_m']=max(row['selected_max_m']);row['maximum_omitted_depth_m']=max(row['omitted_max_m'])
    objective=float(np.mean([np.mean(r['objective_per_key']) for r in rows.values()])*recipe['config']['object_collision_weight'])
    fixed_penalty='object_inequalities' not in recipe
    if fixed_penalty and abs(objective-recipe['objective']['object_collision'])>2e-4:raise ValueError('Reconstructed sampled objective mismatch')
    max_violation=float(np.sqrt(max(max(row['objective_per_key']) for row in rows.values())))
    if not fixed_penalty and abs(max_violation-recipe['stage_records'][-1]['max_sampled_object_clearance_violation_m'])>2e-6:raise ValueError('Sampled final constraint mismatch')
    output.mkdir(parents=True,exist_ok=False);shutil.copyfile(__file__,output/'method.py')
    save(output/'diagnosis.json',dict(at=now(),study=study.relative_to(ROOT).as_posix(),fit_summary_sha256=sha256(fit/'summary.json'),audit_sha256=sha256(Path(str(study)+'-audit')/'verification.json'),dense_candidate_sha256=sha256(Path(str(study)+'-audit')/'candidate.json'),glb_sha256=sha256(asset),mesh_sha256=sha256(ASSET),method_sha256=sha256(__file__),selected_vertices=selected.tolist(),frames=frames.tolist(),objects=rows,reconstructed_fixed_penalty=objective,fixed_penalty_equivalence_checked=fixed_penalty,maximum_sampled_key_clearance_violation_m=max_violation,recorded_objective=recipe['objective']['object_collision'],quality_approved=False,scope='Exact current/snapshot implementation binding and reconstructed frozen selection, independently decoded exported skin. For V12 the squared penalty is a diagnostic proxy, not its AL merit; final sampled constraint magnitude is checked instead. Attribution of failure to omission versus sampled constraint violation; not feasibility, anatomy, self-collision or naturalness proof.'))
    print(dict(selected=len(selected),objects={n:{k:v for k,v in r.items() if not isinstance(v,list)} for n,r in rows.items()},objective=objective),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('study',type=Path);parser.add_argument('output',type=Path);args=parser.parse_args()
    with threadpool_limits(limits=2):run(args.study,args.output)
