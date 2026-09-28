"""Copy the complete labeled clearance comparison for a developer to inspect."""
import argparse
import hashlib
import shutil
import zipfile
from pathlib import Path

from compare_kneel_origins import verified
from strep import ROOT, now, read, save, sha256


def run(study, audit, output):
    archive=output.with_suffix('.zip')
    if output.exists() or archive.exists():
        raise ValueError('Preserve earlier developer packets')
    complete=read(audit/'completion.json')
    if read(audit/'pipeline.json')['status']!='complete':
        raise ValueError('Require complete phase and engine audit')
    for path,digest in complete['inputs'].items():
        if sha256(path)!=digest:
            raise ValueError('Audit input changed')
    if sha256(audit/'results.json')!=complete['results_sha256'] or sha256(audit/'engine/verification.json')!=complete['engine_sha256']:
        raise ValueError('Audit results changed')
    raw_audit=ROOT/'reports/kneel-ending-guides-audit-v1'
    raw_complete,_=verified(raw_audit)
    proofs={r['id']:r['source_sha256'] for r in read(audit/'engine/verification.json')['checks']}
    raw_proofs={r['id']:r['source_sha256'] for r in read(raw_audit/'engine/verification.json')['checks']}
    rows=read(audit/'results.json')['rows']
    if len(rows)!=24 or len({(r['id'],r['variant']) for r in rows})!=24:
        raise ValueError('Expected complete eight-source three-variant set')
    output.mkdir(parents=True)
    files={}
    for row in rows:
        name=row['id']+'-'+row['variant']
        source=study/'takes'/row['id']
        if row['variant']!='body-candidate':
            source=source/('raw' if row['variant']=='raw' else 'limb')
        if row['glb_sha256'] != (raw_proofs[row['id']] if row['variant']=='raw' else proofs[name]):
            raise ValueError('Clip lacks matching all-frame engine proof')
        for filename in ['soma.glb','motion.bvh','root-motion.json','contacts.json']:
            src=source/filename
            if sha256(src)!=complete['inputs'][str(src)]:
                raise ValueError('Packaged source changed')
            dest=output/'clips'/name/filename
            dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(src,dest)
            if sha256(dest)!=sha256(src):
                raise ValueError('Copied bytes changed')
            files[dest.relative_to(output).as_posix()]=sha256(dest)
    shutil.copyfile(ROOT/'vendor/kimodo/LICENSE',output/'SOMA-preview-LICENSE.txt')
    (output/'README.md').write_text('''# Developer review: endings and floor clearance

These 24 editable clips show the same timed action across four seeds, two ending-guide methods and three processing versions. This is a labeled developer review, not a blind animator evaluation.

The action is: lower from standing to both knees in 2 seconds, pause upright on the knees for 1 second, step one foot forward and rise during 3 seconds. Final-frame guidance targets the standing pose at frame 179. Held-ending guidance targets it during frames 170–179. Both also set the starting pose and impose a common ending location.

Import a soma.glb or motion.bvh in your animation editor or engine at 30 fps. Compare the matching raw, limb-only and body-candidate folders. Start with seed 1301 to inspect a flagged knee gap and seed 2089 to compare a case with fewer numerical warnings, then review the remaining seeds. The body candidate is experimental: floor clearance can introduce hovering or sliding. Successful engine import does not certify realistic motion.

Watch once at normal speed, then inspect descent, knee support, the forward step, rise and finish. Record actual observations in review-notes.md. Leave cleanup time blank unless you actually edit the animation; record active editing seconds, operations and saved edited file. No ratings or cleanup times have been entered for you.

Root tracks reflect each exported version. Contact files contain unchanged model foot predictions; they do not confirm knee supports or gameplay events. The packet contains no model weights and submits nothing. All 24 source GLBs have matching all-frame Godot checks. The agent has not visually reviewed the packet.
''',encoding='utf8')
    notes=['# Developer observations','','Reviewer: ','Date: ','Editor/engine: ','',
           'Leave unknowns blank. Record cleanup seconds only for actual edits.','','| Clip | Phase/ending observations | Floor/support observations | Abruptness | Cleanup seconds | Edited file / operations |','|---|---|---|---|---|---|']
    for row in rows:
        notes.append(f"| {row['id']} / {row['variant']} | | | | | |")
    (output/'review-notes.md').write_text('\n'.join(notes)+'\n',encoding='utf8')
    save(output/'manifest.json',dict(at=now(),files=files,review_type='labeled_developer',clips=len(rows),
        source_audit_sha256=sha256(audit/'completion.json'),raw_audit_sha256=sha256(raw_audit/'completion.json'),
        rows=rows,human_review=None,visual_review=False,quality_approved=False))
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for path in sorted(output.rglob('*')):
            if path.is_file():z.write(path,path.relative_to(output).as_posix())
    with zipfile.ZipFile(archive) as z:
        if z.testzip() is not None:raise ValueError('Archive CRC failed')
        for name in z.namelist():
            if hashlib.sha256(z.read(name)).hexdigest()!=sha256(output/name):
                raise ValueError('Archived bytes changed')
    save(output.parent/(output.name+'-build.json'),dict(at=now(),archive=str(archive),archive_sha256=sha256(archive),
        bytes=archive.stat().st_size,clips=len(rows),source_engine_actor_frames=complete['engine_actor_frames']+raw_complete['engine_actor_frames'],
        all_copied_and_archived_bytes_verified=True,visual_review=False,human_review=None,quality_approved=False))
    print(dict(archive=str(archive),clips=len(rows),bytes=archive.stat().st_size))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['study','audit','output']:p.add_argument(name,type=Path)
    a=p.parse_args()
    run(a.study.resolve(),a.audit.resolve(),a.output.resolve())
