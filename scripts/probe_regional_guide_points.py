"""Enumerate explicitly alternative region guide points; never rewrite a scene."""
import argparse
import copy
from pathlib import Path
import shutil
import time
import numpy as np
import psutil
from scipy.spatial.transform import Rotation
from threadpoolctl import threadpool_limits
from strep import ROOT,read,save,sha256,now
from regional_pose_witness import RegionalPoseProblem
from rigid_contact_placement import placement_frame
from grasp_orientation import unit
from scene_region_contact import measure_frame,validate_binding
from study_regional_hand_placement import pure_hand_vertices


def orientations(normal,target_normal,tilt_degrees=9.5):
    if not np.isfinite(tilt_degrees) or not 0<tilt_degrees<90:raise ValueError('Tilt in (0,90) required')
    _,target,basis,base=placement_frame(normal,target_normal);result=[]
    for twist in range(0,360,45):
        spin=Rotation.from_rotvec(target*np.deg2rad(twist)).as_matrix()@base
        for tilt,azimuth in [(0,0)]+[(tilt_degrees,a) for a in range(0,360,45)]:
            axis=basis@np.array([np.cos(np.deg2rad(azimuth)),np.sin(np.deg2rad(azimuth))])
            matrix=Rotation.from_rotvec(axis*np.deg2rad(tilt)).as_matrix()@spin
            result.append(dict(twist_degrees=twist,tilt_degrees=tilt,azimuth_degrees=azimuth,
                rotation=matrix.tolist(),rotation_angle_degrees=float(np.rad2deg(np.linalg.norm(Rotation.from_matrix(matrix).as_rotvec())))))
    return result


def clearance_batch(vertices,anchors,matrix,point,geometry,position,rotation):
    """Full-hand queries in bounded caller-supplied anchor batches."""
    placed=(vertices[None]-anchors[:,None])@matrix.T+point
    distances=geometry.distance_gradient(placed.reshape(-1,3),position,rotation)[0].reshape(len(anchors),len(vertices))
    return distances.min(1),distances.argmin(1)


