"""Explicit motion descriptors and matched-speed/phase diagnostics, not stat estimates."""
import argparse
import itertools
from pathlib import Path
import numpy as np
from scipy.signal import find_peaks
from strep import ROOT,read,save,sha256,now
from profile_inputs import DEFAULT_STUDY
from correct_stance import load_motion
from correct_loops import repeat_motion,yaw_rotation
from inspect_motion import validate_motion,metrics,skeleton_metadata


def descriptors(data,fps=30):
    names,_,feet=validate_motion(data,fps)
    p=data['posed_joints'];root=data['root_positions'];n=len(root)
    speed=float((root[-1,2]-root[0,2])*fps/(n-1))
    # Canonical +Z travel in this pilot; signed lean distinguishes forward/backward.
    torso=p[:,names.index('Neck1')]-p[:,names.index('Hips')]
    lean=np.degrees(np.arctan2(torso[:,2],torso[:,1]))
    arm_ranges=[];knee_drive=[];stride_periods=[]
    for side in ('Left','Right'):
        arm=p[:,names.index(side+'Hand')]-p[:,names.index(side+'Arm')]
        arm_angle=np.unwrap(np.arctan2(arm[:,2],-arm[:,1]))*180/np.pi
        arm_ranges.append(float(np.percentile(arm_angle,95)-np.percentile(arm_angle,5)))
        thigh=p[:,names.index(side+'Shin')]-p[:,names.index(side+'Leg')]
        knee_drive.append(float(np.percentile(np.degrees(np.arctan2(thigh[:,2],-thigh[:,1])),95)))
        height=p[:,names.index(side+'Foot'),1]
        peaks,_=find_peaks(height,distance=max(1,round(.3*fps)),prominence=.03)
        if len(peaks)>1:stride_periods.extend((np.diff(peaks)/fps).tolist())
    period=float(np.median(stride_periods)) if stride_periods else None
    cadence=120/period if period else None
    contact=data['foot_contacts']
    return {'mean_forward_speed_m_s':speed,'cadence_steps_min':cadence,
        'stride_length_m':speed*period if period else None,'cadence_peak_intervals':len(stride_periods),
        'pelvis_vertical_p95_p5_m':float(np.percentile(root[:,1],95)-np.percentile(root[:,1],5)),
        'torso_forward_lean_median_degrees':float(np.median(lean)),
        'arm_swing_range_mean_degrees':float(np.mean(arm_ranges)),
        'knee_drive_p95_mean_degrees':float(np.mean(knee_drive)),
        'predicted_stance_fraction_left':float(contact[:,:3].any(1).mean()),
        'predicted_stance_fraction_right':float(contact[:,3:].any(1).mean())}


def speed_screen(data,study,displacement=None):
    root=data['root_positions'];fps=study['fps'];target=study['speed_m_s']
    if displacement is not None:
        speed=float(displacement[2]*fps/len(root))
    else:speed=float((root[-1,2]-root[0,2])*fps/(len(root)-1))
    expected=np.column_stack([np.zeros(len(root)),np.arange(len(root))/fps*target])
    relative=root[:,[0,2]]-root[0,[0,2]]
    error=np.linalg.norm(relative-expected,axis=1)
    p95=float(np.percentile(error,95))
    flags=[]
    if abs(speed-target)>target*study['speed_relative_tolerance']:flags.append('speed')
    if p95>study['pelvis_path_p95_tolerance_m']:flags.append('pelvis_path')
    return {'mean_forward_speed_m_s':speed,'pelvis_relative_path_error_p95_m':p95,'flags':flags,
        'accepted':not flags,'scope':'Pelvis XZ relative to its first sample; not the vendor smoothed-root constraint metric.'}


def canonical_cycle(data,count=64):
    names,_,_=skeleton_metadata(77);core,_,_=skeleton_metadata(30)
    indices=[names.index(name) for name in core]
    positions=data['posed_joints'][:,indices]-data['root_positions'][:,None]
    heading=data['global_rot_mats'][:,0,:,2].mean(0)
    rotation=yaw_rotation(-np.arctan2(heading[0],heading[2]))
    positions=positions@rotation.T
    t=np.arange(len(positions)+1)/len(positions);sample=np.arange(count)/count
    closed=np.concatenate([positions,positions[:1]]).reshape(len(positions)+1,-1)
    result=np.stack([np.interp(sample,t,closed[:,i]) for i in range(closed.shape[1])],axis=1)
    return result.reshape(count,len(indices),3)


