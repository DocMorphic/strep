"""Three-stage comparison using verified raw, coordinate and coupled results."""
from strep import ROOT,read,save


def build(out):
    report=read(out/'review-analysis.json')
    old=read(ROOT/'reports/pose-trajectory-v1/review-analysis.json')
    rows=[]
    for case in read(out/'protocol.json')['cases']:
        rows.append(next(r for r in report['cases'] if r['action']==case and r['condition']=='original'))
        coordinate=next(r for r in old['cases'] if r['action']==case and r['condition']=='candidate')
        rows.append(dict(coordinate,condition='coordinate'))
        rows.append(next(r for r in report['cases'] if r['action']==case and r['condition']=='candidate'))
    report['cases']=rows
    save(out/'review-analysis.json',report)
    html=(ROOT/'scripts/pose-trajectory-review.html').read_text(encoding='utf-8')
    html=html.replace('Bounded temporal target correction','Coordinated temporal target correction')
    html=html.replace('Original generated motion and bounded correction over a 31-frame window.',
        'Compare raw motion, the previous coordinate correction, and the coordinated candidate over the same 31-frame window. The default pair isolates the added coordinated correction.')
    html=html.replace('<option selected>original</option><option>candidate</option>',
        '<option>original</option><option selected>coordinate</option><option>candidate</option>')
    html=html.replace('<option>original</option><option selected>candidate</option>',
        '<option>original</option><option>coordinate</option><option selected>candidate</option>')
    html=html.replace('Original and candidate loaded. Neither is quality approved.',
        'Selected stages loaded. No stage is quality approved.')
    html=html.replace('Candidate is a deterministic edit with hard edit and neighbor-motion bounds.',
        'Coordinate is the previous per-frame correction. Candidate adds coordinated temporal controls with the same hard edit and neighbor-motion bounds and unchanged objective weights.')
    html=html.replace('../godot-pose-trajectory-v1/verification.json','../godot-coupled-pose-v1/verification.json')
    (out/'viewer.html').write_text(html,encoding='utf-8')


if __name__=='__main__':build(ROOT/'reports/coupled-pose-v1')
