"""Frozen CPU-only rig/engine diagnostic on every take in one breadth round."""
import argparse
import os
from pathlib import Path
import shutil
import sys
import traceback
import psutil
from strep import ROOT,read,save,sha256,now

IMPLEMENTATION=['breadth_transfer_study.py','retarget_rig.py','rig_asset.py','gltf_tools.py','correct_stance.py',
                'inspect_motion.py','audit_rig_ground.py','target_rig_contact.py','rig_contact_tracks.py',
                'run_godot_rig_import.py','godot_import_audit.gd']


def prepare(breadth,output,round_number):
    from breadth_study import validate_freeze,verify_complete
    breadth=Path(breadth).resolve();output=Path(output).resolve()
    if output.exists():raise ValueError('Preserve existing transfer study')
    frozen=validate_freeze(breadth);protocol=read(breadth/'protocol.json')
    cases=[c for c in protocol['cases'] if c['round']==round_number]
    if not cases:raise ValueError('No requested round')
    actors={c['id']+'-'+a['id'].lower():c for c in cases for a in c['actors']}
    expected={(i,s) for i,c in actors.items() for s in c['seeds']};found={}
    surface={}
    for batch in frozen['batches']:
        ids={r['id'] for r in read(ROOT/batch['request'])['requests']}
        if not ids.intersection(actors):continue
        if not ids<=actors.keys():raise ValueError('Mixed round batch')
        for t in verify_complete(batch):
            key=(t['request_id'],t['seed'])
            if key in found:raise ValueError('Repeated planned take')
            found[key]=(batch,t)
        for entry in read(breadth/'surface'/f'{batch["id"]}.json')['trials']:
            surface[(entry['request_id'],entry['seed'])]=entry['result']
    if set(found)!=expected:raise ValueError('Incomplete round; do not select successful takes only')
    output.mkdir(parents=True)
    rigs=[]
    for n,asset in enumerate(read(ROOT/'assets/characters/catalog.json')['characters']):
        source=ROOT/asset['file'];profile=ROOT/asset['profile']
        if sha256(source)!=asset['sha256'] or read(profile)['character_sha256']!=asset['sha256']:
            raise ValueError('Bundled rig/profile changed')
        name=f'rig-{n+1:02d}';folder=output/'rigs'/name;folder.mkdir(parents=True)
        shutil.copyfile(source,folder/'character.glb');shutil.copyfile(profile,folder/'profile.json')
        for label,path in asset['attachments'].items():shutil.copyfile(ROOT/path,folder/label)
        rigs.append(dict(id=name,label=source.stem,family='cesium' if 'cesium-man' in asset['file'] else 'quaternius-base',
                         directory=folder.relative_to(output).as_posix(),files={p.name:sha256(p) for p in folder.iterdir()}))
    motions=[]
    for key in sorted(found):
        batch,t=found[key];case=actors[key[0]];source=ROOT/batch['output']/'takes'/t['id']
        motions.append(dict(id=f'motion-{len(motions)+1:03d}',request_id=key[0],seed=key[1],case=case['id'],family=case['family'],
            prompt=t['request']['segments'][0]['prompt'],frames=t['frames'],fps=30,source=str(source/'motion.npz'),
            source_sha256=t['source_sha256'],native_glb=str(source/'soma.glb'),native_glb_sha256=t['hashes']['soma.glb'],
            flat_floor_screen_applicable=case['flat_floor_screen_applicable'],scene_validation=case['scene_validation'],
            native_mesh_depth_m=surface[key]['mesh_max_depth_m'] if surface[key] else None))
    (output/'implementation').mkdir()
    for name in IMPLEMENTATION:shutil.copyfile(ROOT/'scripts'/name,output/'implementation'/name)
    spec=dict(schema=1,created_at=now(),breadth_protocol_sha256=frozen['protocol_sha256'],round=round_number,rigs=rigs,motions=motions,
        cpu_threads=1,gpu_enabled=False,floor_screen_m=.01,planned_transfers=len(rigs)*len(motions),
        planned_engine_clips=(len(rigs)+1)*len(motions),
        implementation={name:sha256(ROOT/'scripts'/name) for name in IMPLEMENTATION},
        scope='Development transfer-only study on all actors/seeds of one fixed breadth round. Three existing assets, two rig families; not held-out rigs. No corrections, per-action profile changes, independent review or release approval.',
        timing_qualification='CPU transfer and headless engine work may overlap the separate frozen generation study. Do not use these wall times as isolated performance benchmarks.')
    save(output/'protocol.json',spec);save(output/'freeze.json',{'protocol_sha256':sha256(output/'protocol.json')})
    rows=[dict(id=m['id']+'-'+r['id'],motion=m['id'],rig=r['id'],status='pending',quality_approved=False) for m in motions for r in rigs]
    save(output/'results.json',dict(rows=rows,engine_groups=[],quality_approved=False))
    save(output/'pipeline.json',dict(status='prepared',planned_transfers=len(rows)))
    return spec


