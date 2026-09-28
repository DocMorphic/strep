"""Review raw, body-fit and explicitly authored finger layers at a shared clock."""
import argparse
from pathlib import Path
import shutil
from strep import ROOT,read,save,sha256,now


def run(study,audit,output):
    study,audit,output=[Path(p).resolve() for p in [study,audit,output]]
    if output.exists() or output.parent!=ROOT/'reports':raise ValueError('Use a new reports folder')
    proof=read(study/'preservation-verification.json');manifest=read(study/'manifest.json');request=read(study/'request.json')
    if proof['manifest_sha256']!=sha256(study/'manifest.json') or proof['request_sha256']!=sha256(study/'request.json'):raise ValueError('Changed verification')
    for path,digest in proof['files'].items():
        if sha256(path)!=digest:raise ValueError('Changed verified payload')
    versions=[];rows=[];lookup={s['id']:s for s in manifest['scenes']}
    for seed in request['seeds']:
        for mode,label in [('raw','Raw generation'),('body_fit','Body correction'),('body_fit_posture','Body + authored hand')]:
            identifier=f'{mode}-seed-{seed}';item=lookup[identifier];scene=read(study/item['variants']['palm'])['scene'];actors={}
            for actor in ['A','B']:
                relative=scene['actors'][actor]['preview_glb'];actors[actor]=dict(url='../'+study.name+'/'+relative,sha256=manifest['assets'][relative]['sha256'])
            text=f'Seed {seed} · {label}'
            versions.append(dict(id=identifier,label=text,scene='../'+study.name+'/'+item['variants']['palm'],actors=actors,audit='../'+audit.name+'/pipeline.json',
                note=f'{text}. Same saved scene placement and 30 fps clock. Authored finger pose reaches full strength at frame75 and blends over60–90. Complete surface-motion audit is separate; no quality approval.'))
            rows.append(dict(label=text,gap='Model output' if mode=='raw' else 'Fitted anchors 0 / 75 / 149',depth='Authored 60–90' if mode=='body_fit_posture' else 'Model relaxed hand',screens='Pending full geometry'))
    template=(ROOT/'scripts/palm-continuation-review.html').read_text(encoding='utf-8')
    replacements={
        'Two hands, one contact':'Body motion and hand posture, separately',
        'Same saved pose · eight additional fitting iterations · bounded arms versus arms and fingers':'Five fixed seeds · raw generation · body correction · timed authored fingers',
        'Development comparison on one observed high-five. Surface proximity and engine import do not establish a usable interaction. No independent animator review. The earlier candidate intersects one frame before contact; motion through the surrounding frames needs separate validation.':'The model does not retain authored finger poses. This comparison applies a separate timed hand layer after body correction. All variants passed engine import; independent preservation checks cover every actor. Contact, approach collisions and floor checks are still being audited. No animation is approved.',
        '<th>Selected-pair gap</th><th>Event penetration</th><th>Event screens</th>':'<th>Body motion</th><th>Finger source</th><th>Motion validation</th>',
        'Independent event audit':'Live geometry audit',
        'Gaps are selected solver pairs; independent contact screens also require distributed proximity and opposing normals. Event depth is a vertex test, not continuous or self-collision certification.':'The hand layer changes only selected finger rotations. Body correction is a separate operation and can affect motion throughout the clip. Inspect before and after contact; matching one pose is insufficient for a usable interaction.',
        '../paired-palm-region-export-v4/SOMA-preview-LICENSE.txt':'SOMA-preview-LICENSE.txt'}
    for old,new in replacements.items():
        if old not in template:raise ValueError('Review template changed')
        template=template.replace(old,new)
    output.mkdir();(output/'viewer.html').write_text(template,encoding='utf-8');save(output/'viewer-manifest.json',dict(versions=versions,rows=rows))
    shutil.copyfile(study/'preservation-verification.json',output/'comparison.json');shutil.copyfile(study/'SOMA-preview-LICENSE.txt',output/'SOMA-preview-LICENSE.txt')
    save(output/'build.json',dict(at=now(),source_manifest_sha256=sha256(study/'manifest.json'),source_proof_sha256=sha256(study/'preservation-verification.json'),
        files={n:sha256(output/n) for n in ['viewer.html','viewer-manifest.json','comparison.json']},builder_sha256=sha256(__file__),quality_approved=False))
    print(output/'viewer.html')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('study',type=Path);p.add_argument('audit',type=Path);p.add_argument('output',type=Path);a=p.parse_args();run(a.study,a.audit,a.output)
