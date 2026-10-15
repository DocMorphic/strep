"""Independent barycentric feasibility checks for reported triangle crossings."""
import argparse
from pathlib import Path
import time
import numpy as np
from scipy.optimize import linprog
from scipy.spatial.transform import Rotation
from threadpoolctl import threadpool_limits
from strep import read, save, sha256, now
from rig_asset import RigAsset, array
from rig_clip_import import AnimationSampler


def interior_witness(a, b):
    # Separate formulation: find one point with positive barycentric weights in
    # both triangles, maximizing the minimum of all six weights.
    origin = np.mean(np.r_[a,b], axis=0)
    scale = float(np.ptp(np.r_[a,b], axis=0).max())
    if scale <= 0:
        raise ValueError('Degenerate comparison')
    a, b = (a-origin)/scale, (b-origin)/scale
    equality = np.zeros((5,7))
    equality[:3,:3], equality[:3,3:6] = a.T, -b.T
    equality[3,:3], equality[4,3:6] = 1, 1
    inequality = np.c_[-np.eye(6), np.ones(6)]
    objective = np.r_[np.zeros(6), -1.]
    result = linprog(objective, A_ub=inequality, b_ub=np.zeros(6),
                     A_eq=equality, b_eq=[0,0,0,1,1], bounds=[(0,1)]*7,
                     method='highs', options={'primal_feasibility_tolerance':1e-9,'dual_feasibility_tolerance':1e-9})
    if not result.success:
        return dict(feasible=False, status=int(result.status), message=result.message)
    residual = float(np.abs(equality@result.x-[0,0,0,1,1]).max())
    return dict(feasible=True, minimum_barycentric_weight=float(result.x[:6].min()),
                max_scaled_equality_error=residual, barycentric=result.x[:6].tolist(),
                position_m=((result.x[:3]@a)*scale+origin).tolist())


def run(study, output):
    study, output = study.resolve(), output.resolve()
    if output.exists():
        raise ValueError('Preserve prior verification')
    complete, request, summary = [read(study/n) for n in ['completion.json','request.json','summary.json']]
    if complete['summary_sha256'] != sha256(study/'summary.json'):
        raise ValueError('Summary changed')
    for path, digest in request['inputs'].items():
        if sha256(path) != digest:
            raise ValueError('Input changed')
    source = Path(request['source'])
    output.mkdir(parents=True)
    save(output/'request.json',dict(at=now(),study=str(study),request_sha256=sha256(study/'request.json'),
         summary_sha256=sha256(study/'summary.json'),implementation_sha256=sha256(__file__),
         minimum_barycentric_weight=1e-8,maximum_scaled_equality_error=1e-8,quality_approved=False))
    rows = []
    with threadpool_limits(limits=1):
        for sample in summary['rows']:
            if sha256(study/sample['sample']) != sample['sample_sha256']:
                raise ValueError('Sample changed')
            scene=read(source/sample['scene'])['scene'];triangles=[]
            for actor in scene['actors'].values():
                rig=RigAsset.load(source/actor['preview_glb']);sampler=AnimationSampler(rig.document,rig.binary,0)
                p=rig.primitives[0];mesh=rig.document['nodes'][p['node']]['mesh']
                faces=array(rig.document,rig.binary,rig.document['meshes'][mesh]['primitives'][p['primitive']]['indices']).reshape(-1,3)
                vertices=rig.vertices(sampler.sample(float(np.float32(sample['frame']/scene['fps']))))
                vertices=vertices@Rotation.from_quat(actor['transform']['rotation_xyzw']).as_matrix().T+actor['transform']['translation_m']
                triangles.append(vertices[faces])
            records=read(study/sample['sample'])['records'];checks=[];start=time.perf_counter()
            for record in records:
                if record['kind'] != 'proper_crossing':
                    continue
                result=interior_witness(triangles[0][record['left_triangle']],triangles[1][record['right_triangle']])
                passed=result['feasible'] and result['minimum_barycentric_weight']>1e-8 and result['max_scaled_equality_error']<=1e-8
                checks.append(dict(left_triangle=record['left_triangle'],right_triangle=record['right_triangle'],passed=passed,**result))
            name=f'sample-{len(rows):03d}.json';save(output/name,dict(checks=checks,quality_approved=False))
            rows.append(dict(scene=sample['scene'],frame=sample['frame'],crossings=len(checks),
                             failed=sum(not c['passed'] for c in checks),seconds=time.perf_counter()-start,
                             checks=name,checks_sha256=sha256(output/name)))
            print(rows[-1],flush=True)
            save(output/'summary.json',dict(rows=rows,quality_approved=False))
    failed=sum(r['failed'] for r in rows)
    save(output/'completion.json',dict(at=now(),samples=len(rows),crossings=sum(r['crossings'] for r in rows),failed=failed,
         summary_sha256=sha256(output/'summary.json'),quality_approved=False,
         scope='Independent linear feasibility witness for every reported proper crossing in these samples. Does not prove absence of missed crossings, exact predicates, continuous collision or quality.'))
    if failed:
        raise ValueError('One or more reported crossings lack an independent strict-interior witness')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('study',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args();run(args.study,args.output)
