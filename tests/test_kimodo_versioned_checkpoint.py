"""Source-only pin/configuration checks; no torch, model payload or GPU required."""
import copy,json,sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import kimodo_versioned_checkpoint as loader
from strep import save,sha256


def configuration():
    return dict(_target_='kimodo.model.Kimodo',num_base_steps=1000,
        denoiser=dict(_target_='kimodo.model.twostage_denoiser.TwostageDenoiser',
            ckpt_path='${oc.select:checkpoint_dir}/model.safetensors',
            motion_rep=dict(_target_='kimodo.motion_rep.KimodoMotionRep',
                stats_path='${oc.select:checkpoint_dir}/stats/motion/',skeleton=dict(_target_='kimodo.skeleton.SOMASkeleton30'))))


def test_qualified_configuration_is_data_only_and_unmodified():
    value=configuration();before=copy.deepcopy(value)
    loader.check_configuration(value,copy.deepcopy(value));assert value==before


@pytest.mark.parametrize('fault',['architecture','target','nested-target','directive','environment','checkpoint','stats','skeleton'])
def test_different_or_executable_configurations_reject_before_resolution(fault):
    value=configuration();baseline=copy.deepcopy(value)
    if fault=='architecture':value['num_base_steps']=999
    elif fault=='target':value['_target_']='subprocess.call';baseline=copy.deepcopy(value)
    elif fault=='nested-target':value['denoiser']['extra']={'_target_':'subprocess.call'};baseline=copy.deepcopy(value)
    elif fault=='directive':value['_recursive_']=False;baseline=copy.deepcopy(value)
    elif fault=='environment':value['secret']='${oc.env:UNEXPECTED}';baseline=copy.deepcopy(value)
    elif fault=='checkpoint':value['denoiser']['ckpt_path']='https://example.invalid/model.safetensors';baseline=copy.deepcopy(value)
    elif fault=='stats':value['denoiser']['motion_rep']['stats_path']='../outside';baseline=copy.deepcopy(value)
    else:value['denoiser']['motion_rep']['skeleton']['_target_']='other.Skeleton';baseline=copy.deepcopy(value)
    with pytest.raises(ValueError):loader.check_configuration(value,baseline)


def acquisition(tmp_path,monkeypatch):
    monkeypatch.setattr(loader,'ROOT',tmp_path)
    folder=tmp_path/'models/checkpoints/Kimodo-SOMA-RP-v1.2';folder.mkdir(parents=True)
    files={}
    for name in loader.FILES:
        p=folder/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(('fixture '+name).encode())
        files[name]=dict(bytes=p.stat().st_size,sha256=sha256(p))
    value=dict(status='complete',weights_acquired=True,inference_executed=False,default_changed=False,
        quality_approved=False,release_approved=False,repo='nvidia/Kimodo-SOMA-RP-v1.2',revision='a'*40,target=str(folder),files=files)
    receipt=tmp_path/'receipt.json';save(receipt,value)
    return receipt,value,folder


def test_explicit_complete_acquisition_has_no_registry_or_default_side_effect(tmp_path,monkeypatch):
    path,value,folder=acquisition(tmp_path,monkeypatch);before=path.read_bytes()
    actual,target,pins=loader.binding(path,sha256(path))
    assert actual==value and target==folder and len(pins)==len(loader.FILES)+1 and path.read_bytes()==before


@pytest.mark.parametrize('fault',['pin','missing','extra','file','size','hash','repo','variant','revision','outside','approval','incomplete'])
def test_missing_changed_or_unqualified_checkpoint_cannot_bind(tmp_path,monkeypatch,fault):
    path,value,folder=acquisition(tmp_path,monkeypatch)
    if fault=='missing':value['files'].pop('config.yaml')
    elif fault=='extra':value['files']['extra.pt']=value['files']['config.yaml']
    elif fault=='file':(folder/'config.yaml').write_bytes(b'changed')
    elif fault=='size':value['files']['config.yaml']['bytes']+=1
    elif fault=='hash':value['files']['config.yaml']['sha256']='0'*64
    elif fault=='repo':value['repo']='unknown/model-v1.2'
    elif fault=='variant':value['repo']='nvidia/Kimodo-SOMA-RP-ArdyRep-v1.2'
    elif fault=='revision':value['revision']='main'
    elif fault=='outside':value['target']=str(tmp_path/'outside')
    elif fault=='approval':value['quality_approved']=True
    elif fault=='incomplete':value['weights_acquired']=False
    save(path,value);pin='0'*64 if fault=='pin' else sha256(path)
    with pytest.raises(ValueError):loader.binding(path,pin)
