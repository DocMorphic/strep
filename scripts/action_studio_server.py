"""Loopback-only authoring UI, real local generation and restricted artifact serving."""
import argparse
import json
import mimetypes
import subprocess
import sys
import threading
import uuid
import re
from datetime import datetime
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit,unquote,parse_qs
from strep import ROOT,read,save,offline_environment
from action_requests import validate_batch
from action_worker_lock import worker_busy

CORRECTION_STUDIES = ['contact-authoring-v2', 'support-contact-v1', 'body-contact-v1', 'body-contact-holdout-v1', 'floor-contact-v1-reviewed', 'floor-contact-holdout-v1']


def allowed_file(url_path):
    path=unquote(urlsplit(url_path).path)
    if path in ['/','/studio']:return ROOT/'scripts/action-studio.html'
    if path=='/motion-profile-editor.js':return ROOT/'scripts/motion-profile-editor.js'
    if path in ['/pose-guide-editor.js','/soma-preview-skin.js','/rig-joint-editor.js','/rig-posture-editor.js','/scene-release-editor.js','/scene-region-editor.js','/scene-grip-picker.js','/scene-object-geometry.js']:return ROOT/'scripts'/path[1:]
    if path.startswith('/assets/'):
        root=(ROOT/'assets/viewer/node_modules/three').resolve()
        target=(root/path.removeprefix('/assets/')).resolve()
    elif path.startswith('/files/'):
        relative=path.removeprefix('/files/')
        prefixes=['character-assets','rig-jobs','rig-loop-searches','scene-preview-v1','scene-fitting-v1','scene-fitting-v2','scene-fitting-v3','scene-fitting-v4','scene-fitting-v5','scene-fitting-v6','scene-fitting-v7','hand-frame-fit-v1','partner-clearance-fit-v1','object-attachment-v1','action-coverage-v1','action-jobs','contact-jobs',*CORRECTION_STUDIES]
        prefixes.append('pose-targets')
        prefixes.extend(['object-release-v1','object-release-v2','static-collider-v1','moving-collider-v1'])
        prefixes.extend(['scene-release-jobs','scene-region-jobs'])
        if not any(relative.startswith(p+'/') for p in prefixes):return None
        root=(ROOT/'reports').resolve();target=(root/relative).resolve()
        allowed=[(root/p).resolve() for p in prefixes]
        if not any(target.is_relative_to(p) for p in allowed):return None
    else:return None
    if not target.is_relative_to(root) or target.suffix.lower() not in {'.json','.glb','.bvh','.npz','.zip','.txt','.js','.gd','.md'}:return None
    return target


def validate_contact_request(payload):
    if not isinstance(payload,dict) or set(payload)!={'collection','take_id','contact_spec'}:raise ValueError('Collection, take and contact specification required')
    collection=payload['collection'];take=payload['take_id']
    if not isinstance(collection,str) or not re.fullmatch(r'[a-zA-Z0-9_/-]+',collection):raise ValueError('Invalid collection')
    if not isinstance(take,str) or not re.fullmatch(r'[a-zA-Z0-9_-]+',take):raise ValueError('Invalid take')
    target=allowed_file(f'/files/{collection}/takes/{take}/motion.npz')
    if target is None or not target.is_file():raise ValueError('Source motion not found')
    source=target.parent
    if not all((source/n).is_file() for n in ['evidence.json','raw/motion.npz','limb/motion.npz']):raise ValueError('Select a body-corrected take to author contacts')
    parent=read(source/'evidence.json')
    if 'body_correction' not in parent:raise ValueError('Select a body-corrected take to author contacts')
    import numpy as np
    from contact_spec import validate
    from support_contact import regions
    from build_soma_preview import ASSET
    validate(payload['contact_spec'],parent['frames'],regions(dict(np.load(ASSET))))
    return source,payload['contact_spec']


