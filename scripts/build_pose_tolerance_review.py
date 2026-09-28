"""Compare verified raw, coordinated and target-feasibility outputs."""
from strep import ROOT,read,save


def build():
    out=ROOT/'reports/pose-tolerances-v1'
    assert read(out/'finalizer-state.json')['status']=='complete'
    report=read(out/'review-analysis.json');old=read(ROOT/'reports/coupled-pose-v1/review-analysis.json');rows=[]
    for case in read(out/'protocol.json')['cases']:
        rows.append(next(r for r in report['cases'] if r['action']==case and r['condition']=='original'))
        rows.append(dict(next(r for r in old['cases'] if r['action']==case and r['condition']=='candidate'),condition='coupled'))
        rows.append(next(r for r in report['cases'] if r['action']==case and r['condition']=='candidate'))
    report['cases']=rows;save(out/'review-analysis.json',report)
    html=(ROOT/'scripts/pose-trajectory-review.html').read_text(encoding='utf-8')
    html=html.replace('Bounded temporal target correction','Explicit joint-target tolerances')
    html=html.replace('Original generated motion and bounded correction over a 31-frame window.',
        'Compare raw motion, the coordinated correction, and the target-feasibility candidate over the same 31-frame window. The default pair isolates the tolerance stage.')
    html=html.replace('<option selected>original</option><option>candidate</option>',
        '<option>original</option><option selected>coupled</option><option>candidate</option>')
    html=html.replace('<option>original</option><option selected>candidate</option>',
        '<option>original</option><option>coupled</option><option selected>candidate</option>')
    html=html.replace('Original and candidate loaded. Neither is quality approved.','Selected stages loaded. No stage is quality approved.')
    html=html.replace('Candidate is a deterministic edit with hard edit and neighbor-motion bounds. Joint/floor targets are soft objectives and can be missed.',
        'Coupled is the previous coordinated correction. Candidate seeks separate position and orientation tolerances while preserving hard edit and neighbor-motion bounds. An unmet target is retained as a failure. Target success does not establish surface/contact quality; those errors may regress.')
    html=html.replace('../godot-pose-trajectory-v1/verification.json','../godot-pose-tolerances-v1/verification.json')
    html=html.replace('<h2>Review still required</h2>',
        '<p><a href="target-verification.json">Independent target acceptance and energy tradeoffs</a></p><h2>Review still required</h2>')
    (out/'viewer.html').write_text(html,encoding='utf-8')


if __name__=='__main__':build()