def validate(output):
    spec=read(output/'protocol.json')
    if sha256(output/'protocol.json')!=read(output/'freeze.json')['protocol_sha256']:raise ValueError('Protocol changed')
    for name,digest in spec['implementation'].items():
        if sha256(ROOT/'scripts'/name)!=digest:raise ValueError('Frozen transfer implementation changed: '+name)
    for rig in spec['rigs']:
        for name,digest in rig['files'].items():
            if sha256(output/rig['directory']/name)!=digest:raise ValueError('Frozen rig fixture changed')
    return spec


def summarize(spec,data):
    motions={m['id']:m for m in spec['motions']};rows=[]
    for item in data['rows']:
        m=motions[item['motion']];r=item.get('result',{});eligible=m['flat_floor_screen_applicable']
        depth=r.get('target_mesh_floor_depth_max_m');native=m['native_mesh_depth_m']
        rows.append(dict(**item,family=m['family'],case=m['case'],seed=m['seed'],
            flat_floor_screen_applicable=eligible,scene_validation=m['scene_validation'],
            native_mesh_depth_m=native,target_mesh_depth_m=depth,
            native_floor_screen=native<=spec['floor_screen_m'] if eligible and native is not None else None,
            target_floor_screen=depth<=spec['floor_screen_m'] if eligible and depth is not None else None,
            human_review=None))
    return dict(planned=spec['planned_transfers'],complete=sum(r['status']=='complete' for r in rows),
        failed=sum(r['status']=='failed' for r in rows),pending=sum(r['status'] in ['pending','running'] for r in rows),
        engine_groups=data['engine_groups'],rows=rows,quality_approved=False,
        scope='Import/transfer validity is separate from semantic correctness, support/contact and physical realism. Missing evidence remains missing.')


def audit_sidecars(folder,motion):
    import numpy as np
    from scipy.spatial.transform import Rotation
    from rig_asset import RigAsset
    from gltf_tools import sample_animation
    from inspect_motion import validate_motion,contact_events
    report=read(folder/'report.json');rig=RigAsset.load(folder/'character.glb')
    source=dict(np.load(motion['source'],allow_pickle=False));_,_,feet=validate_motion(source,30)
    root=read(folder/'root-motion.json');contacts=read(folder/'contacts.json');node=report['root_node']
    expected=source['root_positions']*report['scale_from_mean_leg_lengths']+report['world_offset_m']
    roots=np.array([sample_animation(rig.document,rig.binary,0,f)[node] for f in range(motion['frames'])])
    errors=dict(root_source_scale_offset_max_m=float(np.max(np.abs(roots[:,:3,3]-expected))),
                root_sidecar_position_max_m=float(np.max(np.abs(roots[:,:3,3]-root['positions_m']))),
                root_sidecar_basis_max=float(np.max(np.abs(roots[:,:3,:3]-Rotation.from_quat(root['rotations_xyzw']).as_matrix()))))
    if max(errors.values())>1e-5:raise ValueError('Decoded root/source/sidecar mismatch')
    if contacts['intervals']!=contact_events(source['foot_contacts'],feet,30):raise ValueError('Predicted contacts changed')
    np.testing.assert_allclose(root['times_s'],np.arange(motion['frames'])/30,atol=1e-6,rtol=0)
    save(folder/'sidecar-verification.json',dict(**errors,predicted_contacts_preserved=True))
    return errors


