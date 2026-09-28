"""Verify profile provenance, text cache, matched outputs and authoring packages."""
import hashlib
import json
import zipfile
from pathlib import Path
import numpy as np
from strep import ROOT,read,save,sha256,now
from strep import model_directory
from action_requests import validate_batch,request_digest,conditioning_texts
from motion_profile import brief,resolved_segments
from kimodo.sanitize import sanitize_texts
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler


def run(folder):
    folder=Path(folder);batch=validate_batch(read(folder/'request.json'));state=read(folder/'pipeline.json')
    assert state['status']=='complete'
    assert state['request_sha256']==request_digest(batch)
    summary=read(folder/'summary.json');cache=read(folder/'conditioning/manifest.json')
    checkpoint=read(ROOT/'models/manifest.json')['models']['nvidia/Kimodo-SOMA-RP-v1.1']
    checkpoint_hash=sha256(model_directory(checkpoint)/'model.safetensors')
    assert checkpoint_hash==checkpoint['files_sha256']['model.safetensors']
    assert sorted(cache['entries'])==conditioning_texts(batch)
    assert cache['request_sha256']==request_digest(batch)
    for entry in cache['entries'].values():assert sha256(folder/'conditioning'/entry['file'])==entry['sha256']
    rows=[];motions={};manifest=[]
    for trial in summary['trials']:
        dest=folder/'takes'/trial['id'];request=trial['request'];record=read(dest/'generation-record.json')
        assert request==next(r for r in batch['requests'] if r['id']==request['id'])
        assert record['request_sha256']==request_digest(batch) and record['seed']==44
        assert record['checkpoint_sha256']==checkpoint_hash
        assert record['checkpoint_revision']==checkpoint['revision']
        assert record['diffusion_steps']==100 and record['postprocessing'] is False
        texts=sanitize_texts([s['prompt'] for s in resolved_segments(request)])
        assert all(t in cache['entries'] for t in texts)
        expected=brief(request)
        if expected is None:assert 'motion_brief' not in record and not (dest/'motion-brief.json').exists()
        else:
            assert record['motion_brief']==expected==trial['motion_brief']==read(dest/'motion-brief.json')
            assert sha256(folder/'profile-implementation/motion_profile.py')==expected['compiler_sha256']
            assert expected['response_validated'] is False
            assert expected['unmapped_stats']==[dict(id='endurance',label='Endurance',value=50)]
        assert len(record['timeline'])==2 and record['timeline'][-1]['end_frame_exclusive']==240
        assert record['timeline'][0]['prompt']==request['segments'][0]['prompt']
        for name,digest in trial['hashes'].items():assert sha256(dest/name)==digest
        with zipfile.ZipFile(dest/'animation-pack.zip') as package:
            assert package.testzip() is None
            for name in package.namelist():
                actual=(ROOT/'vendor/kimodo/LICENSE').read_bytes() if name=='LICENSE.txt' else (dest/name).read_bytes()
                assert package.read(name)==actual
            if expected is not None:assert 'motion-brief.json' in package.namelist()
            entries=len(package.namelist())
        motion=dict(np.load(dest/'motion.npz',allow_pickle=False));motions[request['id']]=motion
        assert len(motion['posed_joints'])==240
        rig=RigAsset.load(dest/'soma.glb');sampler=AnimationSampler(rig.document,rig.binary,0)
        error=0.;floor=[];half=[]
        for f in range(240):
            world=sampler.sample(float(np.float32(f/30)))
            error=max(error,float(np.max(np.abs(world[1:78,:3,3]-motion['posed_joints'][f]))))
            floor.append(max(0.,-float(rig.vertices(world)[:,1].min())))
            if f<239:half.append(max(0.,-float(rig.vertices(sampler.sample((f+.5)/30))[:,1].min())))
        assert error<1e-5
        rows.append(dict(id=trial['id'],profile_applied=expected is not None,source_sha256=sha256(dest/'motion.npz'),encoded_texts=texts,package_entries=entries,glb_pose_max_error_m=error,full_mesh_floor_depth_max_m=max(floor),half_frame_floor_depth_max_m=max(half),style_response_validated=False))
        manifest.append(dict(id=trial['id'],path=(dest/'soma.glb').relative_to(folder).as_posix(),sha256=sha256(dest/'soma.glb'),frames=240,fps=30))
    a,b=motions['plain-sequence'],motions['profile-sequence']
    delta=b['posed_joints']-a['posed_joints'];rms=float(np.sqrt(np.mean(delta**2)))
    # Distinct results establish conditioning changed the output, not whether
    # the requested profile is recognizable or physically realistic.
    assert rms>1e-5
    result=dict(created_at=now(),checks_passed=True,cases=rows,matched_pose_component_rms_difference_m=rms,model_unchanged=True,quality_approved=False,style_response_validated=False,scope='One composite profile and one seed over a two-action sequence. No per-stat attribution, monotonicity, biomechanical calibration or human review.')
    save(folder/'profile-verification.json',result);save(folder/'manifest.json',dict(cases=manifest))
    save(ROOT/'reports/motion-profile-v1/verification.json',result)
    print(result)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('folder',type=Path);run(p.parse_args().folder)
