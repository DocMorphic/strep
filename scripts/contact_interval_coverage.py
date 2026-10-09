"""Complete contact-key coverage and deterministic failure-first work plans."""
import re
import numpy as np


def validate_frames(frames,*,maximum=1000):
    if type(maximum) is not int or not 2<=maximum<=1002:
        raise ValueError('Explicit frame capacity must be between two and1002')
    if (not isinstance(frames,list) or not 2<=len(frames)<=maximum
            or any(type(f) is not int or f<0 for f in frames)
            or frames!=list(range(frames[0],frames[0]+len(frames)))):
        raise ValueError(f'Two to{maximum} consecutive explicit native frames required')
    return frames


def partition_frames(frames,width=3):
    validate_frames(frames)
    if type(width) is not int or not 2<=width<=5:raise ValueError('Explicit bounded window width required')
    if width==2 and len(frames)%2:
        return [frames[i:i+2] for i in range(0,len(frames)-1,2)]+[frames[-2:]]
    count=(len(frames)+width-1)//width;size,extra=divmod(len(frames),count)
    start=0;windows=[]
    for i in range(count):
        end=start+size+(i<extra);windows.append(frames[start:end]);start=end
    assert sum(windows,[])==frames and all(2<=len(w)<=width for w in windows)
    return windows


def summarize_rows(frames,labels,slacks):
    # Up to1000 requested contact keys plus the two exterior body boundaries.
    validate_frames(frames,maximum=1002);slacks=np.asarray(slacks,dtype=float)
    if (not isinstance(labels,list) or not labels or len(set(labels))!=len(labels)
            or slacks.shape!=(len(labels),) or not np.isfinite(slacks).all()):
        raise ValueError('Complete finite uniquely labeled interval rows required')
    rows={frame:[] for frame in frames}
    for i,label in enumerate(labels):
        match=re.fullmatch(r'(.+):frame-(\d+)',label) if isinstance(label,str) else None
        if match is None or int(match[2]) not in rows:raise ValueError('Every row must bind an audited frame')
        rows[int(match[2])].append(i)
    if any(not ids for ids in rows.values()):raise ValueError('No audited frame may be omitted')
    result=[]
    for frame,ids in rows.items():
        values=slacks[ids];negative=np.minimum(values,0);failed=[labels[i] for i in ids if slacks[i]<0]
        families={}
        for label in failed:
            family=label.split(':',1)[0];families[family]=families.get(family,0)+1
        result.append(dict(frame=frame,row_count=len(ids),failed_rows=failed,failed_families=families,
            maximum_violation=float(-negative.min()),squared_violation=float(negative@negative),keyed_rows_passed=not failed))
    return dict(frames=result,audited_frames=frames.copy(),complete_keyed_rows_passed=all(r['keyed_rows_passed'] for r in result),
        quality_approved=False,release_approved=False)


def rank_windows(frames,summary,width=3):
    windows=partition_frames(frames,width);records={r['frame']:r for r in summary['frames']}
    if len(records)!=len(summary['frames']) or any(f not in records for f in frames):
        raise ValueError('Complete uniquely measured repair frames required')
    ranked=[]
    for window in windows:
        values=[records[f] for f in window]
        ranked.append(dict(frames=window,maximum_violation=max(r['maximum_violation'] for r in values),
            squared_violation=sum(r['squared_violation'] for r in values),failed_frames=[r['frame'] for r in values if not r['keyed_rows_passed']]))
    return sorted(ranked,key=lambda r:(-r['maximum_violation'],-r['squared_violation'],r['frames'][0]))


def select_window(frames,summary,width=3,exclusions=None):
    """Highest measured priority not yet attempted in an explicitly bound pass."""
    canonical={tuple(block) for block in partition_frames(frames,width)}
    exclusions=[] if exclusions is None else exclusions
    if (not isinstance(exclusions,list) or any(not isinstance(block,list) or any(type(f) is not int for f in block)
            or tuple(block) not in canonical for block in exclusions)
            or len({tuple(block) for block in exclusions})!=len(exclusions)):
        raise ValueError('Distinct complete canonical attempted windows required')
    ranked=summary['ranked_windows']
    if not isinstance(ranked,list) or len(ranked)!=len(canonical) or {tuple(r['frames']) for r in ranked}!=canonical:
        raise ValueError('Every measured canonical window must remain in the ranking')
    skipped={tuple(block) for block in exclusions}
    return next((r['frames'].copy() for r in ranked if tuple(r['frames']) not in skipped),None)
