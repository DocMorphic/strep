from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import pytest
import strep

@pytest.fixture
def moved(tmp_path,monkeypatch):
 root=tmp_path/'new project location';root.mkdir();lock=root/'sources.json';strep.save(lock,dict(models=[dict(repo_id='nvidia/Test',revision='abc'),dict(repo_id='org/Encoder',revision='def')]))
 monkeypatch.setattr(strep,'ROOT',root);monkeypatch.setattr(strep,'CACHE',root/'.cache/huggingface/hub');monkeypatch.setattr(strep,'LOCK',lock)
 return root

@pytest.mark.parametrize('repo,revision,relative',[('nvidia/Test','abc','models/checkpoints/Test'),('org/Encoder','def','.cache/huggingface/hub/models--org--Encoder/snapshots/def')])
def test_resolves_new_checkout_even_when_old_path_exists(moved,tmp_path,repo,revision,relative):
 old=tmp_path/'old';old.mkdir();(old/'weights').write_text('wrong old bytes')
 target=moved/relative;target.mkdir(parents=True);(target/'weights').write_text('new bytes')
 entry=dict(repo_id=repo,revision=revision,directory=str(old))
 resolved=strep.model_directory(entry)
 assert resolved==target.resolve() and (resolved/'weights').read_text()=='new bytes'
 assert entry['directory']==str(old)

@pytest.mark.parametrize('entry',[{},dict(repo_id='unknown',revision='abc'),dict(repo_id='nvidia/Test',revision='wrong')])
def test_unknown_or_mismatched_pin_rejected(moved,entry):
 with pytest.raises(ValueError):strep.model_directory(entry)

def test_does_not_fall_back_to_old_weights_if_moved_copy_missing(moved,tmp_path):
 old=tmp_path/'old';old.mkdir();(old/'weights').write_text('old')
 path=strep.model_directory(dict(repo_id='nvidia/Test',revision='abc',directory=str(old)))
 assert not path.exists() and path.is_relative_to(moved)
