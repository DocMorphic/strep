"""Generation-only review: every fixed seed, with unresolved audits explicit."""
import argparse
from pathlib import Path
import shutil
from strep import ROOT,read,save,sha256,now


def run(study,audit,output):
    study,audit,output=[Path(p).resolve() for p in [study,audit,output]]
    if output.exists() or output.parent!=ROOT/'reports':raise ValueError('Use a new reports folder')
    protocol=read(study/'protocol.json');points=read(study/'event-point-screen.json');manifest=read(audit/'manifest.json')
    if points['protocol_sha256']!=sha256(study/'protocol.json') or points['generation_summary_sha256']!=sha256(study/'generation/summary.json'):raise ValueError('Generation comparison changed')
    seeds=[e['seed'] for e in read(study/'baseline-population.json')['entries']]
    lookup={r['id']:r for r in points['rows']};versions=[];rows=[]
    for seed in seeds:
        for method,label in [('baseline','Unconditioned'),('hand','Hand target'),('body','Body pose target')]:
            identifier=f'{method}-seed-{seed}';scene_path=audit/identifier/'scene.json';scene=read(scene_path)['scene'];actors={}
            for actor in ['A','B']:
                relative=scene['actors'][actor]['preview_glb'];digest=manifest['assets'][relative]['sha256']
                if sha256(audit/relative)!=digest:raise ValueError('Actor changed')
                actors[actor]=dict(url='../'+audit.name+'/'+relative,sha256=digest)
            gap=lookup[f'hand-seed-{seed}']['baseline_event_gap_m'] if method=='baseline' else lookup[identifier]['raw_generated_event_gap_m']
            text=f'Seed {seed} · {label}'
            versions.append(dict(id=identifier,label=text,scene='../'+audit.name+'/'+identifier+'/scene.json',actors=actors,audit='../'+audit.name+'/results.json',
                note=f'{text}. Palm-point gap at frame75: {gap*1000:.1f} mm. Raw model output; no post-generation correction. Full-scene audit is separate and may still be running. No quality approval.'))
            rows.append(dict(label=text,gap=f'{gap*1000:.1f} mm',depth='Pass' if gap<=.03 else 'Fail',screens='See live audit'))
    if len(versions)!=15:raise ValueError('Incomplete seed/method population')
    template=(ROOT/'scripts/palm-continuation-review.html').read_text(encoding='utf-8')
    replacements={
        'Two hands, one contact':'Does shared pose guidance coordinate two people?',
        'Same saved pose · eight additional fitting iterations · bounded arms versus arms and fingers':'Five fixed seeds · unchanged checkpoint · unconditioned, hand-target and body-pose guidance',
        'Development comparison on one observed high-five. Surface proximity and engine import do not establish a usable interaction. No independent animator review. The earlier candidate intersects one frame before contact; motion through the surrounding frames needs separate validation.':'All ten guided pairs improve the selected palm-point distance over their matching baseline, but all still exceed 30 mm at the requested contact frame. The common guide pose is a development fixture, not validated ground truth. Generated fingers are unchanged. Collision, timing, distributed contact and independent human review remain separate requirements.',
        '<th>Selected-pair gap</th><th>Event penetration</th><th>Event screens</th>':'<th>Palm gap · frame75</th><th>30 mm point screen</th><th>Full-scene validation</th>',
        'Independent event audit':'Live scene audit',
        'Gaps are selected solver pairs; independent contact screens also require distributed proximity and opposing normals. Event depth is a vertex test, not continuous or self-collision certification.':'Gaps compare a fixed geometry-derived palm vertex in the decoded GLBs. A small point gap is insufficient for successful contact. All versions use the same 30 fps clock; the guide methods share a fixed authored pose fixture. The live audit checks the whole clip at integer frames and half frames around the event.',
        '../paired-palm-region-export-v4/SOMA-preview-LICENSE.txt':'SOMA-preview-LICENSE.txt'
    }
    for original,replacement in replacements.items():
        if original not in template:raise ValueError('Review template changed')
        template=template.replace(original,replacement)
    output.mkdir();(output/'viewer.html').write_text(template,encoding='utf-8')
    shutil.copyfile(study/'event-point-screen.json',output/'comparison.json');shutil.copyfile(study/'SOMA-preview-LICENSE.txt',output/'SOMA-preview-LICENSE.txt')
    save(output/'viewer-manifest.json',dict(versions=versions,rows=rows))
    save(output/'build.json',dict(at=now(),protocol_sha256=sha256(study/'protocol.json'),scene_manifest_sha256=sha256(audit/'manifest.json'),files={n:sha256(output/n) for n in ['viewer.html','viewer-manifest.json','comparison.json']},builder_sha256=sha256(__file__),quality_approved=False))
    print(output/'viewer.html')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('study',type=Path);p.add_argument('audit',type=Path);p.add_argument('output',type=Path);a=p.parse_args();run(a.study,a.audit,a.output)
