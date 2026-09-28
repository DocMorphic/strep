"""Freeze then audit existing object tracks under explicit mass/inertia assumptions."""
import argparse
import shutil
import numpy as np
from scipy.spatial.transform import Rotation
from strep import ROOT,read,save,sha256,now
from object_dynamics import diagnose,uniform_box_inertia


OUT=ROOT/'reports/object-dynamics-v1'


def prepare():
    OUT.mkdir(exist_ok=False)
    cases=[]
    for seed in [11,22]:
        source=ROOT/f'reports/object-attachment-v1/palm-attached-box-seed-{seed}'
        destination=OUT/'inputs'/f'seed-{seed}';destination.mkdir(parents=True)
        files={}
        for name in ['object-track.json','scene.json','attachment.json','events.json']:
            shutil.copyfile(source/name,destination/name);files[name]=sha256(destination/name)
        cases.append(dict(id=f'seed-{seed}',source=str(source.relative_to(ROOT)).replace('\\','/'),
            inputs=str(destination.relative_to(OUT)).replace('\\','/'),files=files))
    implementation={}
    for name in ['scripts/object_dynamics.py','scripts/study_object_dynamics.py','tests/test_object_dynamics.py']:
        dest=OUT/'source-snapshot'/name;dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/name,dest);implementation[name]=sha256(dest)
    save(OUT/'protocol.json',dict(frozen_at=now(),cases=cases,implementation=implementation,
        mass_sensitivity_kg=[1.,5.,20.],mass_provenance='Hypothetical sensitivity values; no measured object mass is available.',
        inertia_provenance='Uniform-density solid box centered at the geometry origin; not measured.',
        gravity_m_s2=[0.,-9.81,0.],gravity_provenance='Assumed Y-up standard gravity.',
        support_provenance='Before grasp: unknown; attached: authored hand support; after release: unknown, not inferred free flight.',
        metrics=['required non-gravity net force','required COM torque','phase interiors','all boundary samples retained',
            'released object clearance above the Y=0 floor','release adjacent-interval velocity change'],
        derivative='Original sample clock, no smoothing or resampling; three-point differences and adjacent SO(3) logs.',
        thresholds=None,quality_approval=False,
        scope='Exploratory inverse-dynamics diagnostic on two already-seen failed attachment fixtures. No new motion, measured forces, human-body dynamics or held-out evaluation.',
        source='https://modernrobotics.northwestern.edu/nu-gm-book-resource/8-2-dynamics-of-a-single-rigid-body-part-1-of-2/'))


def run():
    protocol=read(OUT/'protocol.json')
    if (OUT/'summary.json').exists():raise ValueError('Preserve existing results')
    for name,digest in protocol['implementation'].items():
        assert sha256(ROOT/name)==digest and sha256(OUT/'source-snapshot'/name)==digest
    rows=[]
    for case in protocol['cases']:
        folder=OUT/case['inputs']
        for name,digest in case['files'].items():
            assert sha256(folder/name)==digest and sha256(ROOT/case['source']/name)==digest
        track=read(folder/'object-track.json');attachment=read(folder/'attachment.json')
        p=np.asarray(track['positions_m']);q=np.asarray(track['rotations_xyzw']);fps=track['fps']
        frames=len(p);grasp=attachment['grasp_frame'];release=attachment['release_frame']
        assert 0<grasp<release<frames-1
        phases=[dict(id='before-grasp',start_frame=0,end_frame_exclusive=grasp,support_assumption='unknown'),
            dict(id='attached',start_frame=grasp,end_frame_exclusive=release,support_assumption='supported'),
            dict(id='released',start_frame=release,end_frame_exclusive=frames,support_assumption='unknown')]
        r=Rotation.from_quat(q).as_matrix()
        bottom=p[:,1]-np.abs(r[:,1,:])@(np.asarray(track['size_m'])/2)
        incoming=(p[release]-p[release-1])*fps;outgoing=(p[release+1]-p[release])*fps
        scenarios=[]
        for mass in protocol['mass_sensitivity_kg']:
            report=diagnose(p,q,fps=fps,mass_kg=mass,inertia_body_kg_m2=uniform_box_inertia(mass,track['size_m']),
                gravity_m_s2=protocol['gravity_m_s2'],phases=phases)
            report['assumptions']={k:protocol[k] for k in ['mass_provenance','inertia_provenance','gravity_provenance','support_provenance']}
            dest=OUT/'results'/case['id']/f'mass-{mass:g}kg.json';save(dest,report)
            scenarios.append(dict(mass_kg=mass,path=dest.relative_to(OUT).as_posix(),sha256=sha256(dest),phases=report['phases']))
        rows.append(dict(id=case['id'],frames=frames,fps=fps,grasp_frame=grasp,release_frame=release,
            released_bottom_height_min_m=float(bottom[release:].min()),released_bottom_height_max_m=float(bottom[release:].max()),
            released_frames_above_1cm=int(np.sum(bottom[release:]>.01)),released_frames=frames-release,
            incoming_interval_velocity_m_s=incoming.tolist(),outgoing_interval_velocity_m_s=outgoing.tolist(),
            release_adjacent_interval_velocity_change_m_s=float(np.linalg.norm(outgoing-incoming)),
            boundary_note='Difference of adjacent secant velocities; not a measured impulse or a continuity proof.',
            scenarios=scenarios,quality_approved=False))
    save(OUT/'summary.json',dict(at=now(),protocol_sha256=sha256(OUT/'protocol.json'),cases=rows,
        release_approved=False,scope=protocol['scope']))
    print([(r['id'],r['released_bottom_height_min_m'],r['release_adjacent_interval_velocity_change_m_s']) for r in rows])


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['prepare','run']);args=parser.parse_args()
    prepare() if args.action=='prepare' else run()