def phase_distance(a,b):
    return min(float(np.sqrt(np.mean(np.sum((a-np.roll(b,shift,axis=0))**2,axis=-1)))) for shift in range(len(a)))


def main(folder,study_path):
    folder=Path(folder).resolve();study=read(study_path)
    summary={'created_at':now(),'study':study,'study_sha256':sha256(study_path),'trials':[],
        'definitions':{'cadence':'Twice the median same-foot peak frequency; 3 cm height prominence and 0.3 second peak separation. Null if no repeated peak.',
            'arm_swing':'Mean left/right 95th-to-5th percentile sagittal shoulder-to-wrist angle span.',
            'phase_distance':'30 core joints, pelvis translation removed, mean facing aligned, cycles resampled to 64 phases; minimum RMS over cyclic phase shifts. Metres; not a style-success criterion.'}}
    cycles={}
    for profile in study['profiles']:
        loops=read(folder/'loop'/profile['id']/'summary.json')['trials']
        stances=read(folder/'stance'/profile['id']/'summary.json')['trials']
        for loop,stance in zip(loops,stances):
            seed=loop['seed'];raw=load_motion(loop['source']);processed=load_motion(folder/'stance'/profile['id']/f'seed-{seed}/corrected.npz')
            loop_data=load_motion(folder/'loop'/profile['id']/f'seed-{seed}/corrected.npz')
            start,length=loop['source_start_frame'],loop['cycle_frames']
            crop={k:v[start:start+length].copy() for k,v in raw.items()}
            raw_delta=raw['root_positions'][start+length]-raw['root_positions'][start];raw_delta[1]=0
            delta=np.array(loop['cycle_displacement_m'])
            selected=repeat_motion(crop,raw_delta,4);repeated=repeat_motion(processed,delta,4)
            speed=speed_screen(processed,study,delta)
            final_flags=stance['regressions']+stance['screen']['screen_exceedances']+speed['flags']
            if not stance['improved']:final_flags.append('stance_improvement_not_demonstrated')
            trial={'id':profile['id']+f'-{seed}','profile':profile['id'],'seed':seed,'source_path':loop['source'],
                'source_sha256':loop['source_sha256'],'source_start_frame':start,'cycle_frames':length,
                'raw_cycle_displacement_m':raw_delta.tolist(),'processed_cycle_displacement_m':delta.tolist(),
                'raw_full_descriptors':descriptors(raw),'selected_raw_descriptors':descriptors(selected),
                'loop_descriptors':descriptors(repeat_motion(loop_data,delta,4)),'processed_descriptors':descriptors(repeated),
                'raw_speed_screen':speed_screen(raw,study),'processed_speed_screen':speed,
                'loop_report':loop,'stance_report':stance,'accepted_source':bool(stance['accepted'] and speed['accepted']),
                'flags':final_flags,'style_judgment':'unassessed: blind human review pending'}
            summary['trials'].append(trial)
            cycles[trial['id']]={'raw':canonical_cycle(crop),'processed':canonical_cycle(processed)}
    distances=[]
    for a,b in itertools.combinations(summary['trials'],2):
        same_profile=a['profile']==b['profile'];same_seed=a['seed']==b['seed']
        if not same_profile and not same_seed:continue
        distances.append({'a':a['id'],'b':b['id'],'kind':'within_profile' if same_profile else 'between_profiles_same_seed',
            'both_pass_source_screens':a['accepted_source'] and b['accepted_source'],
            'raw_m':phase_distance(cycles[a['id']]['raw'],cycles[b['id']]['raw']),
            'processed_m':phase_distance(cycles[a['id']]['processed'],cycles[b['id']]['processed'])})
    summary['phase_distances']=distances
    summary['counts']={'generated':len(summary['trials']),'accepted_source':sum(t['accepted_source'] for t in summary['trials'])}
    save(folder/'summary.json',summary)
    print(summary['counts'])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('folder',type=Path);p.add_argument('--study',type=Path,default=DEFAULT_STUDY)
    a=p.parse_args();main(a.folder,a.study)
