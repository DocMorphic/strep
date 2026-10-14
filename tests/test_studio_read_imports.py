"""Read-only status must not load the motion model or numerical correction stack."""
import os
from pathlib import Path
import subprocess
import sys


def isolated(code, tmp_path):
    scripts=Path(__file__).resolve().parents[1]/'scripts'
    prelude=f'''
import sys, importlib.abc
from pathlib import Path
sys.path.insert(0,{str(scripts)!r})
class NoNumerics(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in ('torch','numpy','scipy'):
            raise AssertionError('Read-only route imported '+fullname)
sys.meta_path.insert(0,NoNumerics())
root=Path({str(tmp_path)!r})
'''
    result=subprocess.run([sys.executable,'-c',prelude+code],env=os.environ.copy(),capture_output=True,text=True,timeout=30)
    assert result.returncode==0,result.stdout+result.stderr


def test_timing_metadata_and_validation_work_without_numerical_dependencies(tmp_path):
    isolated('''
import contact_timing_job as job
from strep import save,sha256
job.ROOT=root
folder=root/'reports/contact-jobs/check'
save(folder/'timing-result.json',{'immutable':'receipt'})
state=dict(kind='timing_check',status='needs_authoring_change',check_schema_version=3,message='Two conflicts',source='original')
row=job.listing(folder,state)
assert row['kind']=='contact_check' and row['timing_message']=='Two conflicts'
assert row['check_revision']==sha256(folder/'timing-result.json')
assert row['pose_report']=='/files/contact-jobs/check/pose-preflight.json'
assert row['bound_contacts']=='/files/contact-jobs/check/bound-contact-spec.json'
assert job.listing(folder,dict(kind='other'))=={}
spec={'regions':{'LeftFoot':{'mode':'explicit','segments':[dict(space='world',start_frame=30,end_frame=149)]}}}
assert job.validate_options({'edit_window':[20,159]},spec,180)=={'edit_window':[20,159]}
assert not {'torch','numpy','scipy'}&set(sys.modules)
''',tmp_path)


def test_real_study_dispatch_preserves_timing_status_without_numerical_imports(tmp_path):
    isolated('''
from types import SimpleNamespace
import action_studio_server as server
import contact_timing_job as timing
from strep import save
server.ROOT=timing.ROOT=root
folder=root/'reports/contact-jobs/check'
save(folder/'pipeline.json',dict(kind='timing_check',status='needs_authoring_change',message='Two conflicts',check_schema_version=3))
server.worker_busy=lambda:False
server.external_pair_fit_busy=lambda:False
h=server.Handler.__new__(server.Handler)
h.path='/api/studies';h.headers={'Host':'127.0.0.1:8768'}
h.server=SimpleNamespace(allowed_hosts={'127.0.0.1:8768'},worker=None)
responses=[];h.respond=lambda code,value:responses.append((code,value))
h.do_GET();code,value=responses[0]
assert code==200 and value['busy'] is False
row=next(s for s in value['studies'] if s['id']=='contact-jobs/check/result')
assert row['status']=='needs_authoring_change' and row['kind']=='contact_check' and row['ready'] is False
assert row['timing_message']=='Two conflicts' and row['check_schema_version']==3
assert row['pose_report']=='/files/contact-jobs/check/pose-preflight.json'
assert not {'torch','numpy','scipy'}&set(sys.modules)
''',tmp_path)
