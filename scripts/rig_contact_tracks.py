"""Load original prediction clocks or explicitly retimed contact intervals."""
from pathlib import Path
import numpy as np
from strep import read,sha256

ROLES=[side+part for side in ('Left','Right') for part in ('Foot','ToeBase','ToeEnd')]


def prediction_origin(data):
    """Keep missing prediction evidence unknown through joins, loops and retiming."""
    origin=data['origin'];parents=data.get('source_origins',[data.get('source_origin',origin)])
    if all(v=='none_supplied' for v in parents):return 'none_supplied'
    if any(v in ('none_supplied','partially_unknown') for v in parents):return 'partially_unknown'
    return origin


def signals(report):
    frames=report['frames'];masks={name:np.zeros(frames,dtype=bool) for name in ROLES}
    if report.get('timeline_edited'):
        path=Path(report['contact_annotations_file'])
        if sha256(path)!=report['contact_annotations_sha256']:raise ValueError('Retimed contact annotations changed')
        data=read(path)
        for interval in data['intervals']:
            a,b=interval['start_frame'],interval['end_frame_exclusive']
            if type(a) is not int or type(b) is not int or not 0<=a<b<=frames:raise ValueError('Contact interval does not match edited timeline')
            if interval['joint'] in masks:masks[interval['joint']][a:b]=True
        return masks,prediction_origin(data)
    if report.get('source_kind')=='gltf_animation':return masks,'none_supplied'
    from correct_stance import load_motion
    from inspect_motion import validate_motion
    motion=load_motion(report['source']);_,_,labels=validate_motion(motion,report['fps'])
    if len(motion['foot_contacts'])!=frames:raise ValueError('Prediction clock does not match motion')
    for name in masks:
        if name in labels:masks[name]=motion['foot_contacts'][:,labels.index(name)]>=.5
    return masks,'source_model_predictions'
