"""Build an immutable visual comparison from completed, checked exports."""
import argparse
from pathlib import Path
import shutil
from strep import ROOT,read,save,sha256,now


def run(output):
    output=Path(output).resolve()
    if output.exists() or output.parent!=ROOT/'reports':raise ValueError('Choose a new immediate reports folder')
    comparison=ROOT/'reports/palm-region-continuation-comparison.json'
    rows=[];versions=[];sources={}
    for version,variant,label in [(4,'input','Original authored hands'),(4,'candidate','Starting candidate'),(5,'candidate','Eight more steps · arms'),(6,'candidate','Eight more steps · arms and fingers')]:
        export=ROOT/f'reports/paired-palm-region-export-v{version}'
        complete=read(export/'completion-verification.json');manifest=read(export/'manifest.json')
        sources[str(export)]=sha256(export/'completion-verification.json')
        for path,digest in complete['files'].items():
            if sha256(export/path)!=digest:raise ValueError('Completed export changed')
        scene_path=export/(variant+'-scene.json');scene=read(scene_path)['scene']
        if scene['frame_count']!=150 or read(export/'request.json')['event_frame']!=75:raise ValueError('Unsupported review clock')
        actors={}
        for name in ['A','B']:
            path=scene['actors'][name]['preview_glb']
            actors[name]=dict(url='../'+export.name+'/'+path,sha256=manifest['assets'][path]['sha256'])
        passed=complete['event_screens']
        note='Original input with explicit reference finger posture. No optimized partner contact.' if variant=='input' else 'Observed development candidate. Event screens: '+', '.join(k+' '+('pass' if v else 'fail') for k,v in passed.items())+'. Surrounding motion and anatomy are not approved.'
        versions.append(dict(id=f'{version}-{variant}',label=label,scene='../'+export.name+'/'+scene_path.name,actors=actors,
            audit='../'+export.name+'/region-verification.json',note=note))
        if variant=='candidate':
            rows.append(dict(label=label,gap=f"{complete['contact_solver_max_distance_m']*1000:.3f} mm",depth=f"{complete['event_depth_m']*1000:.3f} mm",
                screens=', '.join(k+': '+('pass' if v else 'fail') for k,v in passed.items())))
    evidence=read(comparison)
    if {r['version'] for r in evidence['rows']}!={5,6}:raise ValueError('Incomplete comparison')
    output.mkdir();shutil.copyfile(comparison,output/'comparison.json')
    shutil.copyfile(ROOT/'scripts/palm-continuation-review.html',output/'viewer.html')
    save(output/'viewer-manifest.json',dict(versions=versions,rows=rows))
    save(output/'build.json',dict(at=now(),source_completions=sources,comparison_sha256=sha256(comparison),
        files={n:sha256(output/n) for n in ['comparison.json','viewer.html','viewer-manifest.json']},
        builder_sha256=sha256(__file__),quality_approved=False))
    print(output/'viewer.html')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);run(p.parse_args().output)
