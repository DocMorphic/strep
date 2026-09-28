"""Independent immutable-input, clock, glTF, package and HTTP verification."""
import argparse
import hashlib
import urllib.request
import zipfile
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from strep import ROOT,read,save,sha256,now
from object_release import audit_simulation,validate
from scene_constraints import sample_object
from gltf_tools import read_glb
from rig_clip_import import AnimationSampler


def verify(folder,output):
    folder=Path(folder).resolve();output=Path(output).resolve();request=read(folder/'request.json')
    assert read(folder/'pipeline.json')['status']=='complete'
    for name,digest in request['files'].items():assert sha256(folder/name)==digest
    original=read(folder/'input.json')['scene'];candidate=read(folder/'candidate.json')['scene'];release=request['authored']['release_frame'];name=request['authored']['object']
    assert original==read(folder/'source/bundle.json')['scene']
    assert candidate['actors']==original['actors'] and candidate['contacts']==original['contacts']
    source_bundle=read(folder/'source/original-bundle.json')['scene']
    for actor,entry in candidate['actors'].items():
        assert sha256(ROOT/entry['motion'])==source_bundle['actors'][actor]['source_sha256']
    for other in original['objects']:
        if other!=name:assert candidate['objects'][other]==original['objects'][other]
    track=read(folder/'object-track.json');base=read(folder/'source/object-track.json');frames=candidate['frame_count']
    for key in ['positions_m','rotations_xyzw']:assert track[key][:release+1]==base[key][:release+1]
    simulation=read(folder/'simulation/engine-output.json');audit_simulation(validate(request['physics']),simulation)
    samples=simulation['observations'][::request['physics']['physics_fps']//30]
    np.testing.assert_array_equal(track['positions_m'][release+1:],[s['position_m'] for s in samples[1:]])
    np.testing.assert_array_equal(track['rotations_xyzw'][release+1:],[s['rotation_xyzw'] for s in samples[1:]])
    events=read(folder/'events.json')['events'];assert events[:-1]==read(folder/'source/events.json')['events']
    assert events[-1]==dict(type='dynamic_release_start',object=name,frame=release,time_s=release/30,provenance='Authored bake request')
    decoded=[]
    for kind,scene in [('input',original),('candidate',candidate)]:
        path=folder/('objects.glb' if kind=='candidate' else 'input-objects.glb');doc,binary=read_glb(path);sampler=AnimationSampler(doc,binary,0)
        assert {n.get('extras',{}).get('strep_object_id') for n in doc['nodes']}==set(scene['objects'])
        for obj,entry in scene['objects'].items():
            node=next(i for i,n in enumerate(doc['nodes']) if n.get('extras',{}).get('strep_object_id')==obj)
            p,r=sample_object(entry,frames);pe=0.;re=0.;depth=0.
            for frame in np.arange(0,frames-.5,.5):
                matrix=sampler.sample(float(np.float32(frame/30)))[node]
                if frame.is_integer():
                    pe=max(pe,float(np.abs(matrix[:3,3]-p[int(frame)]).max()));re=max(re,float(np.abs(matrix[:3,:3]-r[int(frame)]).max()))
                bottom=matrix[1,3]-np.abs(matrix[1,:3])@(np.asarray(entry['size_m'])/2)
                if frame>=release:depth=max(depth,float(max(0.,-bottom)))
            assert max(pe,re)<1e-6
            decoded.append(dict(variant=kind,object=obj,position_error_m=pe,rotation_element_error=re,frame_and_half_frame_floor_depth_m=depth))
    with zipfile.ZipFile(folder/'scene-animation.zip') as archive:
        assert archive.testzip() is None
        for filename in archive.namelist():
            assert (folder/filename).resolve().is_relative_to(folder)
            if filename!='README.txt':assert hashlib.sha256(archive.read(filename)).hexdigest()==sha256(folder/filename)
    portable=read(folder/'portable-scene.json')
    for entry in portable['actors'].values():
        for field in ['motion','preview_glb']:
            path=(folder/entry[field]).resolve();assert path.is_relative_to(folder) and path.is_file()
    served=[]
    for filename in ['scene-animation.zip','objects.glb','input-objects.glb','events.json','candidate.json']:
        url='http://127.0.0.1:8768/files/'+folder.relative_to(ROOT/'reports').as_posix()+'/'+filename
        with urllib.request.urlopen(url,timeout=30) as response:data=response.read()
        assert hashlib.sha256(data).hexdigest()==sha256(folder/filename)
        served.append(dict(file=filename,sha256=sha256(folder/filename),bytes=len(data)))
    result=dict(at=now(),job=folder.relative_to(ROOT).as_posix(),saved_inputs_preserved=True,actor_motion_and_placements_preserved=True,contacts_and_prior_events_preserved=True,
        release_prefix_exact=True,simulation_clock_and_sampling_passed=True,decoded_objects=decoded,package_and_portable_paths_passed=True,served=served,
        scope='Preservation and artifact consistency; floor penetration/contact failures remain independent. Engine and human review are separate.',quality_approved=False)
    save(output,result);print(result,flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('folder');parser.add_argument('output');args=parser.parse_args();verify(args.folder,args.output)
