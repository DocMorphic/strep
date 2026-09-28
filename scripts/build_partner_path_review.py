"""Expose retained raw and corrected partner motion on a shared review clock."""
import argparse
from pathlib import Path
import shutil

from strep import ROOT,read,save,sha256,now
from compare_partner_paths import full_curve


def verified_export(study):
    if read(study/'pipeline.json')['status']!='complete':raise ValueError('Require terminal study')
    done=read(study/'completion.json');export=study/'export'
    if not done['accepted'] or sha256(export/'completion.json')!=done['export_completion_sha256']:
        raise ValueError('Missing or changed terminal export')
    complete=read(export/'completion.json')
    for name,key in [('manifest.json','manifest_sha256'),('source-evidence.json','source_evidence_sha256'),
                     ('engine-audit/verification.json','engine_sha256'),('geometry-summary.json','geometry_summary_sha256')]:
        if sha256(export/name)!=complete[key]:raise ValueError('Changed export evidence')
    manifest=read(export/'manifest.json')
    for relative,item in manifest['assets'].items():
        path=(export/relative).resolve()
        if not path.is_relative_to(export) or sha256(path)!=item['sha256']:raise ValueError('Changed or escaping asset')
    if complete['engine_actor_frames']!=600 or complete['samples_per_scene']!=299:raise ValueError('Incomplete audit population')
    curves={}
    for row in read(export/'geometry-summary.json')['rows']:
        path=export/'geometry'/row['variant']/'samples.json'
        if sha256(path)!=row['samples_sha256']:raise ValueError('Changed geometry samples')
        curves[row['variant']]=full_curve(read(path)['rows'])
    if set(curves)!={'raw','candidate'}:raise ValueError('Both scenes required')
    return export,manifest,curves


def run(refinement,continuation,output):
    if output.exists() or output.parent!=ROOT/'reports':raise ValueError('Use a new reports folder')
    warm=Path(read(refinement/'request.json')['warm'])
    if Path(read(continuation/'request.json')['warm'])!=refinement:raise ValueError('Continuation does not follow refinement')
    for folder in [refinement,continuation]:
        proof=read(folder/'independent-verification.json')
        if not proof['exported'] or proof['completion_sha256']!=sha256(folder/'completion.json'):
            raise ValueError('Require independently verified terminal result')
    exports={str(p):verified_export(p) for p in [warm,refinement,continuation]}
    originals=[value[2]['raw'] for value in exports.values()]
    if not all(curve==originals[0] for curve in originals):raise ValueError('Unmatched raw baseline')
    versions=[];rows=[];comparison=[]
    entries=[(warm,'raw','raw','Original generated motion'),(warm,'candidate','warm','Earlier contact correction'),
             (refinement,'candidate','refined','Finer timing controls'),(continuation,'candidate','continued','Further correction')]
    for folder,variant,identifier,label in entries:
        export,manifest,curves=exports[str(folder)]
        scene_path=export/(variant+'.json');scene=read(scene_path)['scene'];curve=curves[variant]
        if scene['frame_count']!=150:raise ValueError('Review requires the retained150-frame clock')
        actors={}
        for actor in ['A','B']:
            relative=scene['actors'][actor]['preview_glb']
            actors[actor]=dict(url='../'+(export/relative).relative_to(ROOT/'reports').as_posix(),sha256=manifest['assets'][relative]['sha256'])
        prefix='../'+export.relative_to(ROOT/'reports').as_posix()+'/'
        versions.append(dict(id=identifier,label=label,scene=prefix+scene_path.name,actors=actors,audit=prefix+'geometry-summary.json',peak_frame=curve['peak_frame'],
            note=f'{label}. Peak partner overlap {curve["max_depth_m"]*1000:.2f} mm; {len(curve["failed_frames"])} sampled times exceed 5 mm. Floor peak {curve["floor_max_m"]*1000:.2f} mm. Development motion; not quality approved.'))
        rows.append(dict(label=label,gap=f'{curve["max_depth_m"]*1000:.2f} mm',depth=str(len(curve['failed_frames'])),screens=f'{curve["floor_max_m"]*1000:.2f} mm'))
        comparison.append(dict(id=identifier,study=str(folder),variant=variant,curve=curve,completion_sha256=sha256(folder/'completion.json')))
    template=(ROOT/'scripts/palm-continuation-review.html').read_text(encoding='utf-8')
    replacements={
        'Two hands, one contact':'Contact correction across the whole motion',
        'Same saved pose · eight additional fitting iterations · bounded arms versus arms and fingers':'One retained high-five · original motion and three correction stages · shared frame control',
        'Development comparison on one observed high-five. Surface proximity and engine import do not establish a usable interaction. No independent animator review. The earlier candidate intersects one frame before contact; motion through the surrounding frames needs separate validation.':'Every stage remains unapproved. The corrected stages preserve the contact pose, but partner overlap and floor penetration still fail the 5 mm development screens. This is one known pair, not evidence of broad interaction quality. Inspect approach, contact and recovery.',
        '<th>Selected-pair gap</th><th>Event penetration</th><th>Event screens</th>':'<th>Peak partner overlap</th><th>Samples above 5 mm</th><th>Peak floor depth</th>',
        'Independent event audit':'Full-timeline geometry audit',
        'Gaps are selected solver pairs; independent contact screens also require distributed proximity and opposing normals. Event depth is a vertex test, not continuous or self-collision certification.':'Each table row uses 299 integer and half-frame samples over the full clip. Vertex penetration does not certify continuous collision freedom, self-collision, balance or naturalness. The original and corrected stages have different contact quality; overlap alone does not rank their overall usefulness.',
        '<button id="contact" disabled>Contact frame</button>':'<button id="contact" disabled>Contact frame</button><button id="peak" disabled>Worst overlap</button>',
        "['version','play','frame','fit','hands','contact']":"['version','play','frame','fit','hands','contact','peak']",
        "$('contact').onclick=()=>{stop();seek(75);};":"$('contact').onclick=()=>{stop();seek(75);};$('peak').onclick=()=>{stop();seek(manifest.versions.find(v=>v.id===$('version').value).peak_frame);};",
        '../paired-palm-region-export-v4/SOMA-preview-LICENSE.txt':'SOMA-preview-LICENSE.txt'}
    for old,new in replacements.items():
        if old not in template:raise ValueError('Review template changed')
        template=template.replace(old,new)
    output.mkdir()
    (output/'viewer.html').write_text(template,encoding='utf-8')
    save(output/'viewer-manifest.json',dict(versions=versions,rows=rows))
    save(output/'comparison.json',dict(versions=comparison,quality_approved=False,human_review=None))
    shutil.copyfile(ROOT/'reports/paired-guide-review-v1/SOMA-preview-LICENSE.txt',output/'SOMA-preview-LICENSE.txt')
    save(output/'build.json',dict(at=now(),builder_sha256=sha256(__file__),
        files={p.name:sha256(p) for p in output.iterdir() if p.is_file()},
        source_verification={str(p):sha256(p/'independent-verification.json') for p in [refinement,continuation]},quality_approved=False))
    print(output/'viewer.html')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['refinement','continuation','output']:p.add_argument(name,type=Path)
    a=p.parse_args();run(a.refinement.resolve(),a.continuation.resolve(),a.output.resolve())
