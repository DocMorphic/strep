"""Direct decoded comparison of an earlier result and an unpromoted pilot clip."""
import argparse
from pathlib import Path
from strep import read,sha256
from compare_midpoint_support import verified
from compare_support_iterations import selected_metrics
from audit_authoring_intent import check_files
from audit_support_iteration_pair import measure_pair


def run(before,pilot,case,output,reference='earlier'):
    if reference not in ('earlier','common-input'):
        raise ValueError('Use an earlier selected output or the bound common input')
    if output.exists():raise ValueError('Preserve previous pilot audit')
    bp,bc=verified(before);pp=read(pilot/'protocol.json')
    if pp['source_completion_sha256']!=sha256(before/'completion.json') or Path(pp['source']).resolve()!=before:
        raise ValueError('Pilot describes a different reference')
    if pp['population']!=bp['cases'] or pp['steps_per_block']!=bp['steps_per_block'] or pp['trusts']!=bp['trusts']:
        raise ValueError('Pilot reference population or solve budget differs')
    if pp['search_order']!='original_then_fallback' or case not in pp['pilot_cases']:
        raise ValueError('Not an explicitly planned fallback pilot case')
    check_files(pilot/'implementation',pp['implementation'])
    meta=next(c for c in bp['cases'] if c['id']==case)
    earlier=next(r for r in bc['rows'] if r['id']==case)
    old_audit=read(before/case/'audit.json');old_metrics=selected_metrics(old_audit,earlier)
    folder=pilot/case;result=read(folder/'result.json');audit=read(folder/'audit.json')
    candidate=folder/'take/candidate/character.glb'
    if result['status']!='evaluated' or result['candidate_sha256']!=sha256(candidate) or audit['candidate_sha256']!=sha256(candidate):
        raise ValueError('Pilot export identity changed or evaluation unfinished')
    if result['candidate_passes_common_input']!=audit['passed'] or old_audit['source_sha256']!=audit['source_sha256']:
        raise ValueError('Pilot check status or common source differs')
    check_files(folder/'base',meta['files'])
    earlier_path=Path(earlier['selected'])
    if sha256(earlier_path)!=earlier['selected_sha256']:raise ValueError('Earlier selected asset changed')
    reference_path=earlier_path if reference=='earlier' else folder/'base/selected/character.glb'
    if reference=='common-input' and sha256(reference_path)!=audit['source_sha256']:
        raise ValueError('Common-input export does not match audit source')
    paths=[reference_path,candidate]
    files=[before/'protocol.json',before/'completion.json',before/case/'audit.json',
        pilot/'protocol.json',folder/'result.json',folder/'audit.json',
        folder/'base/spec.json',folder/'base/input/contacts.json',*paths,
        Path(__file__).resolve(),Path(__file__).with_name('audit_support_iteration_pair.py').resolve()]
    inputs={str(p):sha256(p) for p in files}
    reference_peaks=({f['side']:f['selected_peak_m_s'] for f in old_metrics['feet']} if reference=='earlier'
                     else {f['side']:f['support_peak_before_m_s'] for f in audit['feet']})
    peaks=[reference_peaks,
           {f['side']:f['support_peak_after_m_s'] for f in audit['feet']}]
    measure_pair(paths,read(folder/'base/spec.json'),read(folder/'base/input/contacts.json'),
        peaks,output,case,'fallback_pilot' if reference=='earlier' else 'fallback_common_input',inputs)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('before',type=Path);p.add_argument('pilot',type=Path);p.add_argument('case');p.add_argument('output',type=Path)
    p.add_argument('--reference',choices=['earlier','common-input'],default='earlier')
    a=p.parse_args();run(a.before.resolve(),a.pilot.resolve(),a.case,a.output.resolve(),a.reference)
