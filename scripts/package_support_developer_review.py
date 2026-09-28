"""Publish all completed support cases for a non-blind developer comparison."""
import argparse
from pathlib import Path
import zipfile
import hashlib
import math
from strep import ROOT, read, save, sha256, now
from audit_authoring_intent import check_files
from package_correction_review import checked_copy


def verified_pair(folder, identifier, before, after, comparison_kind='iterations'):
    audit=read(folder/'completion.json')
    if audit.get('comparison_kind','iterations') != comparison_kind:
        raise ValueError('Paired audit describes a different experiment kind')
    if audit['case']!=identifier or audit['before_sha256']!=sha256(before) or audit['after_sha256']!=sha256(after):
        raise ValueError('Paired audit describes different selected outputs')
    check_files(Path('.'),audit['inputs'])
    if sha256(folder/'timeline.json')!=audit['timeline_sha256']:
        raise ValueError('Paired sample timeline changed')
    return audit


def review_landmarks(audit, frames):
    """Expose measured witnesses, not a fabricated judgement of motion quality."""
    if audit is None:
        return []
    rows = []
    def add(label, frame):
        if frame is None:
            return
        if not math.isfinite(frame) or not 0 <= frame <= frames-1:
            raise ValueError('Review witness lies outside the clip')
        rows.append(dict(label=label, frame=frame))
    floor = audit['floor']
    if floor['worsened_samples']:
        add('Largest floor-depth increase', floor['worst']['frame'])
    root = audit['root_acceleration']
    if root['maximum_pointwise_increase'] > .0036:
        add('Largest root-acceleration increase', root['maximum_increase_frame'])
    for side, curve in audit['feet'].items():
        add(side+' support-speed peak', curve.get('candidate_peak_frame'))
    return rows


