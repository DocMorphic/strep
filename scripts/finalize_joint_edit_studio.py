"""Record development integration evidence; never approve a release gate."""
from pathlib import Path
import shutil
from strep import ROOT,read,save,sha256,now


def main():
    out=ROOT/'reports/rig-joint-studio-v1'
    evidence=read(out/'verification.json')
    assert evidence['checks_passed']
    decision=dict(at=now(),status='implemented_experimental_editor',quality_approved=False,
        release_approved=False,targets_reached=sum(c['audit']['targets_reached'] for c in evidence['cases']),
        numerical_screen_passes=sum(c['audit']['numerical_screen_passed'] for c in evidence['cases']),
        cases=len(evidence['cases']),human_ratings=None,cleanup_time=None,
        next='Broaden scene/partner reliability and dynamics diagnostics under the existing project-wide goal.')
    save(out/'decision.json',decision)
    save(out/'ui-verification.json',dict(at=now(),url='http://127.0.0.1:8768/studio',
        job='20260927-044311-aab345bc',checks=['actual world-pose sample and target submission',
        'duplicate joint/frame rejected','draft survives close/reopen','completed job selected',
        'rejected floor/support status visible','input/candidate switching','frame 30',
        'playback 30 to 37 and pause','reset view displays whole grey character',
        'recipe/audit/package/root links present'],console_errors_observed=[],
        note='Manual browser inspection, not independent animator review. Scrolling over canvas zoomed it; Reset view restored framing.'))
    paths=['scripts/rig_joint_recipe.py','scripts/rig_joint_edit.py','scripts/rig_studio_job.py',
        'scripts/action_studio_server.py','scripts/action-studio.html','scripts/rig-joint-editor.js',
        'scripts/verify_joint_edit_studio.py','scripts/finalize_joint_edit_studio.py',
        'tests/test_rig_joint_recipe.py','tests/test_rig_joint_edit.py']
    snapshots={}
    for name in paths:
        dest=out/'final-implementation'/name;dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/name,dest);snapshots[name]=sha256(dest)
    save(out/'implementation.json',dict(at=now(),files=snapshots))
    matrix=read(ROOT/'benchmarks/project-release-v1.json')
    for capability in matrix['capabilities']:
        if capability['id'] in ['rough_clip_editing','explicit_contact_authoring','game_engine_import','reproducible_failure_reporting']:
            for item in ['docs/rig-joint-editing-v1.md','reports/rig-joint-studio-v1/verification.json',
                'reports/rig-joint-studio-v1/decision.json','reports/godot-rig-joint-studio-v1/verification.json']:
                if item not in capability['development_evidence']:capability['development_evidence'].append(item)
    matrix['last_progress_at']=now()
    matrix['last_progress']=dict(at=now(),summary='Imported-rig joint editing integrated and verified through API/Studio. Two requests meet targets, both rejected by floor/support screens. Six GLBs and 366 Godot frames pass structural checks; full suite 480 passes. No release approval.')
    save(ROOT/'benchmarks/project-release-v1.json',matrix)
    for name in ['README.md','docs/project-goal.md']:
        path=ROOT/name;text=path.read_text(encoding='utf-8-sig')
        if name=='README.md':
            old=next(line for line in text.splitlines() if line.startswith('Latest research:'))
            new='Latest: [imported-rig joint editing](docs/rig-joint-editing-v1.md) now works through Studio, with persistent targets, preserved inputs and independently audited exports. Both real requests reach their targets but remain rejected by floor/support screens. Six GLBs and 366 Godot frame checks pass structural validation; the full suite passes 480 tests. These are development results, with no animator or release approval. The [independent review workflow](docs/human-review-v1.md) is ready, with no actual ratings submitted.'
        else:
            old=next(line for line in text.splitlines() if line.startswith('Target-preserving refinement then'))
            new='Target-preserving refinement retained successful targets but gave negligible jump improvement and no dance improvement, so it was not promoted. Imported-rig joint editing is now integrated through the supervised worker/API and Studio. Both actual requests meet their targets while failing floor/support screens. Six GLBs and 366 Godot frames pass structural checks; the full suite has 480 passes. See `docs/rig-joint-editing-v1.md`. Continue broader interaction/dynamics reliability under this same goal.'
        temp=path.with_suffix(path.suffix+'.tmp');temp.write_text(text.replace(old,new),encoding='utf-8');temp.replace(path)


if __name__=='__main__':main()
