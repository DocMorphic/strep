"""Package completed native contact experiments as a local, unapproved comparison."""
import argparse
from pathlib import Path
import shutil
from strep import ROOT, read, save, sha256, now
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler


def run(studies, output):
    output = Path(output).resolve(); studies = [Path(p).resolve() for p in studies]
    if output.exists() or output.parent != ROOT/'reports' or not 2 <= len(studies) <= 8 or len(set(studies)) != len(studies):
        raise ValueError('Two to eight distinct studies and a fresh immediate reports folder required')
    versions = []; verified = {}; copies = []; reference = None
    for index, study in enumerate(studies):
        q, r = read(study/'request.json'), read(study/'result.json')
        if r['status'] != 'complete' or not r['native_animation_exported']:
            raise ValueError('Completed native exports required')
        files = dict(q['inputs']); files[str(study/'result.json')] = sha256(study/'result.json')
        for name, digest in r['outputs'].items():
            path = (study/name).resolve()
            if path.parent != study: raise ValueError('Escaping output path')
            files[str(path)] = digest
        for name, digest in q['implementation'].items():
            path = (study/'implementation'/name).resolve()
            if path.parent != study/'implementation': raise ValueError('Escaping method archive')
            files[str(path)] = digest
        for path, digest in files.items():
            if sha256(path) != digest: raise ValueError('Changed study evidence')
            if path in verified and verified[path] != digest: raise ValueError('Conflicting study evidence')
        verified.update(files)
        def bound(path):
            if files.get(str(path)) != sha256(path): raise ValueError('Unbound comparison input')
            return read(path)
        pose = q; seen = set()
        while 'baseline' not in pose:
            path = Path(pose['source'])/'request.json'
            if path in seen or len(seen) >= 32: raise ValueError('Invalid provenance chain')
            seen.add(path); pose = bound(path)
        region = bound(Path(pose['source'])/'request.json'); prepared = bound(Path(region['prepared'])/'request.json')
        names = list(prepared['actors'])
        if names != ['A', 'B']: raise ValueError('This comparison requires the paired A/B development fixture')
        placements = [prepared['actors'][n]['placement'] for n in names]
        contract = dict(target=q['target'], event=q['event_time_s'], window=q['window_s'], guard=q['guard_times_s'], placements=placements)
        if reference is not None and contract != reference: raise ValueError('Compare matching contact intent, placements, window and guard samples')
        reference = contract; actors = []; durations = []
        for i, placement in enumerate(placements):
            path = study/f'candidate-{i}.glb'; rig = RigAsset.load(path); reader = AnimationSampler(rig.document, rig.binary, 0)
            durations.append(reader.duration); relative = f'assets/{index}-{i}.glb'
            actors.append(dict(url=relative, sha256=sha256(path), placement=placement)); copies.append((path, relative))
        if durations[0] != durations[1] or versions and durations[0] != versions[0]['duration_s']:
            raise ValueError('Matching actual animation durations required')
        d = bound(study/'decoded.json'); floor = bound(study/'floor.json')
        floor_mm = max(max(v['exported_m']) for v in floor)*1000
        audit = f'audits/{index}-result.json'; copies.extend([(study/'result.json', audit), (study/'decoded.json', f'audits/{index}-decoded.json')])
        versions.append(dict(id=str(index), label=study.name.replace('-', ' ')+(' (diagnostic only)' if r.get('diagnostic_only') else ''), actors=actors, duration_s=durations[0],
            event_time_s=q['event_time_s'], contact_gap_m=d['contact']['gap_m'], guard_samples=r['guard_samples'],
            failed_geometry_samples=r['failed_geometry_samples'], maximum_depth_m=r['maximum_vertex_depth_m'],
            rate_failed_rows=[v['failed_rows'] for v in d['motion_rates']], motion_rates=d['motion_rates'],
            audit=audit, source_result_sha256=sha256(study/'result.json'), quality_approved=False,
            note=('Diagnostic replay; not selected by the solver. ' if r.get('diagnostic_only') else '')+f"Auxiliary hand-plane check: {('pass' if r['proposal_plane_clearance_pass'] else 'FAIL') if 'proposal_plane_clearance_pass' in r else 'not recorded'}. Recorded floor penetration: {floor_mm:.3f} mm. Original rate caps: {'pass' if r['original_motion_caps_pass'] else 'FAIL'}. Mesh evidence covers only the declared samples. No human quality approval or engine-import claim is made by this report."))
    output.mkdir(); (output/'assets').mkdir(); (output/'audits').mkdir()
    for path, relative in copies:
        shutil.copyfile(path, output/relative)
        if sha256(output/relative) != sha256(path): raise ValueError('Copied asset changed')
    for name, destination in [('native-contact-review.html', 'viewer.html'), ('native-contact-clock.mjs', 'native-contact-clock.mjs'), ('soma-preview-skin.js', 'soma-preview-skin.js')]:
        shutil.copyfile(ROOT/'scripts'/name, output/destination)
    shutil.copyfile(ROOT/'vendor/kimodo/LICENSE', output/'SOMA-preview-LICENSE.txt')
    save(output/'viewer-manifest.json', dict(at=now(), versions=versions,
        scope='Local canonical A/B development comparison. No Studio selection or review evidence is submitted.', browser_render_verified=False))
    for path, digest in verified.items():
        if sha256(path) != digest: raise ValueError('Source changed while packaging')
    save(output/'build.json', dict(at=now(), status='complete', inputs=verified, builder_sha256=sha256(__file__),
        outputs={p.relative_to(output).as_posix(): sha256(p) for p in output.rglob('*') if p.is_file()},
        browser_render_verified=False, studio_selection_changed=False, human_review_submitted=False, quality_approved=False))
    print(output/'viewer.html')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('output', type=Path); parser.add_argument('studies', type=Path, nargs='+')
    args = parser.parse_args(); run(args.studies, args.output)
