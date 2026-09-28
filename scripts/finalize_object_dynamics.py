"""Save diagnostic evidence without changing release acceptance."""
import shutil
from strep import ROOT,read,save,sha256,now
from study_object_dynamics import OUT


def main():
    verification=read(OUT/'verification.json');assert verification['passed']
    summary=read(OUT/'summary.json')
    save(OUT/'decision.json',dict(at=now(),status='diagnostic_completed',release_approved=False,
        finding='Both original post-release tracks remain stationary above the floor and require unaccounted upward force under the stated mass/gravity assumptions.',
        action='Implement an opt-in offline rigid-body release and bake policy with incoming velocity, explicit collision/material assumptions, preserved original and independent export/contact checks.',
        limitations='No contact-force allocation or human-body dynamics. No new generated motion or measured physical parameters. No animator approval.'))
    for name in ['scripts/verify_object_dynamics.py','scripts/finalize_object_dynamics.py']:
        dest=OUT/'verification-snapshot'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,dest)
    save(OUT/'verification-implementation.json',dict(at=now(),files={
        name:sha256(OUT/'verification-snapshot'/name) for name in ['scripts/verify_object_dynamics.py','scripts/finalize_object_dynamics.py']}))
    matrix=read(ROOT/'benchmarks/project-release-v1.json')
    for item in matrix['capabilities']:
        if item['id'] in ['object_scene_interactions','reproducible_failure_reporting']:
            for name in ['docs/object-dynamics-v1.md','reports/object-dynamics-v1/summary.json',
                'reports/object-dynamics-v1/verification.json','reports/object-dynamics-v1/decision.json']:
                if name not in item['development_evidence']:item['development_evidence'].append(name)
    matrix['last_progress_at']=now()
    matrix['last_progress']=dict(at=now(),summary='Joint-target Studio integration verified; two targets met but quality rejected. Added and verified object inverse-dynamics diagnostic across two preserved attachment exports and three explicitly assumed masses. Both authored release tails float above the floor. Dynamic release policy is next; all release gates remain open.')
    save(ROOT/'benchmarks/project-release-v1.json',matrix)
    path=ROOT/'docs/project-goal.md';text=path.read_text(encoding='utf-8-sig')
    paragraph='Object dynamics diagnostics now quantify the required net force/torque for declared mass/inertia/gravity and phases. Both existing attachment release tails remain stationary 37–40 cm above the floor. Their 360 exported samples and original inputs are independently checked; no physical approval is inferred. See `docs/object-dynamics-v1.md`. Next is an opt-in offline rigid-body release/bake policy, preserving originals and checking floor impact, actor contact, clocks and exports.\n\n'
    if paragraph not in text:
        text=text.replace('The independent human-review workflow',paragraph+'The independent human-review workflow')
        temporary=path.with_suffix('.md.tmp');temporary.write_text(text,encoding='utf-8');temporary.replace(path)


if __name__=='__main__':main()
