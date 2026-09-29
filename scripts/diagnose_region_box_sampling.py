"""Reconstruct the frozen fitting sample and locate missed full-skin collisions."""
import argparse
from pathlib import Path
import numpy as np
from strep import ROOT,read,save,sha256
from build_soma_preview import ASSET
from floor_contact import Surface
from support_contact_v5 import infer_support
from contact_spec import apply_overrides
from scene_solver_context import context_primitives


def run(study,output):
    if output.exists():raise ValueError('Preserve earlier diagnosis')
    protocol=read(study/'protocol.json');done=read(study/'result.json');recipe=read(study/'recipe.json')
    for name,key in [('protocol.json','protocol_sha256'),('recipe.json','recipe_sha256'),('motion.npz','candidate_sha256')]:
        if sha256(study/name)!=done[key]:raise ValueError('Changed retained fit')
    for path,digest in protocol['inputs'].items():
        if sha256(path)!=digest:raise ValueError('Changed original input')
    source=dict(np.load(study/'source-motion.npz',allow_pickle=False));candidate=dict(np.load(study/'motion.npz',allow_pickle=False))
    skin=dict(np.load(ASSET,allow_pickle=False));surface=Surface(skin);config=recipe['config']
    package=read(study/'region-constraints.json');context=recipe['scene_context']
    if context['normals'] or context.get('partner_cuts'):raise ValueError('This diagnostic requires the region-only object fixture')
    contacts=apply_overrides(infer_support(source,skin),source,skin,recipe['contact_spec'],config['fade_frames'],config['clearance_m'])
    selected={int(v) for r in package['regions'] for v in r['vertex_ids']}
    primitives=context_primitives(context)
    for c in contacts.values():selected.update(c['vertex_ids'].tolist())
    selected.update(range(0,len(skin['bind_vertices']),config['object_uniform_stride']))
    for r,p in zip(source['global_rot_mats'],source['posed_joints']):
        points=surface.vertices(r,p);selected.update(np.argsort(points[:,1])[:32].tolist())
    for frame,(r,p) in enumerate(zip(source['global_rot_mats'],source['posed_joints'])):
        points=surface.vertices(r,p)
        for geometry,obj in primitives:
            d=geometry.distance_gradient(points,np.asarray(obj['positions_m'][frame]),np.asarray(obj['rotations'][frame]))[0]
            selected.update(np.argsort(d)[:config['object_near_samples']].tolist())
    ids=np.array(sorted(selected))
    if len(ids)!=recipe['selected_vertices']:raise ValueError('Reconstructed fitting sample differs')
    rows=[]
    for frame,(r,p) in enumerate(zip(candidate['global_rot_mats'],candidate['posed_joints'])):
        points=surface.vertices(r,p)
        for index,(geometry,obj) in enumerate(primitives):
            d,gradient,*_=geometry.distance_gradient(points,np.asarray(obj['positions_m'][frame]),np.asarray(obj['rotations'][frame]))
            worst=int(d.argmin());names=skin['rig_joint_names'][skin['lbs_indices'][worst]]
            rows.append(dict(frame=frame,object=index,full_minimum_m=float(d.min()),sample_minimum_m=float(d[ids].min()),
                worst_vertex=worst,worst_in_fitting_sample=worst in selected,root_vertical_distance_derivative=float(gradient[worst,1]),
                omitted_penetrating_vertices=int(sum((d[v]<0) for v in range(len(d)) if v not in selected)),
                influences=[dict(joint=str(n),weight=float(w)) for n,w in zip(names,skin['lbs_weights'][worst]) if w>0]))
    save(output,dict(study=str(study),result_sha256=sha256(study/'result.json'),implementation_sha256=sha256(__file__),
        sample_vertices=ids.tolist(),total_vertices=len(skin['bind_vertices']),rows=rows,
        initial_root_lift_derivative_m_per_logit=config['max_root_lift_m']*1e-4*(1-1e-4),
        final_root_lift_m=recipe['root_lift_m'],quality_approved=False))
    print(dict(selected=len(ids),total=len(skin['bind_vertices']),worst=min(rows,key=lambda r:r['full_minimum_m'])))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('study',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();run(a.study.resolve(),a.output.resolve())
