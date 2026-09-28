"""Locate rejected root-block constraints without changing their decision."""
import argparse
from pathlib import Path
import numpy as np
from threadpoolctl import threadpool_limits
from strep import read,save,sha256,now
from study_root_release_block import problem_for


def labels(problem):
    rows=[];n=len(problem.fitter.rig.vertices(problem.world[0]));sides=list(problem.fitter.spec['patches'])
    for frame in problem.frames:
        rows.extend(dict(kind='floor',frame=int(frame),vertex=v) for v in range(n))
        rows.extend(dict(kind='hover',frame=int(frame),side=side) for i,side in enumerate(sides) if problem.envelope['active_frames'][frame][i])
    rows.extend(dict(kind='foot_acceleration',center=int(i+1),side=side) for i in problem.acceleration_indices for side in sides)
    rows.extend(dict(kind='support_speed',end_frame=int(i+1),side=side) for i in problem.speed_indices for j,side in enumerate(sides) if problem.envelope['support_steps'][i][j])
    edges=sorted({end for frame in problem.frames for end in (frame,frame+1) if 1<=end<len(problem.initial)})
    rows.extend(dict(kind='adjacent_edit',end_frame=int(end),column=column) for end in edges for column in range(0,problem.initial.shape[1],3))
    rows.extend(dict(kind='root_acceleration',center=int(i+1)) for i in problem.acceleration_indices)
    return rows


def run(folder,output):
    if output.exists():raise ValueError('Preserve prior diagnostic')
    request=read(folder/'request.json');done=read(folder/'completion.json')
    for name,digest in done['files'].items():
        if sha256(folder/name)!=digest:raise ValueError('Completed output changed')
    solver=read(folder/'take/solver.json');envelope=read(folder/'envelope.json');trials=[]
    with threadpool_limits(limits=1):
        p=problem_for(request,envelope);x=p.initial[np.ix_(p.frames,p.free)].ravel();proposal=np.asarray(solver['proposed_coordinates']);description=labels(p)
        base=p.evaluate(x);smooth=p.evaluate(x,False)
        if len(description)!=len(base[2]):raise ValueError('Constraint label count differs')
        for fraction in [1.,.5,.25,.125,.0625,.03125,.015625,.0078125]:
            y=x+fraction*(proposal-x);actual=p.evaluate(y);unquantized=p.evaluate(y,False);bad=np.flatnonzero(actual[2]<-1e-8)
            selected=sorted(bad,key=lambda i:actual[2][i])[:12]
            trials.append(dict(fraction=fraction,objective=actual[0],actual_geometry_passed=p.geometric_guard(actual[5]),violations=len(bad),
                worst=[dict(index=int(i),**description[i],initial=float(base[2][i]),actual=float(actual[2][i]),unquantized=float(unquantized[2][i]),
                    linear_prediction=float(smooth[2][i]+smooth[3][i]@(y-x))) for i in selected]))
    save(output,dict(at=now(),completion_sha256=sha256(folder/'completion.json'),implementation_sha256=sha256(__file__),trials=trials,
        scope='Diagnostic of stored rejected endpoint and the same fixed fractions. No optimization, acceptance or threshold change. Geometry evaluated explicitly even when other constraints fail.',quality_approved=False))
    print([dict(fraction=t['fraction'],objective=t['objective'],geometry=t['actual_geometry_passed'],violations=t['violations'],worst=t['worst'][:3]) for t in trials])


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('folder',type=Path);p.add_argument('output',type=Path);a=p.parse_args();run(a.folder.resolve(),a.output.resolve())
