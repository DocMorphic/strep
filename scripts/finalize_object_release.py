"""Keep release experiments and open failures in the development evidence ledger."""
import shutil
from strep import ROOT,read,save,sha256,now


def main():
    out=ROOT/'reports/object-release-v2';verification=read(out/'verification.json');engine=read(out/'engine-http-verification.json')
    assert verification['passed'] and len(engine['objects'])==4
    summary=read(out/'summary.json')
    save(out/'decision.json',dict(at=now(),status='experimental_release_bake_implemented',
        floor_screen_passes=sum(c['floor_screens_passed'] for c in summary['cases']),cases=len(summary['cases']),
        engine_object_precision_passes=sum(c['position_screen_passed'] and c['rotation_screen_passed'] for c in engine['objects']),
        engine_scene_count=4,quality_approved=False,release_approved=False,
        retained_failures=['Original v1 contact-tolerance floor failures','Existing secondary-hand and body/box failures',
            'Seed-22 dynamic Godot playback rotation precision failure','Actor colliders omitted'],
        next='Integrate explicit dynamic-release authoring, extend collision representation and diagnose playback rotation discrepancy; retain the single broad project goal.'))
    sources=['scripts/object_release.py','scripts/godot_object_release.gd','scripts/study_object_release.py',
        'scripts/verify_object_release.py','scripts/verify_object_release_engine.py','scripts/godot_object_rotation_diagnostic.gd',
        'scripts/finalize_object_release.py','scripts/action_studio_server.py','scripts/action-studio.html',
        'scripts/scene-viewer.js','tests/test_object_release.py']
    files={}
    for name in sources:
        target=out/'final-implementation'/name;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/name,target);files[name]=sha256(target)
    save(out/'implementation.json',dict(at=now(),files=files))
    save(out/'test-results.json',dict(at=now(),full_suite=dict(passed=505,warnings=5,seconds=123.73,
        path='reports/object-release-full-tests.log',sha256=sha256(ROOT/'reports/object-release-full-tests.log')),
        focused=dict(passed=11,seconds=1.72,path='reports/object-release-tests-final.log'),frontend_syntax='passed'))
    matrix=read(ROOT/'benchmarks/project-release-v1.json')
    for capability in matrix['capabilities']:
        if capability['id'] in ['object_scene_interactions','game_engine_import','root_contact_event_export','reproducible_failure_reporting']:
            for name in ['docs/object-release-v1.md','reports/object-release-v2/verification.json',
                'reports/object-release-v2/engine-http-verification.json','reports/object-release-v2/decision.json']:
                if name not in capability['development_evidence']:capability['development_evidence'].append(name)
    matrix['last_progress_at']=now();matrix['last_progress']=dict(at=now(),summary='Offline dynamic object release and bake implemented; two original/candidate comparisons in Studio. Both revised candidates pass floor/settling screens, existing interaction failures retained. Actual engine bone checks pass; one box rotation precision check fails. Full suite505passes; no release approval.')
    save(ROOT/'benchmarks/project-release-v1.json',matrix)
    for name in ['README.md','docs/project-goal.md']:
        path=ROOT/name;text=path.read_text(encoding='utf-8-sig')
        if name=='README.md':
            old=next(line for line in text.splitlines() if line.startswith('Latest:'))
            new='Latest: [offline object release](docs/object-release-v1.md) simulates and bakes released boxes, with original/candidate comparisons in Studio. Both revised examples pass floor/settling screens; grip/body collisions remain failed, and one engine playback rotation precision check fails. Actor motion and authored events are preserved. Full suite: 505 passing tests. These are development results, with no animator or release approval.'
        else:
            old=next(line for line in text.splitlines() if line.startswith('Object dynamics diagnostics now'))
            new='Object dynamics diagnostics identified floating release tails; offline rigid-body release and baking are now implemented experimentally. Two revised examples pass floor/settling screens, with preserved actors/events and Studio comparisons. Existing interaction failures remain, and one engine playback rotation precision check fails. Full suite505passes. See `docs/object-release-v1.md`. Next: explicit release authoring, actor/environment colliders and playback fidelity, followed by the remaining broad release gates.'
        temporary=path.with_suffix('.md.tmp');temporary.write_text(text.replace(old,new),encoding='utf-8');temporary.replace(path)


if __name__=='__main__':main()
