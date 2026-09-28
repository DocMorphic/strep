"""Portable actor assets, placements and retained failures for generated scenes."""
import argparse
import copy
import hashlib
import json
import zipfile
from pathlib import Path
from strep import ROOT,read,save,sha256,now


def contact_events(scene):
    events=[]
    for contact in scene['contacts']:
        for kind,frame in [('contact_window_start',contact['start_frame']),('contact_window_end',contact['end_frame']+1)]:
            events.append(dict(type=kind,actor=contact['actor'],contact_id=contact['id'],frame=frame,time_s=frame/scene['fps']))
    events.sort(key=lambda e:(e['frame'],e['actor'],e['contact_id'],e['type']))
    return dict(fps=scene['fps'],events=events,provenance='Authored contact windows, not detected or successful contact. End events use the exclusive end frame.')


def pack(folder,engine_report=None):
    folder=Path(folder);manifest=read(folder/'manifest.json');quality=read(folder/'scene-quality-audit.json')
    if quality['status']!='complete':raise ValueError('Finish independent scene audits before packaging')
    checks=[];trials={t['id']:t for t in read(folder/'summary.json')['trials']}
    engine=read(engine_report) if engine_report else None
    for item in manifest['scenes']:
        path=folder/item['variants']['palm'];bundle=read(path);scene=copy.deepcopy(bundle['scene'])
        evidence=next(r for r in quality['scenes'] if r['scene_id']==scene['id'])
        if evidence['scene_sha256']!=sha256(path):raise ValueError('Scene changed after audit')
        scene['review_note']='Independent raw checkpoint samples with '+('fitted contact-pose guides.' if 'guided' in scene['id'] else 'text-only conditioning.')+' Shared authored placement and clock; no joint scene model or collision correction. All candidates unreviewed.'
        files={};mapping={}
        for i,(name,entry) in enumerate(scene['actors'].items()):
            take=(ROOT/entry['motion']).parent;prefix=f'actors/actor-{i}/'
            if sha256(take/'motion.npz')!=entry['source_sha256']:raise ValueError('Actor changed after scene audit')
            for filename in ['motion.npz','motion.bvh','soma.glb','root-motion.json','contacts.json','generation-record.json','timeline.json','request.json','evidence.json']:
                if sha256(take/filename)!=trials[take.name]['hashes'][filename]:raise ValueError('Export changed before packaging: '+filename)
                files[prefix+filename]=(take/filename).read_bytes()
            if (take/'constraint-audit.json').exists():
                if sha256(take/'constraint-audit.json')!=trials[take.name]['hashes']['constraint-audit.json']:raise ValueError('Constraint audit changed before packaging')
                files[prefix+'constraint-audit.json']=(take/'constraint-audit.json').read_bytes()
            entry['motion']=prefix+'motion.npz';entry['preview_glb']=prefix+'soma.glb';mapping[name]=prefix
        files['scene.json']=(json.dumps(scene,indent=2)+'\n').encode()
        files['events.json']=(json.dumps(contact_events(scene),indent=2)+'\n').encode()
        files['godot_clip_adapter.gd']=(ROOT/'scripts/godot_clip_adapter.gd').read_bytes()
        if engine:
            imported=[c for c in engine['checks'] if c['scene_id']==scene['id']]
            if len(imported)!=len(scene['actors']) or {c['actor'] for c in imported}!=set(scene['actors']):raise ValueError('Engine evidence does not cover scene actors')
            for check in imported:
                entry=scene['actors'][check['actor']]
                if check['source_sha256']!=entry['source_sha256'] or check['glb_sha256']!=hashlib.sha256(files[entry['preview_glb']]).hexdigest():
                    raise ValueError('Engine evidence belongs to a different actor asset')
            files['evaluation/engine-import.json']=(json.dumps({**engine,'checks':imported},indent=2)+'\n').encode()
        for filename in ['orientation.json','partner-surface-audit.json','quality-audit.json','actor-placement.json']:
            files['evaluation/'+filename]=(path.parent/filename).read_bytes()
        files['evaluation/contact-evaluation.json']=(json.dumps(bundle['evaluation'],indent=2)+'\n').encode()
        files['SOMA-preview-LICENSE.txt']=(folder/'SOMA-preview-LICENSE.txt').read_bytes()
        files['README.txt']=('Experimental generated interaction; NOT approved for release.\n'
            'Import each actors/actor-N/soma.glb as a separate animated character.\n'
            'Actor names map to folders in manifest.json. Apply scene.json actor transform to a parent of each character.\n'
            'Use one shared 30 fps clock; play once and hold the final key. Coordinates are metres, Y-up.\n'
            'Root tracks are native SOMA Hips transforms; do not apply the placement twice.\n'
            'Contact targets and object tracks in scene.json are authored scene specifications, not generated geometry or collision constraints.\n'
            'Foot-contact files are model predictions, not confirmed gameplay events.\n'
            'events.json contains authored contact-window start/end markers, not verified contact success.\n'
            'The optional Godot adapter emits these markers. Filter events by actor when binding each actor clip, and hold the terminal frame before binding markers at the clip end.\n'
            'Evaluation records retain target/orientation/penetration failures. Scene bodies and hand contact need cleanup.\n'
            'Original generation records retain project paths as provenance. Portable actor asset paths are in scene.json.\n').encode()
        hashes={name:hashlib.sha256(data).hexdigest() for name,data in files.items()}
        files['manifest.json']=(json.dumps(dict(schema_version=1,scene_id=scene['id'],source_scene_sha256=sha256(path),
            actor_directories=mapping,files_sha256=hashes,release_approved=False,flags=evidence['flags']),indent=2)+'\n').encode()
        target=path.parent/'scene-package.zip'
        if target.exists():raise FileExistsError('Keep existing scene packages; choose a new output for changed data')
        with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as archive:
            for name,data in files.items():archive.writestr(name,data)
        with zipfile.ZipFile(target) as archive:
            if set(archive.namelist())!=set(files) or any(archive.read(name)!=data for name,data in files.items()):
                raise ValueError('Scene package verification failed')
        item['downloads'].insert(0,dict(label='Scene assets + diagnostics · ZIP',path=target.relative_to(folder).as_posix()))
        item['review_note']=scene['review_note']
        checks.append(dict(scene_id=scene['id'],zip_sha256=sha256(target),files=len(files),verified=True))
    save(folder/'manifest.json',manifest);save(folder/'scene-package-verification.json',dict(created_at=now(),packages=checks))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('folder',type=Path);parser.add_argument('--engine-report',type=Path);args=parser.parse_args();pack(args.folder,args.engine_report)