def run(source,output,seconds=180.):
    if type(seconds) not in [int,float] or not np.isfinite(seconds) or not 0<seconds<=600:raise ValueError('Bounded time required')
    source,output=Path(source).resolve(),Path(output).resolve();prior=read(source/'protocol.json');summary=read(source/'summary.json')
    if summary['status']!='complete' or summary['protocol_sha256']!=sha256(source/'protocol.json'):raise ValueError('Complete matching hand study required')
    for path,digest in prior['inputs'].items():
        if sha256(path)!=digest:raise ValueError('Source input changed')
    for name,digest in prior['methods'].items():
        if sha256(source/'implementation'/name)!=digest:raise ValueError('Source method snapshot changed')
    original=read(ROOT/prior['study']/'protocol.json');p=RegionalPoseProblem(ROOT/original['fit'],original['frame'])
    scene=read(ROOT/original['fit']/'authored-scene.json');seed=np.array(prior['seed_parameters'])
    output.mkdir(parents=True,exist_ok=False);snap=output/'implementation';snap.mkdir()
    for path in (ROOT/'scripts').glob('*.py'):shutil.copyfile(path,snap/path.name)
    inputs=dict(prior['inputs']);inputs.update({str(source/n):sha256(source/n) for n in ['protocol.json','summary.json']})
    shapes=[]
    for r in p.regions:
        contact=next(c for c in scene['contacts'] if c['id']==r['id']);hand=contact['region_contact']['hand']
        candidates=[row for row in summary['rows'] if row['hand']==hand]
        selected=max(candidates,key=lambda row:(row['minimum_hand_clearance_m'],-row['twist_degrees']))
        folder=ROOT/selected['folder'];result=read(folder/'result.json')
        if sha256(folder/'result.json')!=selected['result_sha256']:raise ValueError('Shape result changed')
        setup=read(folder.parent/'setup.json')
        if sha256(folder.parent/'setup.json')!=result['setup_sha256'] or result['protocol_sha256']!=sha256(source/'protocol.json'):raise ValueError('Shape setup changed')
        record=result['variants']['best_clearance'];path=folder/'best_clearance-unprojected.npz'
        if sha256(path)!=record['unprojected_pose_sha256']:raise ValueError('Shape pose changed')
        for q in [folder/'result.json',folder.parent/'setup.json',path]:inputs[str(q)]=sha256(q)
        for name,parameters in [('original_shape',seed),('searched_shape',np.array(record['parameters']))]:
            audit,motion=p.independent(parameters)
            if not audit['bounds_passed']:raise ValueError('Original source-relative edit bounds failed')
            if name=='searched_shape':
                saved=dict(np.load(path,allow_pickle=False))
                for key in motion:np.testing.assert_array_equal(motion[key],saved[key])
            vertices=p.surface.vertices(motion['global_rot_mats'][0],motion['posed_joints'][0]);ids=pure_hand_vertices(p.skin,p.parents,p.names.index(hand))
            if not set(r['ids']).issubset(set(ids)):raise ValueError('Region outside pure hand')
            tri=vertices[r['faces']];normal=unit(np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]).sum(0))
            if r['limits']['normal_degrees']<=9.5 or r['anchor_tolerance']<=.0049:raise ValueError('Grid exceeds original windows')
            shape=dict(hand=hand,name=name,parameters=parameters.tolist(),original_anchor=r['anchor'],
                source_shape=selected['folder'] if name=='searched_shape' else prior['warm_start']['study'],
                region_vertices=r['ids'].tolist(),hand_vertices=ids.tolist(),region_binding=contact['region_contact'],
                target=r['target'].tolist(),desired_normal=r['normal'].tolist(),orientations=orientations(normal,r['normal']))
            shapes.append((shape,r,vertices,ids,contact))
    protocol=dict(at=now(),source=source.relative_to(ROOT).as_posix(),inputs=inputs,methods={q.name:sha256(q) for q in snap.iterdir()},
        shapes=[s[0] for s in shapes],placement_gaps_m=[.0021,.0029,.0049],anchor_batch_size=16,seconds_budget=seconds,
        maximum_rss_bytes=2*1024**3,minimum_available_bytes=int(1.25*1024**3),
        selection='Enumerate every original region vertex for two declared frozen shapes, 72 orientations and three guide offsets. Rank passing candidates by smallest rigid rotation from their unprojected shape, centroid error, negative area, guide ID and stable enumeration index.',
        scope='Alternative guide binding only: original faces, region limits, normal definition, targets, finger budgets retained. Rigid hand reach/floor/body/self/partner/time constraints relaxed. No scene is overwritten, no skeleton is projected, original guide failure unchanged. Anatomical and developer review remain required.',quality_approved=False)
    save(output/'protocol.json',protocol);rows=[];started=time.monotonic();peak=0;status='complete';reason=None
    def guard():
        nonlocal peak
        rss=psutil.Process().memory_info().rss;peak=max(peak,rss)
        if time.monotonic()-started>seconds or rss>protocol['maximum_rss_bytes'] or psutil.virtual_memory().available<protocol['minimum_available_bytes']:
            raise TimeoutError('Guide-point enumeration resource guard')
    try:
        for shape_index,(shape,r,vertices,ids,contact) in enumerate(shapes):
            for anchor in r['ids']:
                effector=copy.deepcopy(contact['effector']);effector['surface_vertex']=int(anchor)
                validate_binding(contact['region_contact'],effector,p.skin)
            for oi,orientation in enumerate(shape['orientations']):
                matrix=np.array(orientation['rotation'])
                for gap in protocol['placement_gaps_m']:
                    point=r['target']-gap*r['normal']
                    for start in range(0,len(r['ids']),protocol['anchor_batch_size']):
                        guard();anchors=r['ids'][start:start+protocol['anchor_batch_size']]
                        minima,worst=clearance_batch(vertices[ids],vertices[anchors],matrix,point,r['geometry'],r['position'],r['rotation'])
                        for anchor,minimum,w in zip(anchors,minima,worst):
                            full=minimum>=p.config['object_clearance_m']-1e-6;measured=None
                            if full:
                                # Measure the unmodified full region independently of hand batching.
                                placed=(vertices-vertices[anchor])@matrix.T+point
                                measured=measure_frame(placed,r['ids'],r['faces'],r['target'],r['normal'],r['geometry'],r['position'],r['rotation'],r['limits'])
                            rows.append(dict(shape_index=shape_index,orientation_index=oi,anchor=int(anchor),placement_gap_m=gap,
                                minimum_hand_clearance_m=float(minimum),worst_vertex=int(ids[w]),full_hand_clearance_passed=bool(full),
                                region=measured,alternative_condition_passed=bool(full and measured['passed'] and gap<=r['anchor_tolerance'])))
                save(output/'progress.json',dict(status='running',pid=psutil.Process().pid,shape_index=shape_index,orientation_index=oi,placements=len(rows)))
            print(dict(hand=shape['hand'],shape=shape['name'],placements=len(rows),passes=sum(r['alternative_condition_passed'] for r in rows)),flush=True)
    except TimeoutError as exc:status='interrupted_resource_guard';reason=str(exc)
    ranked={}
    for hand in ['LeftHand','RightHand']:
        passing=[(i,row) for i,row in enumerate(rows) if row['alternative_condition_passed'] and protocol['shapes'][row['shape_index']]['hand']==hand]
        def key(item):
            i,row=item;shape=protocol['shapes'][row['shape_index']];triangle=row['region']['contact_triangle']
            return shape['orientations'][row['orientation_index']]['rotation_angle_degrees'],triangle['centroid_error_m'],-triangle['area_m2'],row['anchor'],i
        ranked[hand]=[dict(row_index=i,**row) for i,row in sorted(passing,key=key)[:8]]
    for path,digest in inputs.items():
        if sha256(path)!=digest:raise ValueError('Input changed')
    for name,digest in protocol['methods'].items():
        if sha256(ROOT/'scripts'/name)!=digest:raise ValueError('Method changed')
    result=dict(at=now(),status=status,reason=reason,seconds=time.monotonic()-started,peak_rss_bytes=peak,rows=rows,ranked=ranked,
        placements=len(rows),full_hand_clearance_passes=sum(r['full_hand_clearance_passed'] for r in rows),alternative_condition_passes=sum(r['alternative_condition_passed'] for r in rows),
        protocol_sha256=sha256(output/'protocol.json'),quality_approved=False)
    save(output/'result.json',result);save(output/'progress.json',{k:v for k,v in result.items() if k not in ['rows','ranked']})
    print({k:v for k,v in result.items() if k not in ['rows','ranked']},flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('source',type=Path);parser.add_argument('output',type=Path)
    parser.add_argument('--seconds',type=float,default=180.)
    args=parser.parse_args()
    with threadpool_limits(limits=2):run(args.source,args.output,args.seconds)
