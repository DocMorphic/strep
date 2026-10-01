"""Replay imported raw-weight CPU skin at every bound engine audit time."""
import argparse
from pathlib import Path
import shutil
import numpy as np
from scipy.spatial.transform import Rotation
from strep import ROOT, read, save, sha256, now
from rig_asset import RigAsset
from imported_skin_reconstruction import ImportedSkin
from native_engine_clock import clock_echo_matches


def run(gpu_study, output):
    gpu_study,output=Path(gpu_study).resolve(),Path(output).resolve()
    if output.exists() or output.parent!=ROOT/'reports':raise ValueError('Fresh immediate reports output required')
    q,result=read(gpu_study/'request.json'),read(gpu_study/'result.json')
    if result['status']!='complete' or not result['passed']:raise ValueError('Passing GPU/imported-data evidence required')
    files=dict(q['inputs'])
    for name,digest in result['outputs'].items():
        path=(gpu_study/name).resolve()
        if not path.is_relative_to(gpu_study):raise ValueError('Escaping evidence')
        if str(path) in files and files[str(path)]!=digest:raise ValueError('Conflicting evidence')
        files[str(path)]=digest
    files[str(gpu_study/'result.json')]=sha256(gpu_study/'result.json')
    def unchanged():
        for path,digest in files.items():
            if sha256(path)!=digest:raise ValueError('Changed full-floor evidence')
    def bound(path):
        path=Path(path).resolve()
        if files.get(str(path))!=sha256(path):raise ValueError('Unbound full-floor input')
        return read(path)
    unchanged()
    engine=Path(q['engine_audit']);eq=bound(engine/'request.json');er=bound(engine/'engine-output.json')
    observed=bound(gpu_study/'engine-output.json')
    source_request=bound(Path(eq['study'])/'request.json')
    stance=source_request.get('floor_condition',{}).get('sampled_maximum_lowest_foot_height_m')
    if stance is not None and (not np.isfinite(stance) or stance<=0):raise ValueError('Invalid bound stance height')
    if len(q['cases'])!=len(eq['cases']) or len(er['cases'])!=len(q['cases']) or len(observed['cases'])!=len(q['cases']):raise ValueError('Actor population differs')
    output.mkdir();archive=output/'implementation';archive.mkdir()
    methods={}
    for name in (Path(__file__).name,'imported_skin_reconstruction.py','imported_skin_evidence.py','native_engine_clock.py','rig_asset.py','gltf_tools.py','strep.py','native_leg_floor.py','elbow_swivel.py','two_bone_waypoint.py','paired_approach_basis.py'):
        path=ROOT/'scripts'/name;methods[path]=sha256(path);shutil.copyfile(path,archive/name)
    save(output/'request.json',dict(at=now(),inputs=files,source=str(gpu_study),implementation={p.name:h for p,h in methods.items()},
        sampled_stance_maximum_lowest_height_m=stance,
        scope='Original topology and imported raw weights/binds on all bound observed world-joint samples. CPU formula reconstruction, not GPU vertex readback or continuous floor/contact certification.'))
    summaries=[]
    for index,(case,expected,actual,surface) in enumerate(zip(q['cases'],eq['cases'],er['cases'],observed['cases'])):
        if not case['id']==expected['id']==actual['id']==surface['id'] or len(surface['surfaces'])!=1 or len(actual['frames'])!=len(expected['sample_times_s']):raise ValueError('Actor/sample correspondence differs')
        rig=RigAsset.load(case['path']);primitive=rig.primitives[0];names=[rig.document['nodes'][n]['name'] for n in rig.joints]
        weights=np.zeros((len(primitive['positions']),len(names)))
        for column in range(primitive['joints'].shape[1]):np.add.at(weights,(np.arange(len(weights)),primitive['joints'][:,column]),primitive['weights'][:,column])
        skin=ImportedSkin(primitive['positions'],weights,names,rig.inverse,surface['surfaces'][0])
        rotation=Rotation.from_quat(case['placement']['rotation_xyzw']).as_matrix();translation=np.asarray(case['placement']['translation_m'])
        foot_regions=[]
        if stance is not None:
            from paired_approach_basis import BoundSkin
            from native_leg_floor import foot_region
            source_skin=BoundSkin(rig)
            for name in ('LeftFoot','RightFoot'):
                node=next(n for n in rig.joints if rig.document['nodes'][n]['name']==name)
                foot_regions.append((name,foot_region(source_skin,rig.parents,node)))
        rows=[]
        for time,frame in zip(expected['sample_times_s'],actual['frames']):
            if not clock_echo_matches(time,frame['requested_time_s']) or not clock_echo_matches(time,frame['actual_time_s']):raise ValueError('Imported-floor seek clock differs')
            points=skin.vertices(frame['bones'],actual['bone_names'])@rotation.T+translation
            height=float(points[:,1].min())
            rows.append(dict(time_s=time,actual_time_s=frame['actual_time_s'],minimum_height_m=height,depth_m=max(0.,-height),lowest_vertex=int(points[:,1].argmin())))
            if stance is not None:
                rows[-1]['feet']=[dict(foot=name,minimum_height_m=float(points[ids,1].min()),
                    samples_pass=bool(points[ids,1].min()>=-1e-8 and points[ids,1].min()<=stance)) for name,ids in foot_regions]
        save(output/f'actor-{index}-floor.json',rows)
        summaries.append(dict(actor=case['id'],samples=len(rows),minimum_height_m=min(r['minimum_height_m'] for r in rows),maximum_depth_m=max(r['depth_m'] for r in rows),
            samples_pass=all(r['depth_m']<=1e-8 for r in rows)))
        if stance is not None:
            summaries[-1]['stance_samples_pass']=all(f['samples_pass'] for r in rows for f in r['feet'])
            summaries[-1]['feet']=[dict(foot=name,vertices=len(ids),
                minimum_height_m=min(r['feet'][j]['minimum_height_m'] for r in rows),
                maximum_lowest_height_m=max(r['feet'][j]['minimum_height_m'] for r in rows)) for j,(name,ids) in enumerate(foot_regions)]
        print(summaries[-1],flush=True)
    unchanged()
    if any(sha256(p)!=digest for p,digest in methods.items()):raise ValueError('Full-floor method changed')
    save(output/'verification.json',dict(actors=summaries,passed=all(r['samples_pass'] and r.get('stance_samples_pass',True) for r in summaries),gpu_positions_read_back=False,continuous_floor_certified=False,quality_approved=False))
    save(output/'result.json',dict(at=now(),status='complete',outputs={p.name:sha256(p) for p in output.iterdir() if p.is_file()},quality_approved=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('gpu_study',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args();run(args.gpu_study,args.output)
