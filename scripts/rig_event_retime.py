"""Remap frame-based intent without retaining approval for shifted event timing."""
import copy
import numpy as np


def retime(document,source_frames,source_hash):
    clock=np.asarray(source_frames,float)
    if clock.ndim!=1 or len(clock)<2 or not np.isfinite(clock).all() or np.any(np.diff(clock)<=0):
        raise ValueError('Increasing finite source-frame clock required')
    if document.get('fps',30)!=30 or not isinstance(document.get('events'),list):
        raise ValueError('Event document must use the 30 fps clip clock')
    result=copy.deepcopy(document);mapped=[];rows=[];dropped=[]
    for index,event in enumerate(document['events']):
        frame=event.get('frame')
        if type(frame) not in (int,float) or not np.isfinite(frame):
            raise ValueError('Finite numeric event frame required')
        if not clock[0]<=frame<=clock[-1]:
            dropped.append(index);continue
        ideal=float(np.interp(frame,clock,np.arange(len(clock))))
        output=int(np.floor(ideal+.5));error=(output-ideal)/30
        # Ignore only frame-domain floating-point residue, never a frame tick.
        shifted=abs(output-ideal)>1e-9
        review=event.get('requires_review') is not False or shifted
        record=dict(source_event_index=index,source_frame=frame,ideal_output_frame=ideal,
            output_frame=output,timing_error_s=error,rounded_timing_requires_review=shifted)
        mapped.append({**copy.deepcopy(event),'source_frame':frame,'frame':output,'time_s':output/30,
            'requires_review':review,'lineage':copy.deepcopy(event.get('lineage',[]))+[
                dict(operation='clip_retime',source_glb_sha256=source_hash,**record)]})
        rows.append(record)
    mapped.sort(key=lambda event:event['frame'])
    result.update(events=mapped,retiming='Nearest output frame, half ties round up. Shifted timing requires reconfirmation; outside-trim events are omitted and audited.')
    audit=dict(events=rows,dropped_event_indices=dropped,
        shifted_event_count=sum(row['rounded_timing_requires_review'] for row in rows),
        maximum_absolute_timing_error_s=max((abs(row['timing_error_s']) for row in rows),default=0.),
        numerical_frame_tolerance=1e-9,
        scope='Rounding relative to the source-frame edit clock, not verified contact or semantic timing.')
    return result,audit
