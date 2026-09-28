"""All-frame serialized constraints at the solver's original normalized tolerance."""
import argparse
from pathlib import Path
import numpy as np
from strep import read, save, sha256, now
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler


def run(folder, output):
    if output.exists(): raise ValueError('Preserve existing diagnostic')
    done = read(folder/'completion.json'); request = read(folder/'request.json')
    if read(folder/'pipeline.json')['status'] != 'complete' or done['request_sha256'] != sha256(folder/'request.json'):
        raise ValueError('Completed unchanged trial required')
    for name, digest in done['files'].items():
        if sha256(folder/name) != digest: raise ValueError('Completed artifact changed')
    spec = read(folder/'take/spec.json'); envelope = read(folder/'take/fit-summary.json')
    rig = RigAsset.load(folder/'take/candidate/character.glb'); sampler = AnimationSampler(rig.document, rig.binary, 0)
    surfaces = np.array([rig.vertices(sampler.sample(float(np.float32(f/spec['fps'])))) for f in range(spec['frames'])])
    centers = np.stack([surfaces[:,p['vertices']].mean(axis=1) for p in spec['patches'].values()], axis=1)
    heights = np.stack([surfaces[:,p['vertices'],1].min(axis=1) for p in spec['patches'].values()], axis=1)
    acceleration = np.diff(centers, n=2, axis=0)*spec['fps']**2
    caps = np.asarray(envelope['safety_caps_m_s2'])
    acceleration_margin = (caps**2-np.sum(acceleration**2,axis=2))/np.maximum(caps**2,1.)
    velocity = np.diff(centers[:,:,[0,2]],axis=0)*spec['fps']; caps = np.asarray(envelope['support_speed_caps_m_s'])
    speed_margin = ((caps**2-np.sum(velocity**2,axis=2))/np.maximum(caps**2,.01**2))[np.asarray(envelope['support_steps'],bool)]
    active = np.zeros(heights.shape,bool)
    for side_index, side in enumerate(spec['patches']):
        for interval in read(Path(request['held'])/'input/contacts.json')['intervals']:
            if interval['joint'] in (side+'Foot',side+'ToeBase'):
                active[interval['start_frame']:interval['end_frame_exclusive'],side_index] = True
    hover_margin = ((np.asarray(envelope['hover_caps_m'])-heights)/.01)[active]
    values = np.load(folder/'take/parameters.npz',allow_pickle=False)['parameters']; differences = np.diff(values,axis=0)
    edits = []
    for column in range(0,values.shape[1],3):
        radius = spec['limits']['root_step_m'] if column == 0 else np.radians(spec['limits']['joint_step_degrees'])
        edits.extend(1-np.sum(differences[:,column:column+3]**2,axis=1)/radius**2)
    def minimum(data):
        data = np.asarray(data)
        if not np.isfinite(data).all(): raise ValueError('Nonfinite constraint margin')
        return float(data.min()) if data.size else None
    margins = dict(acceleration=minimum(acceleration_margin),support_speed=minimum(speed_margin),
        integer_floor=minimum((surfaces[:,:,1]+.005)/.005),hover=minimum(hover_margin),adjacent_edits=minimum(edits))
    checks = {key:value >= -1e-8 if value is not None else None for key,value in margins.items()}
    target = request.get('target'); target_value = None
    if target is not None:
        target_value = float(np.linalg.norm(acceleration[np.asarray(target['centers'])-1,target['side_index']],axis=1).max())
    result = dict(at=now(),study=str(folder),completion_sha256=sha256(folder/'completion.json'),implementation_sha256=sha256(__file__),
        minimum_normalized_margins=margins,checks=checks,all_applicable_checks_passed=all(v for v in checks.values() if v is not None),
        target_acceleration_max_m_s2=target_value,target_limit_m_s2=target['limit_m_s2'] if target else None,
        scope='Fresh all-integer-frame skin and adjacent-parameter constraints at original -1e-8 normalized tolerance. Empty support populations are N/A. Does not substitute for half-frame, rotation, root, absolute-edit, import or human checks; does not change original solver decisions.',quality_approved=False)
    save(output,result); print(result)
    return result


if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('folder',type=Path);p.add_argument('output',type=Path);a=p.parse_args();run(a.folder.resolve(),a.output.resolve())