def build(coupled, output, subframes=None, baseline=None, paired_audits=None, comparison_kind='iterations'):
    if output.parent != ROOT/'reports/rig-jobs' or output.exists():
        raise ValueError('Use a new local rig-jobs review directory')
    complete = read(coupled/'completion.json'); protocol = read(coupled/'protocol.json')
    if complete['protocol_sha256'] != sha256(coupled/'protocol.json'):
        raise ValueError('Coupled protocol changed')
    check_files(coupled, complete['files'])
    if complete['engine_verification_sha256'] != sha256(coupled/'engine/verification.json'):
        raise ValueError('Coupled engine evidence changed')
    baseline_rows = {}
    if paired_audits is not None and baseline is None:
        raise ValueError('Paired-output evidence requires its baseline study')
    if baseline is not None:
        from compare_midpoint_support import verified
        from support_comparison_protocol import match_studies
        baseline_protocol, baseline_complete = verified(baseline)
        match_studies(baseline_protocol, protocol, comparison_kind)
        baseline_rows = {r['id']: r for r in baseline_complete['rows']}
    subframe_rows = {}
    if subframes is not None:
        sub_protocol, sub_done = read(subframes/'protocol.json'), read(subframes/'completion.json')
        if sub_protocol['completion_sha256'] != sha256(coupled/'completion.json') or sub_done['protocol_sha256'] != sha256(subframes/'protocol.json'):
            raise ValueError('Subframe audit belongs to different motion or changed protocol')
        check_files(subframes, sub_done['files'])
        subframe_rows = {r['id']: r for r in sub_done['rows']}
    summary_path = Path(protocol['summary'])/'summary.json'; summary = read(summary_path)
    if sha256(summary_path) != protocol['summary_sha256']:
        raise ValueError('Predecessor summary changed')
    previous = Path(summary['study']); prior_done = read(previous/'completion.json')
    if sha256(previous/'completion.json') != summary['study_completion_sha256']:
        raise ValueError('Predecessor completion changed')
    check_files(previous, prior_done['files'])
    population = read(ROOT/'reports/whole-support-breadth-v1/protocol.json')
    identifiers = [c['id'] for c in population['cases']]
    for label, entries in [('coupled protocol', protocol['cases']), ('coupled completion', complete['rows']),
                           ('root summary', summary['rows']), ('root completion', prior_done['rows'])]:
        if [r['id'] for r in entries] != identifiers:
            raise ValueError('Review population differs from source: '+label)
    output.mkdir(parents=True); prefix = f'/files/rig-jobs/{output.name}/'; rows = []
    for prior in prior_done['rows']:
        if prior['status'] == 'unfinished_source': continue
        if prior['status'] == 'failed': raise ValueError('Failed predecessor needs explicit review handling')
        identifier = prior['id']; folder = output/identifier
        meta = next(c for c in population['cases'] if c['id'] == identifier)
        rig = next(r for r in population['rigs'] if r['id'] == meta['rig'])
        current = next(r for r in complete['rows'] if r['id'] == identifier)
        root_summary = next(r for r in summary['rows'] if r['id'] == identifier)
        old = previous/identifier/'cleanup/selected'
        raw = ROOT/'reports/whole-support-breadth-v1/takes'/identifier/'input'
        original = read(previous/identifier/'original-verification.json')
        raw_trace = next(t for t in read(previous/identifier/'original-traces.json')['variants'] if t['variant']=='input')
        if sha256(old/'character.glb') != prior['selected_sha256']:
            raise ValueError('Previous selected package changed')
        new = coupled/identifier/'selected' if current['status'] in ('candidate_preserved', 'input_retained') else old
        if current['status']=='candidate_preserved' and sha256(new/'character.glb') != current['selected_sha256']:
            raise ValueError('New selected package changed')
        audit = read(coupled/identifier/'audit.json') if current['status'] in ('candidate_preserved','input_retained') else None
        approved = current['status']=='candidate_preserved'
        if approved and not audit['passed']: raise ValueError('Unverified candidate selection')
        def metrics(source, peaks):
            return dict(floor_depth_max_m=source.get('floor_depth_max_m'),
                half_frame_floor_depth_max_m=source.get('half_frame_floor_depth_max_m'),
                root_acceleration_max_m_s2=source.get('root_acceleration_max_m_s2'), support_peaks_m_s=peaks)
        raw_peaks = {s: f['predicted_support_max_m_s'] for s, f in raw_trace['feet'].items()}
        before_peaks = {s: f['after'] for s, f in root_summary['feet'].items()}
        prior_metrics = metrics(dict(floor_depth_max_m=root_summary['floor_after_m'],
            root_acceleration_max_m_s2=root_summary['root_peak_after_m_s2']), before_peaks)
        final_peaks = {f['side']: f['support_peak_after_m_s'] for f in audit['feet']} if approved else before_peaks
        latest_metrics = metrics(audit['original_verification']['metrics']['candidate'], final_peaks) if approved else prior_metrics
        choices = [('raw','Raw transfer',raw,metrics(original['metrics']['input'],raw_peaks)),
                   ('input','Before leg/root correction',old,prior_metrics),
                   ('selected','Selected result',new,latest_metrics)]
        earlier_audit = pair_audit = None
        if baseline is not None:
            earlier = baseline_rows[identifier]
            earlier_folder = baseline/identifier/'selected' if earlier['status'] in ('candidate_preserved','input_retained') else old
            if earlier['status'] in ('candidate_preserved','input_retained'):
                if sha256(earlier_folder/'character.glb') != earlier['selected_sha256']:
                    raise ValueError('Earlier selected package changed')
                earlier_audit = read(baseline/identifier/'audit.json')
                if sha256(baseline/identifier/'audit.json') != earlier['audit_sha256']:
                    raise ValueError('Earlier audit changed')
            earlier_metrics = prior_metrics
            if earlier['status']=='candidate_preserved':
                if not earlier_audit['passed']: raise ValueError('Earlier candidate was not retained validly')
                earlier_metrics = metrics(earlier_audit['original_verification']['metrics']['candidate'],
                    {f['side']:f['support_peak_after_m_s'] for f in earlier_audit['feet']})
            choices.insert(2,('earlier','Earlier correction',earlier_folder,earlier_metrics))
            choices[-1]=('selected','Further correction',new,latest_metrics)
            if paired_audits is not None and current['status'] in ('candidate_preserved','input_retained'):
                pair_audit=verified_pair(paired_audits/identifier,identifier,earlier_folder/'character.glb',new/'character.glb',comparison_kind)
        variants=[]
        for key, label, origin, measured in choices:
            files={name: checked_copy(origin/name,folder/key/name) for name in ('character.glb','root-motion.json','contacts.json')}
            variants.append(dict(id=key,label=label,glb=prefix+f'{identifier}/{key}/character.glb',
                sha256=files['character.glb'],root_track=prefix+f'{identifier}/{key}/root-motion.json',
                contacts=prefix+f'{identifier}/{key}/contacts.json',metrics=measured,files=files))
        for name,digest in rig['files'].items():
            if name!='character.glb': checked_copy(Path(population['source'])/rig['directory']/name,folder/'attribution'/name,digest)
        if approved:
            label='Numerical improvement retained · developer review pending'
        elif current['status']=='not_targeted':
            label='No measured foot-peak regression targeted · input retained'
        else: label='No accepted leg/root correction · input retained'
        unresolved = [f'{side} foot peak remains above the raw reference' for side in raw_peaks
            if raw_peaks[side] is not None and final_peaks[side] is not None and final_peaks[side] > raw_peaks[side]+.001]
        if max(latest_metrics.get('floor_depth_max_m') or 0., latest_metrics.get('half_frame_floor_depth_max_m') or 0.) > .005:
            unresolved.append('floor penetration exceeds 5 mm')
        if current['status']=='failed': unresolved.append('correction job failed; retained input shown')
        if pair_audit:
            floor=pair_audit['floor'];root=pair_audit['root_acceleration']
            if floor['worsened_samples']:
                unresolved.append(f"versus earlier correction, local floor depth increased by up to {floor['maximum_per_vertex_depth_increase_m']*1000:.4f} mm ({floor['worsened_samples']} sampled times)")
            if root['maximum_pointwise_increase']>.0036:
                unresolved.append(f"versus earlier correction, root acceleration increased locally by up to {root['maximum_pointwise_increase']:.3f} m/s²")
            for side, curve in pair_audit['feet'].items():
                if curve.get('peak_change') is not None and curve['peak_change'] > .001:
                    unresolved.append(f"versus earlier correction, {side.lower()} support-speed peak increased by {curve['peak_change']:.4f} m/s")
        subframe = subframe_rows.get(identifier)
        if subframe and 'selected_sha256' in subframe:
            if subframe['selected_sha256'] != sha256(new/'character.glb'):
                raise ValueError('Subframe audit selected motion changed')
            if subframe['worsened_samples']:
                unresolved.append(f"quarter-frame floor depth increased by up to {subframe['maximum_per_vertex_depth_increase_m']*1000:.4f} mm versus input ({subframe['worsened_samples']} samples)")
        note='; '.join(unresolved)+'.' if unresolved else 'These diagnostic comparisons pass; action quality and physical correctness still need review.'
        save(folder/'audit.json',dict(source_completion_sha256=sha256(coupled/'completion.json'),
            original_verification=original,root_cleanup_summary=root_summary,coupled_audit=audit,
            selection=current,subframe_audit=subframe,earlier_coupled_audit=earlier_audit,paired_output_audit=pair_audit,
            developer_reviews_collected=0,independent_human_reviews_collected=0,quality_approved=False))
        text=('Developer comparison, not a blind review or release approval. Compare action, timing, weight, '
              'foot contact and starts/ends at normal speed, then inspect individual frames. Report the case, '
              'version and frame range when something looks wrong. Raw transfer precedes contact/root correction. '
              'Selected result retains the input if the leg/root candidate failed. Contact annotations are predictions. '
              'The floor figure for the middle version includes key and midpoint samples; a separate midpoint '
              'figure is unavailable. Original rig attribution is in attribution/. No ratings are prefilled.\n'+
              ('Earlier and further corrections share the same source and physical limits; only the '+
               ('solver iteration budget' if comparison_kind=='iterations' else 'backtracking fraction schedule')+
               ' differs. Local floor/root differences are numerical diagnostics, not animator ratings.\n' if baseline is not None else '')+note+'\n')
        (folder/'README.txt').write_text(text,encoding='utf8')
        files={p.relative_to(folder).as_posix():sha256(p) for p in folder.rglob('*') if p.is_file()}
        with zipfile.ZipFile(folder/'review-pack.zip','x',zipfile.ZIP_DEFLATED) as z:
            for name in sorted(files):z.write(folder/name,name)
        with zipfile.ZipFile(folder/'review-pack.zip') as z:
            if {n:hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist()}!=files:raise ValueError('Review archive changed')
        spec=read(previous/identifier/'contact-spec.json')
        rows.append(dict(id=identifier,label=meta['motion']['case'].replace('_',' ').replace('-',' ')+' · '+rig['label'],
            status=current['status'],status_label=label,default_variant='selected',variants=variants,
            frames=spec['frames'],fps=30,root_node=spec['root_node'],prompt=meta['motion']['prompt'],seed=meta['motion']['seed'],
            failed_checks=[],review_note=note,review_landmarks=review_landmarks(pair_audit,spec['frames']),
            blocks=len(read(coupled/identifier/'selection.json')['blocks']) if audit else 0,
            package=prefix+f'{identifier}/review-pack.zip',audit=prefix+f'{identifier}/audit.json',
            license=prefix+f'{identifier}/attribution/LICENSE.md',quality_approved=False))
    unfinished = sum(r['status']=='unfinished_source' for r in prior_done['rows'])
    if len(rows)+unfinished != len(identifiers):
        raise ValueError('Review population accounting mismatch')
    save(output/'catalog.json',dict(schema='strep-correction-review-v1',at=now(),cases=rows,planned=len(identifiers),unfinished_source=unfinished,
        developer_reviews_collected=0,independent_human_reviews_collected=0,quality_approved=False,
        scope=f'Non-blind developer comparison of all {len(rows)} completed source cases, including retained inputs. No human ratings fabricated.'))
    save(output/'package-verification.json',dict(at=now(),source_completion_sha256=sha256(coupled/'completion.json'),
        implementation_sha256=sha256(__file__),files={p.relative_to(output).as_posix():sha256(p) for p in output.rglob('*') if p.is_file()},
        cases=len(rows),variants=sum(len(r['variants']) for r in rows),quality_approved=False))
    print(dict(cases=len(rows),variants=sum(len(r['variants']) for r in rows),catalog=prefix+'catalog.json'))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('study',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--subframes',type=Path)
    p.add_argument('--baseline',type=Path);p.add_argument('--paired-audits',type=Path)
    p.add_argument('--comparison-kind',choices=['iterations','backtracking'],default='iterations')
    a=p.parse_args();build(a.study.resolve(),a.output.resolve(),a.subframes.resolve() if a.subframes else None,
        a.baseline.resolve() if a.baseline else None,a.paired_audits.resolve() if a.paired_audits else None,a.comparison_kind)
