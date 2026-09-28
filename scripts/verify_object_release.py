"""Audit preserved sources, baked scenes, subframes and portable packages."""
import argparse
import hashlib
import shutil
import zipfile
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from strep import ROOT,read,save,sha256,now
from rig_clip_import import AnimationSampler
from gltf_tools import read_glb
from object_release import audit_simulation,validate


def verify(out):
    out=Path(out).resolve();protocol=read(out/'protocol.json');manifest=read(out/'manifest.json');rows=[];engine_cases=[]
    for case in protocol['cases']:
        source=ROOT/case['source'];candidate=out/(case['id']+'-dynamic')
        for name,digest in case['files'].items():assert sha256(source/name)==digest
        original=read(source/'object-track.json');track=read(candidate/'object-track.json');scene=read(candidate/'scene.json')
        release=read(source/'attachment.json')['release_frame'];frames=len(track['positions_m'])
        assert track['positions_m'][:release+1]==original['positions_m'][:release+1]
        assert track['rotations_xyzw'][:release+1]==original['rotations_xyzw'][:release+1]
        assert scene['contacts']==read(source/'scene.json')['contacts']
        assert sha256(candidate/'events.json')==sha256(source/'events.json')
        assert sha256(ROOT/case['motion'])==case['motion_sha256']
        assert sha256(out/scene['actors']['A']['preview_glb'])==case['actor_glb_sha256']
        simfolder=out/(case['id']+'-simulation');simulation=read(simfolder/'engine-output.json')
        audit_simulation(validate(case['request']),simulation)
        stride=case['request']['physics_fps']//30
        expected=simulation['observations'][::stride]
        np.testing.assert_array_equal(track['positions_m'][release+1:],[o['position_m'] for o in expected[1:]])
        np.testing.assert_array_equal(track['rotations_xyzw'][release+1:],[o['rotation_xyzw'] for o in expected[1:]])
        base_doc,base_binary=read_glb(source/'portable/scene.glb');base_sampler=AnimationSampler(base_doc,base_binary,0)
        doc,binary=read_glb(candidate/'portable/scene.glb');sampler=AnimationSampler(doc,binary,0)
        box=next(i for i,n in enumerate(doc['nodes']) if n.get('name')=='Interaction_box')
        base_box=next(i for i,n in enumerate(base_doc['nodes']) if n.get('name')=='Interaction_box')
        joints=doc['skins'][0]['joints'];base_joints=base_doc['skins'][0]['joints']
        joint_error=0.;object_error=0.;depths=[]
        for frame in np.arange(0,frames-.5,.5):
            time=float(np.float32(frame/30));world=sampler.sample(time);base=base_sampler.sample(time)
            joint_error=max(joint_error,float(np.max(np.abs(world[joints]-base[base_joints]))))
            if frame<=release:np.testing.assert_allclose(world[box],base[base_box],atol=1e-7,rtol=0)
            if frame.is_integer():
                f=int(frame);np.testing.assert_allclose(world[box,:3,3],track['positions_m'][f],atol=1e-6,rtol=0)
                object_error=max(object_error,float(np.max(np.abs(world[box,:3,3]-track['positions_m'][f]))))
            bottom=world[box,1,3]-np.abs(world[box,1,:3])@(np.asarray(track['size_m'])/2)
            if frame>=release:depths.append(max(0.,-float(bottom)))
        assert joint_error<1e-7
        # Preserve the exporter's initial ZIP; create the enriched deliverable
        # only once, after adding the actual simulation inputs and observations.
        portable=candidate/'portable'
        for name in ['request.json','provenance.json','engine-output.json']:
            shutil.copyfile(simfolder/name,portable/('simulation-'+name))
        shutil.copyfile(candidate/'release-audit.json',portable/'release-audit.json')
        if not (candidate/'initial-scene-pack.zip').exists():shutil.copyfile(candidate/'scene-pack.zip',candidate/'initial-scene-pack.zip')
        with zipfile.ZipFile(candidate/'scene-pack.zip','w',zipfile.ZIP_DEFLATED) as archive:
            for path in portable.iterdir():archive.write(path,path.name)
        with zipfile.ZipFile(candidate/'scene-pack.zip') as archive:
            assert archive.testzip() is None
            for name in archive.namelist():assert hashlib.sha256(archive.read(name)).hexdigest()==sha256(portable/name)
        rows.append(dict(id=case['id'],preserved_inputs=True,events_preserved=True,contact_targets_preserved=True,
            actor_matrix_difference_max=joint_error,decoded_object_position_error_max_m=object_error,
            release_floor_depth_30fps_and_half_frames_max_m=max(depths),
            simulation_floor_depth_max_m=read(candidate/'release-audit.json')['simulated_floor_depth_max_m'],
            package_sha256=sha256(candidate/'scene-pack.zip'),physical_or_human_approved=False))
    for item in manifest['scenes']:
        path=Path(item['variants']['palm']).parent/'portable/scene.glb'
        engine_cases.append(dict(id=item['id'],path=path.as_posix(),frames=180,fps=30,sha256=sha256(out/path)))
    manifest['cases']=engine_cases;save(out/'manifest.json',manifest)
    save(out/'verification.json',dict(at=now(),cases=rows,passed=True,
        scope='Sources and actor unchanged, original object retained through release, simulation sampled on original clock, decoded frame/half-frame tracks and package bytes. Separate engine import and UI checks still required.'))
    print(rows)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('output',type=Path);args=parser.parse_args();verify(args.output)
