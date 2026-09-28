"""Capture completed selected-output comparisons without using rejected candidate scores."""
import argparse
from pathlib import Path
from strep import read,save,sha256,now
from compare_support_iterations import selected_metrics
from support_comparison_protocol import match_studies


def run(before,after,pairs,version,kind='backtracking'):
    if not version or not version.replace('-','').isalnum():raise ValueError('Use a simple snapshot version')
    output=pairs/f'snapshot-{version}.json';captured_path=pairs/f'captured-results-{version}.json'
    if output.exists() or captured_path.exists():raise ValueError('Preserve earlier snapshots')
    bp=read(before/'protocol.json');ap=read(after/'protocol.json');match_studies(bp,ap,kind)
    captured=read(after/'results.json');byid={r['id']:r for r in captured['rows']};rows=[]
    for meta in ap['cases']:
        case=meta['id'];row={k:meta[k] for k in ('id','family','action','rig','eligible')}
        result=byid.get(case);path=pairs/case/'completion.json'
        row.update(study_status=result['status'] if result else 'pending',audit_status='pending' if meta['eligible'] else 'not_targeted')
        if meta['eligible'] and path.exists():
            pair=read(path)
            if pair['case']!=case or pair['comparison_kind']!=kind:raise ValueError('Wrong case or experiment')
            metrics=[];statuses=[];hashes=[]
            for study in (before,after):
                folder=study/case;r=read(folder/'result.json');audit=read(folder/'audit.json')
                if sha256(folder/'audit.json')!=r['audit_sha256'] or sha256(r['selected'])!=r['selected_sha256']:
                    raise ValueError('Selected output or audit changed')
                metrics.append(selected_metrics(audit,r));statuses.append(r['status']);hashes.append(r['selected_sha256'])
            if hashes!=[pair['before_sha256'],pair['after_sha256']]:raise ValueError('Pair measures other outputs')
            if sha256(path.parent/'timeline.json')!=pair['timeline_sha256']:raise ValueError('Timeline changed')
            row.update(audit_status='complete',completion_sha256=sha256(path),floor=pair['floor'],
                before_status=statuses[0],after_status=statuses[1],before_sha256=hashes[0],after_sha256=hashes[1],
                foot_peak_changes={k:v.get('peak_change') for k,v in pair['feet'].items()},
                root_peak_change=pair['root_acceleration']['peak_change'],root_local_increase=pair['root_acceleration']['maximum_pointwise_increase'],
                samples=pair['samples'],energy_before=metrics[0]['selected_energy'],energy_after=metrics[1]['selected_energy'])
        rows.append(row)
    save(captured_path,captured)
    summary=dict(at=now(),rows=rows,planned=len(rows),targeted=sum(c['eligible'] for c in ap['cases']),
        audited=sum(r['audit_status']=='complete' for r in rows),comparison_times=sum(r.get('samples',0) for r in rows),
        captured_results_sha256=sha256(captured_path),implementation_sha256=sha256(__file__),quality_approved=False,
        scope='Selected exported outputs only. Rejected candidate scores are excluded. Pending rows remain explicit; engine and human approval are separate.')
    save(output,summary);print({k:summary[k] for k in ('planned','targeted','audited','comparison_times')})


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for arg in ('before','after','pairs'):p.add_argument(arg,type=Path)
    p.add_argument('version');p.add_argument('--comparison-kind',choices=['iterations','backtracking'],default='backtracking')
    a=p.parse_args();run(a.before.resolve(),a.after.resolve(),a.pairs.resolve(),a.version,a.comparison_kind)
