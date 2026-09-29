"""Bind guarded correction jobs to successful immutable stationary-pin checks."""
import re
import shutil
from pathlib import Path
from strep import ROOT,read,save,sha256

RATE_METHODS=['export_point_rate_objective.py','export_motion_sampling.py','linear_skin_operator.py',
              'floor_contact.py','contact_spec.py','support_contact.py','inspect_motion.py']


def validate_request(payload):
    if not isinstance(payload,dict) or set(payload)!={'checked_plan','revision'}:
        raise ValueError('Saved timing check and its revision required')
    key=payload['checked_plan']
    if not isinstance(key,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}',key):raise ValueError('Invalid check identifier')
    folder=(ROOT/'reports/contact-jobs'/key).resolve()
    if not folder.is_relative_to((ROOT/'reports/contact-jobs').resolve()):raise ValueError('Check escapes saved jobs')
    if not isinstance(payload['revision'],str) or sha256(folder/'timing-result.json')!=payload['revision']:
        raise ValueError('Timing check changed; review it again')
    result=read(folder/'timing-result.json');state=read(folder/'pipeline.json')
    if result.get('status')!='checked' or state.get('status')!='checked' or result.get('conflicts')!=0:
        raise ValueError('Resolve timing conflicts and run a new check before fitting')
    for name,h in result['files'].items():
        path=(folder/name).resolve()
        if not path.is_relative_to(folder.resolve()) or sha256(path)!=h:raise ValueError('Checked artifact changed')
    freeze=read(folder/'freeze.json')
    if sha256(folder/'edit-request.json')!=freeze['request_sha256'] or sha256(folder/'contact-spec.json')!=freeze['spec_sha256']:
        raise ValueError('Checked request changed')
    if read(folder/'edit-request.json')['options']['edit_window']!=result['requested_window']:
        raise ValueError('Checked window differs from its result')
    for name,h in freeze['inputs'].items():
        if sha256(folder/'source'/name)!=h:raise ValueError('Checked source snapshot changed')
    for name in RATE_METHODS:
        if sha256(ROOT/'scripts'/name)!=freeze['implementation'][name]:raise ValueError('Rate calculation changed; run a new timing check')
    source=(ROOT/'reports'/result['source']).resolve()
    if not source.is_relative_to(ROOT/'reports'):raise ValueError('Checked source escapes reports')
    for name,h in freeze['inputs'].items():
        if sha256(source/name)!=h:raise ValueError('Current clip differs from the checked clip; run a new check')
    return folder,source


def prepare(payload,folder):
    check,source=validate_request(payload)
    folder.mkdir(parents=True,exist_ok=False)
    shutil.copytree(check,folder/'checked-plan',ignore=shutil.ignore_patterns('implementation','supervisor.log','worker.json'))
    target=folder/'source-take';target.mkdir()
    # Preserve the source's raw/limb history and current preview metadata. Avoid
    # recursively duplicating prior edit histories and animation archives.
    for name in ['raw','limb']:shutil.copytree(source/name,target/name)
    for name in ['motion.npz','soma.glb','motion.bvh','root-motion.json','contacts.json','evidence.json','request.json','timeline.json','generation-record.json']:
        shutil.copyfile(source/name,target/name)
    validate_request(payload)
    if sha256(target/'motion.npz')!=sha256(check/'source/motion.npz') or sha256(target/'soma.glb')!=sha256(check/'source/soma.glb'):
        raise ValueError('Source changed during guarded-job snapshot')
    save(folder/'edit-request.json',dict(kind='checked_fit',check_id=payload['checked_plan'],check_revision=payload['revision']))
    (folder/'implementation').mkdir()
    implementation={}
    for p in (ROOT/'scripts').glob('*.py'):
        shutil.copyfile(p,folder/'implementation'/p.name);implementation[p.name]=sha256(p)
    inputs={p.relative_to(folder).as_posix():sha256(p) for root in [folder/'source-take',folder/'checked-plan'] for p in root.rglob('*') if p.is_file()}
    inputs['edit-request.json']=sha256(folder/'edit-request.json')
    save(folder/'checked-freeze.json',dict(implementation=implementation,inputs=inputs))
    save(folder/'pipeline.json',dict(status='starting',kind='checked_fit'))


def verify(folder):
    frozen=read(folder/'checked-freeze.json')
    if any(sha256(folder/n)!=h for n,h in frozen['inputs'].items()):raise ValueError('Guarded-job input changed')
    if any(sha256(ROOT/'scripts'/n)!=h for n,h in frozen['implementation'].items()):raise ValueError('Guarded-job implementation changed')


def run(folder):
    from run_contact_edit import run as edit
    verify(folder)
    edit(folder/'source-take',folder/'checked-plan/bound-contact-spec.json',folder/'result',checked_plan=folder/'checked-plan')
    verify(folder)