def run(output):
    output=Path(output).resolve();spec=validate(output)
    if read(output/'pipeline.json')['status']!='prepared':raise ValueError('Study already started; inspect its live process and preserve attempts')
    os.environ['CUDA_VISIBLE_DEVICES']='';os.environ['OMP_NUM_THREADS']='1';os.environ['MKL_NUM_THREADS']='1';os.environ['OPENBLAS_NUM_THREADS']='1'
    import torch
    torch.set_num_threads(1)
    from retarget_rig import export
    from audit_rig_ground import audit
    from run_godot_rig_import import run as engine
    owner=psutil.Process();save(output/'runner.json',dict(pid=owner.pid,created_at=owner.create_time(),status='running',started_at=now()))
    data=read(output/'results.json')
    try:
        for motion in spec['motions']:
            validate(output)
            for path,key in [('source','source_sha256'),('native_glb','native_glb_sha256')]:
                if sha256(motion[path])!=motion[key]:raise ValueError('Frozen source motion changed')
            group=output/'engine-groups'/motion['id'];group.mkdir(parents=True,exist_ok=False)
            cases=[dict(id=motion['id']+'-native',path=motion['native_glb'],sha256=motion['native_glb_sha256'],frames=motion['frames'],fps=30)]
            for rig in spec['rigs']:
                identifier=motion['id']+'-'+rig['id'];row=next(r for r in data['rows'] if r['id']==identifier)
                row.update(status='running',started_at=now());save(output/'results.json',data)
                save(output/'pipeline.json',dict(status='transfer',id=identifier,finished=sum(r['status'] in ['complete','failed'] for r in data['rows'])))
                folder=output/'takes'/identifier;fixture=output/rig['directory']
                try:
                    result=export(fixture/'character.glb',fixture/'profile.json',motion['source'],folder)
                    audit_sidecars(folder,motion)
                    ground=audit(folder) if motion['flat_floor_screen_applicable'] else None
                    hover=[x['hover_max_m'] for x in ground['foot_envelope_support'] if x['hover_max_m'] is not None] if ground else []
                    row.update(status='complete',finished_at=now(),result={k:result[k] for k in ['glb_sha256','frames','scale_from_mean_leg_lengths','roundtrip_max_matrix_error','roundtrip_max_vertex_error_m','target_mesh_floor_depth_max_m']},
                        predicted_support_foot_region_hover_max_m=max(hover) if hover else None,
                        sole_draft_error=ground['sole_draft_error'] if ground else None,
                        files={p.name:sha256(p) for p in folder.iterdir() if p.is_file()})
                    cases.append(dict(id=identifier,path=str(folder/'character.glb'),sha256=result['glb_sha256'],frames=motion['frames'],fps=30))
                except Exception as exc:
                    row.update(status='failed',error=str(exc),traceback=traceback.format_exc(),finished_at=now())
                save(output/'results.json',data);save(output/'coverage.json',summarize(spec,data))
                print(identifier+' '+row['status'],flush=True)
            save(group/'manifest.json',dict(cases=cases));save(output/'pipeline.json',dict(status='engine',motion=motion['id']))
            try:
                engine(group,group/'audit');proof=read(group/'audit/verification.json')
                data['engine_groups'].append(dict(motion=motion['id'],status='complete',expected_clips=len(spec['rigs'])+1,
                    verified_clips=len(proof['checks']),verification=str(group/'audit/verification.json'),checks=proof['checks']))
            except Exception as exc:
                data['engine_groups'].append(dict(motion=motion['id'],status='failed',error=str(exc),traceback=traceback.format_exc()))
            save(output/'results.json',data);save(output/'coverage.json',summarize(spec,data))
        failure=any(r['status']!='complete' for r in data['rows']) or any(g['status']!='complete' for g in data['engine_groups'])
        save(output/'pipeline.json',dict(status='complete_with_failures' if failure else 'complete',finished_at=now(),quality_approved=False))
    except BaseException as exc:
        save(output/'pipeline.json',dict(status='failed',error=str(exc),finished_at=now()));raise
    finally:save(output/'runner.json',dict(pid=owner.pid,created_at=owner.create_time(),status='stopped',finished_at=now()))


if __name__=='__main__':
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='command',required=True)
    a=sub.add_parser('prepare');a.add_argument('--breadth',type=Path,default=ROOT/'reports/breadth-baseline-v2');a.add_argument('--round',type=int,default=1)
    a.add_argument('--output',required=True,type=Path)
    b=sub.add_parser('run');b.add_argument('--output',required=True,type=Path)
    args=p.parse_args()
    if args.command=='prepare':print(prepare(args.breadth,args.output,args.round)['planned_transfers'])
    else:run(args.output)
