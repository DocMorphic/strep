"""Show completed bounded-arm evidence, including the worst collision frame."""
import argparse
from pathlib import Path
import shutil
from strep import ROOT, read, save, sha256, now


def run(study,summary,output):
    study,summary,output=[Path(p).resolve() for p in [study,summary,output]]
    if output.exists() or output.parent!=ROOT/'reports':raise ValueError('Use a new reports folder')
    evidence=read(summary/'summary.json');audit=Path(evidence['audit'])
    if sha256(audit/'completion.json')!=evidence['completion_sha256']:raise ValueError('Audit proof changed')
    for path,digest in evidence['verified_files'].items():
        if sha256(path)!=digest:raise ValueError('Verified evidence changed: '+path)
    manifest=read(study/'manifest.json');request=read(study/'request.json')
    if sha256(study/'manifest.json')!=read(audit/'completion.json')['source_manifest_sha256']:raise ValueError('Different study manifest')
    rows={r['id']:r for r in evidence['rows']};versions=[];table=[]
    for item in manifest['scenes']:
        identifier=item['id'];row=rows[identifier];mode,seed=identifier.split('-seed-')
        label={'raw':'Original generation','body_fit':'Bounded arm correction','body_fit_posture':'Bounded arms + authored fingers'}[mode]
        text=f'Seed {seed} · {label}';scene=read(study/item['variants']['palm'])['scene']
        actors={a:dict(url='../'+study.name+'/'+v['preview_glb'],sha256=manifest['assets'][v['preview_glb']]['sha256']) for a,v in scene['actors'].items()}
        note=f"{text}. Worst sampled collision {row['max_depth_m']*1000:.2f} mm at frame {row['peak_frame']}; worst floor penetration {row['floor_max_depth_m']*1000:.2f} mm. Motion remains unapproved."
        if seed=='2089' and mode!='raw':note+=' Actor A also misses the strict wrist-orientation target.'
        versions.append(dict(id=identifier,label=text,scene='../'+study.name+'/'+item['variants']['palm'],actors=actors,
            audit='../'+audit.name+'/'+identifier+'/samples.json',peak_frame=row['peak_frame'],note=note))
        table.append(dict(label=text,gap=f"{row['event_gap_m']*1000:.2f} mm",depth=f"{row['max_depth_m']*1000:.2f} mm · frame {row['peak_frame']}",screens='Collision and floor fail'))
    template=(ROOT/'scripts/palm-continuation-review.html').read_text(encoding='utf-8')
    replacements={
        'Two hands, one contact':'Bounded arms, complete motion review',
        'Same saved pose · eight additional fitting iterations · bounded arms versus arms and fingers':'Five fixed seeds · original generation · bounded arm corrections · optional authored fingers',
        'Development comparison on one observed high-five. Surface proximity and engine import do not establish a usable interaction. No independent animator review. The earlier candidate intersects one frame before contact; motion through the surrounding frames needs separate validation.':'The completed 15-scene audit checks 180 samples per scene and 4,500 actual engine actor-frames. Contact-event gaps improve, but every variant still fails whole-motion collision and floor screens. Use Worst collision to inspect a measured failure. No animation is approved.',
        '<th>Selected-pair gap</th><th>Event penetration</th><th>Event screens</th>':'<th>Contact-frame gap</th><th>Worst motion penetration</th><th>Motion screens</th>',
        'Independent event audit':'Complete sampled geometry',
        'Gaps are selected solver pairs; independent contact screens also require distributed proximity and opposing normals. Event depth is a vertex test, not continuous or self-collision certification.':'Contact is at frame75; arm and finger edits fade over60–90. Root and other body motion stay unchanged. All integer frames and half-frames60–90 were checked, not every continuous instant. The newer wider-path experiment is separate and is not shown here.',
        '../paired-palm-region-export-v4/SOMA-preview-LICENSE.txt':'SOMA-preview-LICENSE.txt',
        '<button id="contact" disabled>Contact frame</button>':'<button id="contact" disabled>Contact frame</button><button id="peak" disabled>Worst collision</button>',
        "['version','play','frame','fit','hands','contact']":"['version','play','frame','fit','hands','contact','peak']",
        "$('version').onchange=load;":"$('peak').onclick=()=>{stop();seek(manifest.versions.find(v=>v.id===$('version').value).peak_frame);};$('version').onchange=load;"}
    for old,new in replacements.items():
        if old not in template:raise ValueError('Review template changed')
        template=template.replace(old,new)
    output.mkdir();(output/'viewer.html').write_text(template,encoding='utf-8')
    save(output/'viewer-manifest.json',dict(versions=versions,rows=table))
    shutil.copyfile(summary/'summary.json',output/'comparison.json');shutil.copyfile(study/'SOMA-preview-LICENSE.txt',output/'SOMA-preview-LICENSE.txt')
    save(output/'build.json',dict(at=now(),source_summary_sha256=sha256(summary/'summary.json'),source_request_sha256=sha256(study/'request.json'),
        files={n:sha256(output/n) for n in ['viewer.html','viewer-manifest.json','comparison.json']},builder_sha256=sha256(__file__),quality_approved=False))
    print(output/'viewer.html',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('study',type=Path);p.add_argument('summary',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();run(a.study,a.summary,a.output)
