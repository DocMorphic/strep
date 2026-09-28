"""Build a verified refinement comparison with rejected requests still visible."""
from strep import ROOT, read, save


def build():
    out = ROOT / 'reports/target-refinement-v1'
    assert read(out / 'finalizer-state.json')['status'] == 'complete'
    audit = read(out / 'refinement-verification.json')
    assert audit['checks_passed']
    report = read(out / 'review-analysis.json')
    source = read(ROOT / 'reports/pose-tolerances-v1/review-analysis.json')
    protocol = read(out / 'protocol.json')
    rows = []
    for case in protocol['cases']:
        rows.append(next(r for r in report['cases'] if r['action'] == case and r['condition'] == 'original'))
        rows.append(dict(next(r for r in source['cases'] if r['action'] == case and r['condition'] == 'candidate'), condition='target-met'))
        rows.append(next(r for r in report['cases'] if r['action'] == case and r['condition'] == 'candidate'))
    report['cases'] = rows
    report['refinement'] = audit
    save(out / 'review-analysis.json', report)
    html = (ROOT / 'scripts/pose-trajectory-review.html').read_text(encoding='utf-8')
    replacements = {
        'Bounded temporal target correction': 'Target-preserving quality refinement',
        'Original generated motion and bounded correction over a 31-frame window.':
            'Compare the target-met input and quality refinement over the same 31-frame window. Raw motion is also available.',
        '<option value="get-up">Get up</option>': '',
        '<option selected>original</option><option>candidate</option>':
            '<option>original</option><option selected>target-met</option><option>candidate</option>',
        '<option>original</option><option selected>candidate</option>':
            '<option>original</option><option>target-met</option><option selected>candidate</option>',
        'Original and candidate loaded. Neither is quality approved.':
            'Selected stages loaded. No stage is quality approved.',
        'Candidate is a deterministic edit with hard edit and neighbor-motion bounds. Joint/floor targets are soft objectives and can be missed.':
            'Candidate minimizes quality cost while preserving reached joint targets, hard motion bounds, integer-frame floor depth and saved support limits. Half-frame behavior is audited separately. Predicted support is not confirmed contact.',
        '<h2>Review still required</h2>':
            '<h2>Refinement audit</h2><p id="refinement"></p><p><a href="refinement-verification.json">Independent guard, energy and half-frame measurements</a></p>'
            '<h2>Rejected input · Get up</h2><p>The get-up request missed the input joint tolerances and was not refined. It remains one of the three requested cases. '
            '<a href="../pose-tolerances-v1/viewer.html">Inspect its retained failed candidate</a>. Rejection does not prove the motion is impossible.</p><h2>Review still required</h2>',
        '../godot-pose-trajectory-v1/verification.json': '../godot-target-refinement-v1/verification.json',
        'Compare all three cases, including numerical failures.': 'Inspect both refined cases and the rejected get-up input.',
        'function table(){': '''function table(){const audit=report.refinement.cases.find(r=>r.case===$('action').value);$('refinement').textContent=`Quality cost ${audit.independent_energy.warm_start.toFixed(5)} → ${audit.independent_energy.after.toFixed(5)}. Joint targets and pre-export integer floor/support guards passed. Delivered GLB meets exact guard caps: ${audit.decoded_guard_caps_exactly_met?'yes':'no; inspect precision excess in the audit'}. Largest half-frame floor-depth change ${(audit.half_frame_floor_regression_max_m*1000).toFixed(4)} mm (positive means worse). This does not establish naturalness or physical contact.`;''',
        '${passed}/3 candidates meet target and floor screens. Edit bounds and preserved frames are separate checks. No action or contact approval.':
            '${passed}/${report.refinement.requested_case_count} requested cases meet target and floor screens after refinement; ${report.refinement.cases.length} eligible inputs were refined and ${report.refinement.rejected_inputs.length} input was rejected. No action or contact approval.',
    }
    for old, new in replacements.items():
        assert old in html, old
        html = html.replace(old, new)
    (out / 'viewer.html').write_text(html, encoding='utf-8')


if __name__ == '__main__':
    build()