class Handler(BaseHTTPRequestHandler):
    def respond(self,status,value):
        payload=json.dumps(value,ensure_ascii=False).encode();self.send_response(status)
        self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(payload)))
        self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(payload)

    def do_GET(self):
        if self.headers.get('Host') not in self.server.allowed_hosts:return self.respond(403,{'error':'Loopback host required'})
        route=urlsplit(self.path).path
        if route=='/api/scene-collections':
            names=['scene-preview-v1',*[f'scene-fitting-v{i}' for i in range(1,8)],
                   'hand-frame-fit-v1','partner-clearance-fit-v1','object-attachment-v1',
                   'object-release-v1','object-release-v2','static-collider-v1','moving-collider-v1']
            folders=[ROOT/'reports'/name for name in names]
            for parent in ['action-jobs','scene-release-jobs','scene-region-jobs']:
                folders.extend(sorted((ROOT/'reports'/parent).glob('*')))
            collections=[]
            for folder in folders:
                if not (folder/'manifest.json').is_file():continue
                if not isinstance(read(folder/'manifest.json').get('scenes'),list):continue
                if folder.name!='scene-preview-v1' and (not (folder/'pipeline.json').is_file() or read(folder/'pipeline.json')['status']!='complete'):continue
                collections.append(folder.relative_to(ROOT/'reports').as_posix())
            return self.respond(200,{'collections':collections})
        if route=='/api/scene-region-source':
            from scene_region_job import metadata
            try:
                query=parse_qs(urlsplit(self.path).query)
                if set(query)!={'path'} or len(query['path'])!=1:raise ValueError('Saved scene path required')
                return self.respond(200,metadata(query['path'][0]))
            except (ValueError,TypeError,KeyError,OSError) as exc:return self.respond(400,{'error':str(exc)})
        if route=='/api/scene-region-jobs':
            from scene_region_job import JOBS
            from contact_edit_job import observed_state
            jobs=[]
            for folder in sorted(JOBS.glob('*'),reverse=True):
                if not (folder/'request.json').exists():continue
                jobs.append(dict(id=folder.name,collection='scene-region-jobs/'+folder.name,
                    label=read(folder/'request.json')['authored']['label'],**observed_state(folder)))
            return self.respond(200,dict(jobs=jobs))
        if route=='/api/scene-release-source':
            from scene_release_job import metadata
            try:
                query=parse_qs(urlsplit(self.path).query)
                if set(query)!={'path'} or len(query['path'])!=1:raise ValueError('Saved scene path required')
                return self.respond(200,metadata(query['path'][0]))
            except (ValueError,TypeError,KeyError,OSError) as exc:return self.respond(400,{'error':str(exc)})
        if route=='/api/scene-release-jobs':
            from scene_release_job import JOBS
            from contact_edit_job import observed_state
            jobs=[]
            for folder in sorted(JOBS.glob('*'),reverse=True):
                if not (folder/'request.json').exists():continue
                state=observed_state(folder)
                jobs.append(dict(id=folder.name,collection='scene-release-jobs/'+folder.name,
                    label=read(folder/'request.json')['authored']['label'],**state))
            return self.respond(200,dict(jobs=jobs))
        if route=='/api/motion-profile-template':
            from motion_profile import default_profile
            return self.respond(200,default_profile())
        if route in ('/api/rig-contact-source','/api/rig-posture-source','/api/rig-mirror-source'):
            if route=='/api/rig-mirror-source':from rig_mirror_edit import metadata
            elif route=='/api/rig-posture-source':from rig_posture_edit import metadata
            else:from rig_contact_authoring import metadata
            try:
                query=parse_qs(urlsplit(self.path).query)
                if set(query)!={'job','variant'} or any(len(v)!=1 for v in query.values()):raise ValueError('Source job and version required')
                return self.respond(200,metadata(query['job'][0],query['variant'][0]))
            except (ValueError,TypeError,KeyError,OSError) as exc:return self.respond(400,{'error':str(exc)})
        if route=='/api/characters':
            from studio_characters import list_assets
            return self.respond(200,{'characters':list_assets()})
        if route.startswith('/api/characters/'):
            from studio_characters import details
            try:return self.respond(200,details(route.removeprefix('/api/characters/')))
            except (ValueError,OSError,KeyError) as exc:return self.respond(400,{'error':str(exc)})
        if route=='/api/rig-jobs':
            from studio_characters import jobs
            return self.respond(200,{'jobs':jobs()})
        if urlsplit(self.path).path=='/api/studies':
            studies=[]
            folders=[*[ROOT/'reports'/name for name in CORRECTION_STUDIES],ROOT/'reports/action-coverage-v1',*sorted((ROOT/'reports/action-jobs').glob('*'),reverse=True)]
            for folder in folders:
                state=read(folder/'pipeline.json') if (folder/'pipeline.json').exists() else {'status':'unknown'}
                if folder.is_dir():studies.append({'id':folder.relative_to(ROOT/'reports').as_posix(),'status':state['status'],'ready':(folder/'summary.json').exists() and (folder.name not in CORRECTION_STUDIES or state['status']=='complete'),'scene_ready':folder.parent==ROOT/'reports/action-jobs' and state['status']=='complete' and (folder/'manifest.json').is_file()})
            for folder in sorted((ROOT/'reports/contact-jobs').glob('*')):
                if not folder.is_dir():continue
                from contact_edit_job import observed_state
                state=observed_state(folder)
                studies.insert(0,{'id':(folder/'result').relative_to(ROOT/'reports').as_posix(),'status':state['status'],
                    'kind':'contact_edit','ready':state['status']=='complete' and (folder/'result/summary.json').is_file(), 'error':state.get('error')})
            return self.respond(200,{'studies':studies,'busy':worker_busy() or (self.server.worker is not None and self.server.worker.poll() is None)})
        target=allowed_file(self.path)
        if target is None or not target.is_file():return self.respond(404,{'error':'File not found'})
        mime=mimetypes.guess_type(str(target))[0] or 'application/octet-stream'
        if target.suffix=='.js':mime='text/javascript'
        self.send_response(200);self.send_header('Content-Type',mime);self.send_header('Content-Length',str(target.stat().st_size))
        self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.end_headers()
        try:
            with target.open('rb') as stream:
                while block:=stream.read(1024*1024):self.wfile.write(block)
        except (BrokenPipeError,ConnectionResetError):pass

    def do_POST(self):
        if self.path not in ['/api/jobs','/api/scene-releases','/api/scene-region-fits','/api/pose-target','/api/motion-brief','/api/contact-edits','/api/characters/import','/api/characters/sample','/api/characters/profile','/api/rig-jobs','/api/rig-contact-edits','/api/rig-contact-inspect','/api/rig-clip-edits','/api/rig-joint-edits','/api/rig-posture-edits','/api/rig-mirror-edits','/api/rig-transitions','/api/rig-loops','/api/rig-loop-search','/api/rig-events','/api/rig-prompt-edits','/api/rig-dynamics-edits']:return self.respond(404,{'error':'Unknown endpoint'})
        host=self.headers.get('Host');origin=self.headers.get('Origin')
        if host not in self.server.allowed_hosts or origin!=f'http://{host}':return self.respond(403,{'error':'Submit from the local studio page'})
        if self.path=='/api/characters/import':
            if self.headers.get('Content-Type')!='application/octet-stream':return self.respond(415,{'error':'GLB binary required'})
            try:
                from studio_characters import import_bytes,MAX_UPLOAD
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<=MAX_UPLOAD:raise ValueError('Choose a GLB up to 32 MiB')
                raw=self.rfile.read(length)
                if len(raw)!=length:raise ValueError('Incomplete upload')
                return self.respond(201,import_bytes(raw,unquote(self.headers.get('X-Filename','Character.glb'))))
            except (ValueError,TypeError,KeyError,IndexError,AttributeError,OSError) as exc:return self.respond(400,{'error':str(exc)})
        if self.headers.get('Content-Type')!='application/json':return self.respond(415,{'error':'JSON required'})
        try:
            length=int(self.headers.get('Content-Length','0'))
            if not 0<length<=32768:raise ValueError('Request too large or empty')
            payload=json.loads(self.rfile.read(length))
            if self.path=='/api/pose-target':
                from pose_target import author,validate
                from action_worker_lock import worker_lock
                validate(payload)
                try:
                    with worker_lock():result=author(payload)
                except RuntimeError as exc:return self.respond(409,{'error':str(exc)})
                return self.respond(201,result)
            if self.path=='/api/motion-brief':
                from action_requests import validate_request
                from motion_profile import brief
                validate_request(payload)
                return self.respond(200,{'motion_brief':brief(payload)})
            if self.path=='/api/characters/sample':
                if payload!={}:raise ValueError('Sample request must be empty')
                from studio_characters import import_bytes
                return self.respond(201,import_bytes((ROOT/'assets/characters/cesium-man/CesiumMan.glb').read_bytes(),'CesiumMan.glb'))
            if self.path=='/api/characters/profile':
                from studio_characters import save_profile
                return self.respond(200,save_profile(payload))
            if self.path=='/api/rig-contact-inspect':
                from rig_contact_authoring import inspect_request
                return self.respond(200,inspect_request(payload))
            if self.path=='/api/rig-loop-search':
                from rig_loop_search import search
                return self.respond(200,search(payload))
            if self.path=='/api/scene-region-fits':
                from scene_region_job import validate
                validate(payload)
            elif self.path=='/api/scene-releases':
                from scene_release_job import validate
                validate(payload)
            elif self.path=='/api/rig-dynamics-edits':
                from rig_dynamics_edit import validate
                validate(payload)
            elif self.path=='/api/rig-mirror-edits':
                from rig_mirror_edit import validate
                validate(payload)
            elif self.path=='/api/rig-posture-edits':
                from rig_posture_edit import validate
                validate(payload)
            elif self.path=='/api/rig-joint-edits':
                from rig_joint_recipe import validate
                validate(payload)
            elif self.path=='/api/rig-prompt-edits':
                from rig_prompt_edit import validate
                validate(payload)
            elif self.path=='/api/rig-events':
                from rig_event_edit import validate
                validate(payload)
            elif self.path=='/api/rig-loops':
                from rig_loop import validate
                validate(payload)
            elif self.path=='/api/rig-transitions':
                from rig_transition import validate
                validate(payload)
            elif self.path=='/api/rig-clip-edits':
                from rig_clip_edit import validate
                validate(payload)
            elif self.path=='/api/rig-contact-edits':
                from rig_contact_authoring import validate_request
                validate_request(payload)
            elif self.path=='/api/rig-jobs':
                from studio_characters import validate_job
                rig_request,rig_source,rig_profile=validate_job(payload,allowed_file)
            elif self.path=='/api/contact-edits':source,spec=validate_contact_request(payload)
            else:
                batch=validate_batch(payload)
                if len(batch['requests'])!=1:raise ValueError('The studio accepts one request at a time')
        except (ValueError,TypeError,KeyError,OSError) as exc:return self.respond(400,{'error':str(exc)})
        with self.server.job_lock:
            if worker_busy() or (self.server.worker is not None and self.server.worker.poll() is None):return self.respond(409,{'error':'A local request is already running; wait for it to finish'})
            job=datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:8]
            if self.path in ('/api/scene-releases','/api/scene-region-fits'):
                if self.path=='/api/scene-region-fits':from scene_region_job import JOBS,prepare
                else:from scene_release_job import JOBS,prepare
                folder=JOBS/job
                try:
                    prepare(payload,folder)
                    with (folder/'supervisor.log').open('w',encoding='utf8') as log:
                        self.server.worker=subprocess.Popen([sys.executable,str(ROOT/'scripts'/('scene_region_job.py' if self.path=='/api/scene-region-fits' else 'scene_release_job.py')),str(folder)],cwd=ROOT,env=offline_environment(),stdout=log,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                    import psutil
                    try:save(folder/'worker.json',dict(pid=self.server.worker.pid,created_at=psutil.Process(self.server.worker.pid).create_time()))
                    except psutil.NoSuchProcess:pass
                except (ValueError,OSError) as exc:
                    if folder.exists():save(folder/'pipeline.json',dict(status='failed',error=str(exc)))
                    return self.respond(400,dict(error=str(exc)))
                return self.respond(202,dict(id=job,status='starting'))
            if self.path in ('/api/rig-contact-edits','/api/rig-clip-edits','/api/rig-joint-edits','/api/rig-posture-edits','/api/rig-mirror-edits','/api/rig-transitions','/api/rig-loops','/api/rig-events','/api/rig-prompt-edits','/api/rig-dynamics-edits'):
                if self.path=='/api/rig-dynamics-edits':from rig_dynamics_edit import prepare
                elif self.path=='/api/rig-mirror-edits':from rig_mirror_edit import prepare
                elif self.path=='/api/rig-posture-edits':from rig_posture_edit import prepare
                elif self.path=='/api/rig-joint-edits':from rig_joint_recipe import prepare
                elif self.path=='/api/rig-prompt-edits':from rig_prompt_edit import prepare
                elif self.path=='/api/rig-events':from rig_event_edit import prepare
                elif self.path=='/api/rig-loops':from rig_loop import prepare
                elif self.path=='/api/rig-transitions':from rig_transition import prepare
                elif self.path=='/api/rig-clip-edits':from rig_clip_edit import prepare
                else:from rig_contact_authoring import prepare
                from studio_characters import JOBS
                folder=JOBS/job
                try:
                    prepare(payload,folder)
                    with (folder/'supervisor.log').open('w',encoding='utf8') as log:
                        self.server.worker=subprocess.Popen([sys.executable,str(ROOT/'scripts'/('rig_dynamics_edit.py' if self.path=='/api/rig-dynamics-edits' else 'rig_studio_job.py')),str(folder)],cwd=ROOT,env=offline_environment(),stdout=log,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                    import psutil
                    try:save(folder/'worker.json',{'pid':self.server.worker.pid,'created_at':psutil.Process(self.server.worker.pid).create_time()})
                    except psutil.NoSuchProcess:pass
                except (ValueError,OSError) as exc:
                    if folder.exists():save(folder/'pipeline.json',{'status':'failed','error':str(exc)})
                    return self.respond(400,{'error':str(exc)})
                return self.respond(202,{'id':job,'status':'starting'})
            if self.path=='/api/rig-jobs':
                from studio_characters import JOBS,prepare_job
                folder=JOBS/job
                try:
                    prepare_job(rig_request,rig_source,rig_profile,folder)
                except (ValueError,TypeError,KeyError,OSError) as exc:
                    if folder.exists():save(folder/'pipeline.json',dict(status='failed',error=str(exc)))
                    return self.respond(400,dict(error=str(exc)))
                try:
                    with (folder/'supervisor.log').open('w',encoding='utf8') as log:
                        self.server.worker=subprocess.Popen([sys.executable,str(ROOT/'scripts/rig_studio_job.py'),str(folder)],cwd=ROOT,env=offline_environment(),stdout=log,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                    import psutil
                    try:save(folder/'worker.json',{'pid':self.server.worker.pid,'created_at':psutil.Process(self.server.worker.pid).create_time()})
                    except psutil.NoSuchProcess:pass
                except OSError as exc:
                    save(folder/'pipeline.json',{'status':'failed','error':str(exc)})
                    return self.respond(500,{'error':'Could not start local rig transfer'})
                return self.respond(202,{'id':job,'status':'starting'})
            if self.path=='/api/contact-edits':
                folder=ROOT/'reports/contact-jobs'/job;folder.mkdir(parents=True)
                save(folder/'contact-spec.json',spec);save(folder/'edit-request.json',{'source':source.relative_to(ROOT/'reports').as_posix()})
                save(folder/'pipeline.json',{'status':'starting'})
                try:
                    with (folder/'supervisor.log').open('w',encoding='utf8') as log:
                        self.server.worker=subprocess.Popen([sys.executable,str(ROOT/'scripts/contact_edit_job.py'),str(folder)],cwd=ROOT,env=offline_environment(),stdout=log,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                        import psutil
                        try:save(folder/'worker.json',{'pid':self.server.worker.pid,'created_at':psutil.Process(self.server.worker.pid).create_time()})
                        except psutil.NoSuchProcess:save(folder/'pipeline.json',{'status':'failed','error':'Contact worker exited during startup'})
                except OSError as exc:
                    save(folder/'pipeline.json',{'status':'failed','error':str(exc)})
                    return self.respond(500,{'error':'Could not start local contact editor'})
                return self.respond(202,{'id':'contact-jobs/'+job+'/result','status':'starting'})
            folder=ROOT/'reports/action-jobs'/job;folder.mkdir(parents=True)
            save(folder/'request.json',batch);save(folder/'pipeline.json',{'status':'starting'})
            with (folder/'supervisor.log').open('w',encoding='utf8') as log:
                self.server.worker=subprocess.Popen([sys.executable,str(ROOT/'scripts/run_actions.py'),str(folder/'request.json'),'--output',str(folder)],
                    cwd=ROOT,env=offline_environment(),stdout=log,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            return self.respond(202,{'id':'action-jobs/'+job,'status':'starting'})


def main(port):
    server=ThreadingHTTPServer(('127.0.0.1',port),Handler)
    server.allowed_hosts={f'127.0.0.1:{port}',f'localhost:{port}'};server.worker=None;server.job_lock=threading.Lock()
    print(f'Action studio: http://127.0.0.1:{port}/studio',flush=True);server.serve_forever()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=8768);main(p.parse_args().port)
