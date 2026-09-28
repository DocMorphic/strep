"""Await one exact triangle-audit owner, verify positives, compare depth curves."""
import argparse
from pathlib import Path
import subprocess
import sys
import time
import traceback
import psutil
from strep import read, save, sha256, now


def run(study, output):
    study, output = study.resolve(), output.resolve()
    request = read(study/'request.json')
    if output.exists():
        raise ValueError('Preserve earlier completion attempt')
    output.mkdir(parents=True)
    owner = psutil.Process()
    save(output/'request.json',dict(at=now(),pid=owner.pid,created=owner.create_time(),study=str(study),
         study_request_sha256=sha256(study/'request.json'),wait_pid=request['pid'],wait_created=request['created'],
         implementation_sha256=sha256(__file__),proof_script_sha256=sha256(Path(__file__).with_name('verify_triangle_scene.py')),
         quality_approved=False))

    def phase(status, **details):
        save(output/'pipeline.json',dict(at=now(),status=status,quality_approved=False,**details))
        print(status,details,flush=True)

    try:
        phase('waiting_for_exact_triangle_owner')
        while True:
            try:
                proc=psutil.Process(request['pid'])
                if proc.create_time()!=request['created']:
                    raise ValueError('Triangle owner PID reused')
            except psutil.NoSuchProcess:
                break
            time.sleep(5)
        if read(study/'pipeline.json')['status']!='complete':
            raise ValueError('Triangle audit did not complete')
        saved=read(output/'request.json')
        if sha256(study/'request.json')!=saved['study_request_sha256']:
            raise ValueError('Triangle request changed')
        completion=read(study/'completion.json');summary=read(study/'summary.json')
        expected=[(scene,frame) for scene in request['scenes'] for frame in request['frames']]
        if [(r['scene'],r['frame']) for r in summary['rows']]!=expected:
            raise ValueError('Unexpected triangle sample population')
        if completion['samples']!=len(expected) or completion['summary_sha256']!=sha256(study/'summary.json'):
            raise ValueError('Incomplete triangle evidence')
        for row in summary['rows']:
            if sha256(study/row['sample'])!=row['sample_sha256']:
                raise ValueError('Changed triangle sample')
        script=Path(__file__).with_name('verify_triangle_scene.py')
        if sha256(script)!=saved['proof_script_sha256']:
            raise ValueError('Independent verifier changed')
        phase('independent_positive_verification')
        with (output/'proof.log').open('w',encoding='utf8') as log:
            subprocess.run([sys.executable,str(script),str(study),str(output/'proof')],check=True,
                           stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        proof=read(output/'proof/completion.json')
        if proof['failed'] or proof['samples']!=len(expected):
            raise ValueError('Incomplete independent proof')
        phase('compare_vertex_and_triangle_curves')
        source=Path(request['source']);exported=read(source/'completion.json')
        if exported['geometry_summary_sha256']!=sha256(source/'geometry-summary.json'):
            raise ValueError('Vertex geometry summary changed')
        geometry=read(source/'geometry-summary.json');comparisons=[];inputs={}
        for variant in ['raw','candidate']:
            vertex_path=source/'geometry'/variant/'samples.json'
            expected_hash=next(r['samples_sha256'] for r in geometry['rows'] if r['variant']==variant)
            if sha256(vertex_path)!=expected_hash:
                raise ValueError('Vertex samples changed')
            inputs[str(vertex_path)]=expected_hash
            vertices=read(vertex_path)['rows']
            triangles=[r for r in summary['rows'] if r['scene']==variant+'.json']
            if [r['frame'] for r in vertices]!=request['frames'] or len(triangles)!=len(vertices):
                raise ValueError('Vertex/triangle clocks differ')
            rows=[]
            for v,t in zip(vertices,triangles):
                if v['frame']!=t['frame']:
                    raise ValueError('Clock reordered')
                sample=read(study/t['sample']);depth=max(d['max_depth_m'] for d in v['collision'])
                crossing=t['counts'].get('proper_crossing',0)
                rows.append(dict(frame=v['frame'],vertex_peak_depth_m=depth,proper_crossing_pairs=crossing,
                                 other_triangle_outcomes={k:n for k,n in t['counts'].items() if k not in ['proper_crossing','disjoint']},
                                 degenerate_face_counts=t['degenerate_face_counts']))
            comparisons.append(dict(variant=variant,rows=rows,
                frames_with_proper_crossings=[r['frame'] for r in rows if r['proper_crossing_pairs']],
                crossing_frames_at_or_below_5mm_depth=[r['frame'] for r in rows if r['proper_crossing_pairs'] and r['vertex_peak_depth_m']<=.005],
                crossing_frames_at_or_below_10nm_depth=[r['frame'] for r in rows if r['proper_crossing_pairs'] and r['vertex_peak_depth_m']<=1e-8],
                vertex_frames_over_5mm=[r['frame'] for r in rows if r['vertex_peak_depth_m']>.005]))
        save(output/'comparison.json',dict(at=now(),rows=comparisons,vertex_inputs=inputs,quality_approved=False,
             scope='Same decoded discrete clocks, complementary surface-crossing and vertex-depth measures. Pair counts are not depth/severity. '
             'No new rejection threshold, optimizer change, continuous/self-collision or quality certification.'))
        save(output/'completion.json',dict(at=now(),samples=len(expected),proof_crossings=proof['crossings'],
             triangle_summary_sha256=sha256(study/'summary.json'),proof_completion_sha256=sha256(output/'proof/completion.json'),
             comparison_sha256=sha256(output/'comparison.json'),quality_approved=False))
        phase('complete')
    except BaseException as exc:
        phase('failed',error=str(exc),traceback=traceback.format_exc())
        raise


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('study',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args();run(args.study,args.output)
