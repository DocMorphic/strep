"""Recover a stopped refresh prefix into a new run with explicit provenance."""
import ast
from pathlib import Path
import numpy as np
from strep import ROOT,read,sha256
from bound_evidence import bind_inputs


def extraction_kernel(source):
    tree=ast.parse(source)
    matches=[n for n in ast.walk(tree) if isinstance(n,ast.If) and isinstance(n.test,ast.Call)
             and isinstance(n.test.func,ast.Name) and n.test.func.id=='all'
             and any(isinstance(c,ast.Attribute) and c.attr=='array_equal' for c in ast.walk(n.test))]
    if len(matches)!=1:raise ValueError('One unchanged-pose / fresh-query extraction block required')
    return ast.dump(matches[0],include_attributes=False)


def recover_current(donor,study,controls,required,actors,worlds):
    donor=Path(donor).resolve()
    if (donor/'result.json').exists():raise ValueError('Recovery is for an unfinished run, not completed evidence')
    request=read(donor/'request.json')
    if Path(request['study']).resolve()!=Path(study).resolve():raise ValueError('Recovery parent differs')
    np.testing.assert_array_equal(request['cumulative_controls'],controls)
    files=bind_inputs(required,request['inputs'])
    files[str(donor/'request.json')]=sha256(donor/'request.json')
    expected={'study_scene_pair_relinearization.py','strep.py','build_guarded_pair_witnesses.py','convex_partner_surface.py',
              'scene_pair_problem.py','timed_rotation_edit.py','paired_approach_basis.py','rig_asset.py','rig_clip_import.py'}
    if not expected.issubset(request['implementation']):raise ValueError('Recovery geometry snapshots are incomplete')
    for name,digest in request['implementation'].items():
        old=(donor/'implementation'/name).resolve();current=ROOT/'scripts'/name
        if old.parent!=donor/'implementation' or sha256(old)!=digest:raise ValueError('Recovery snapshot changed')
        if name=='study_scene_pair_relinearization.py':
            if extraction_kernel(old.read_text())!=extraction_kernel(current.read_text()):raise ValueError('Geometry extraction block changed')
        elif name=='strep.py':
            # Only JSON output retry is changing. Reads and identity hashing
            # must remain the same for recovery from the recorded old version.
            def functions(path):
                return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(path.read_text()).body
                        if isinstance(n,ast.FunctionDef) and n.name in ['read','sha256']}
            if functions(old)!=functions(current):raise ValueError('Recovery read/hash methods changed')
        elif sha256(current)!=digest:raise ValueError('Recovery geometry method changed: '+name)
        files[str(old)]=digest
    paths=sorted((donor/'current').glob('sample-*.json'));times=actors[0]['model'].times
    if not paths or len(paths)>len(times):raise ValueError('Nonempty bounded geometry prefix required')
    recovered={}
    for index,path in enumerate(paths):
        if path.name!=f'sample-{index:03d}.json':raise ValueError('Contiguous saved prefix required')
        row=read(path)
        if row['sample']!=index or row['time_s']!=times[index] or len(row['directions'])!=2:raise ValueError('Recovery sample clock differs')
        for s,t in [(0,1),(1,0)]:
            direction=row['directions'][s];records=direction['records']
            if direction['source']!=s or direction['target']!=t or direction['selected_witnesses']!=len(records):raise ValueError('Recovery witness population differs')
            if not np.isfinite(direction['maximum_depth_m']) or direction['maximum_depth_m']<0:raise ValueError('Invalid recovered depth')
            if not records:
                if direction['maximum_depth_m']!=0:raise ValueError('Positive depth lacks retained witness')
                continue
            ids=np.array([r['vertex'] for r in records],int);tri=np.array([r['target_vertices'] for r in records],int)
            faces=np.array([r['target_triangle'] for r in records],int)
            if np.any(ids<0) or np.any(tri<0) or np.any(faces<0):raise ValueError('Nonnegative geometry indices required')
            np.testing.assert_array_equal(tri,actors[t]['faces'][faces])
            bary=np.array([r['barycentric'] for r in records]);normals=np.array([r['normal'] for r in records])
            if np.any(bary < -1e-8) or np.any(bary > 1+1e-8):raise ValueError('Recovered point is outside its triangle')
            np.testing.assert_allclose(bary.sum(axis=1),1,atol=1e-8,rtol=0)
            np.testing.assert_allclose(np.linalg.norm(normals,axis=1),1,atol=1e-8,rtol=0)
            a,b=actors[s],actors[t];frames=np.full(len(ids),index)
            points=a['skin'].evaluate(worlds[s],frames,ids)@a['rotation'].T+a['translation']
            triangles=(b['skin'].evaluate(worlds[t],np.repeat(frames,3),tri.ravel())@b['rotation'].T+b['translation']).reshape(-1,3,3)
            closest=np.einsum('ni,nij->nj',bary,triangles)
            gaps=np.einsum('ni,ni->n',points-closest,normals)
            np.testing.assert_allclose(points,[r['source_position_m'] for r in records],atol=1e-8,rtol=0)
            np.testing.assert_allclose(closest,[r['target_position_m'] for r in records],atol=1e-8,rtol=0)
            np.testing.assert_allclose(gaps,[r['gap_m'] for r in records],atol=1e-8,rtol=0)
            np.testing.assert_allclose(np.maximum(-gaps,0).max(),direction['maximum_depth_m'],atol=1e-8,rtol=0)
        unchanged=all(np.array_equal(w[index],a['model'].source_world[index]) for a,w in zip(actors,worlds))
        recovered[index]=(row,unchanged);files[str(path)]=sha256(path)
    return recovered,files
