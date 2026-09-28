"""Check a future evaluation reservation against recorded development exposure."""
import argparse
from collections import Counter
from pathlib import Path
from inventory_development_prompts import normalize
from strep import ROOT, now, read, save, sha256


def screen(reservation,inventory,matrix):
    cases=reservation['cases'];design=matrix['evaluation_design']
    families={f['id'] for f in matrix['action_families']}
    old_prompts={p['normalized'] for p in inventory['prompts']}
    old_seeds={p['seed'] for p in inventory['seeds']}
    ids=[c['id'] for c in cases];texts=[normalize(c['prompt']) for c in cases]
    counts=Counter(c['family'] for c in cases);errors=[];prompt_overlap=[];seed_overlap=[]
    if len(set(ids))!=len(ids):errors.append('Duplicate case identifiers')
    if len(set(texts))!=len(texts):errors.append('Duplicate normalized prompts within reservation')
    if set(counts)!=families:errors.append('Reserved families differ from full release scope')
    for family in sorted(families):
        if counts[family]<design['minimum_prompts_per_family']:errors.append('Insufficient prompts: '+family)
    for c,text in zip(cases,texts):
        if not text:errors.append('Empty prompt: '+c['id'])
        if text in old_prompts:prompt_overlap.append(c['id'])
        seeds=c['seeds']
        if (len(set(seeds))<design['seeds_per_prompt'] or len(set(seeds))!=len(seeds)
            or any(type(s) is not int or not 0<=s<2**31 for s in seeds)):
            errors.append('Invalid or insufficient distinct seeds: '+c['id'])
        overlap=sorted(set(seeds)&old_seeds)
        if overlap:seed_overlap.append(dict(case=c['id'],seeds=overlap))
    if inventory['parse_errors']:errors.append('Inventory has unreadable inputs')
    return dict(cases=len(cases),families=dict(sorted(counts.items())),structural_errors=errors,
        exact_normalized_prompt_overlap=prompt_overlap,seed_overlap=seed_overlap,
        exact_overlap_screen_passed=not errors and not prompt_overlap and not seed_overlap,
        semantic_novelty_approved=False,checkpoint_training_independence_known=False,
        scene_assets_bound=False,release_trials_ready=False,quality_approved=False)


def run(reservation,inventory_folder,output):
    if output.exists():raise ValueError('Preserve earlier reservation checks')
    summary=read(inventory_folder/'summary.json');inventory=read(inventory_folder/'inventory.json')
    if summary['inventory_sha256']!=sha256(inventory_folder/'inventory.json'):
        raise ValueError('Inventory bytes changed')
    matrix=ROOT/'benchmarks/project-release-v1.json'
    result=screen(read(reservation),inventory,read(matrix))
    exempt=inventory.get('excluded_unexecuted_reservation_catalogs',{})
    allowed={reservation.relative_to(ROOT).as_posix():sha256(reservation)}
    if exempt and exempt!=allowed:
        raise ValueError('Inventory exempts more than this exact unexecuted reservation catalog')
    changed=[p for p,d in inventory['files'].items() if not (ROOT/p).is_file() or sha256(ROOT/p)!=d]
    result.update(at=now(),snapshot_files_changed_since_inventory=changed,
        inputs={str(p):sha256(p) for p in [reservation,inventory_folder/'inventory.json',inventory_folder/'summary.json',matrix]},
        implementation_sha256=sha256(Path(__file__)),
        scope='Exact normalized prompt and integer-seed screen against a dated development snapshot. Does not establish semantic novelty or unseen model training data. Scene/rig/partner fixtures, remaining acceptance gates, method freeze and human evaluation are still required. Refresh inventory before execution; do not tune on reserved trials.')
    if changed:result['exact_overlap_screen_passed']=False
    save(output/'verification.json',result)
    print({k:result[k] for k in ['cases','structural_errors','exact_normalized_prompt_overlap','seed_overlap','snapshot_files_changed_since_inventory','exact_overlap_screen_passed','release_trials_ready']})


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['reservation','inventory_folder','output']:parser.add_argument(name,type=Path)
    a=parser.parse_args();run(a.reservation.resolve(),a.inventory_folder.resolve(),a.output.resolve())
