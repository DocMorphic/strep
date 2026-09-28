"""Build synchronized previews only from completed independently audited trials."""
import argparse
from pathlib import Path
import shutil
import numpy as np
from strep import ROOT,read,save,sha256,now
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler


def build(studies,audits,output):
    if output.exists() or len(studies)!=len(audits):raise ValueError('New output and matching studies/audits required')
    output.mkdir(parents=True);cases=[]
    for study,audit in zip(studies,audits):
        study,audit=study.resolve(),audit.resolve();proof=read(audit);request=read(study/'request.json');done=read(study/'completion.json')
        if proof['completion_sha256']!=sha256(study/'completion.json') or read(study/'pipeline.json')['status']!='complete':raise ValueError('Independent completion binding differs')
        for name,digest in done['files'].items():
            if sha256(study/name)!=digest:raise ValueError('Completed artifact changed')
        identifier=request['case'];dest=output/identifier;dest.mkdir();prior=Path(request['prior']);spec=read(study/'take/spec.json')
        original_report=read(study/'take/input/report.json');fixture=Path(original_report['character']).parent
        if sha256(fixture/'character.glb')!=original_report['character_sha256']:raise ValueError('Original character changed')
        license_dir=dest/'source';license_dir.mkdir()
        if not (fixture/'LICENSE.md').exists():raise ValueError('Missing original character license')
        for name in ['LICENSE.md','provenance.json','UPSTREAM-README.md','Cesium-logo-terms.txt','packing.json']:
            if (fixture/name).exists():shutil.copyfile(fixture/name,license_dir/name)
        variants=[];minimum=np.full(3,np.inf);maximum=np.full(3,-np.inf)
        for variant,source in [('input',study/'take/input/character.glb'),('prior',prior/'candidate/character.glb'),('candidate',study/'take/candidate/character.glb')]:
            target=dest/(variant+'.glb');shutil.copyfile(source,target)
            rig=RigAsset.load(target);sampler=AnimationSampler(rig.document,rig.binary,0)
            for frame in range(spec['frames']):
                vertices=rig.vertices(sampler.sample(float(np.float32(frame/spec['fps']))))
                minimum=np.minimum(minimum,vertices.min(axis=0));maximum=np.maximum(maximum,vertices.max(axis=0))
            variants.append(dict(id=variant,path=target.relative_to(output).as_posix(),sha256=sha256(target),
                metrics=next(r for r in proof['rows'] if r['variant']==variant)))
        shutil.copyfile(audit,dest/'audit.json');shutil.copyfile(study/'take/comparison.json',dest/'decision.json')
        failures=proof['failed_checks']
        status=('Frozen numerical comparison: '+(', '.join(failures)+' fails.' if failures else 'all declared numerical checks pass.')+
            ' Development result only; independent animator review remains pending. Six additional leg-refit sweeps; source and previous correction are retained.')
        cases.append(dict(id=identifier,label=identifier.replace('motion-026-','Beckon · '),frames=spec['frames'],fps=spec['fps'],variants=variants,
            bounds=dict(min=minimum.tolist(),max=maximum.tolist()),audit=identifier+'/audit.json',decision=identifier+'/decision.json',
            status=status,license=identifier+'/source/LICENSE.md',source_completion_sha256=sha256(study/'completion.json'),audit_sha256=sha256(audit)))
    save(output/'manifest.json',dict(at=now(),cases=cases,quality_approved=False,human_reviews_collected=0,
        scope='Synchronized organizer comparison, not a blind reviewer packet. GLB bytes unchanged; gray preview-only material. Bounds cover all integer-frame skinned vertices.'))
    shutil.copyfile(ROOT/'scripts/fixed-root-preview.html',output/'viewer.html')
    save(output/'build.json',dict(at=now(),manifest_sha256=sha256(output/'manifest.json'),viewer_sha256=sha256(output/'viewer.html'),
        implementation_sha256=sha256(__file__),clips=3*len(cases),quality_approved=False))
    print(dict(cases=len(cases),clips=3*len(cases)))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--studies',nargs='+',type=Path,required=True);p.add_argument('--audits',nargs='+',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();build(a.studies,a.audits,a.output.resolve())
