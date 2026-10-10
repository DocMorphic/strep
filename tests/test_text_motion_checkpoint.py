"""Payload/protocol integrity fixtures; no inference or animation-quality claims."""
import builtins
import json
from pathlib import Path
import sys
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import text_motion_checkpoint as subject
import score_text_motion


def fixture(tmp_path, monkeypatch):
    original = Path(__file__).resolve().parents[1]/subject.LEDGER
    ledger = json.loads(original.read_text())
    model = tmp_path/ledger['directory']
    for name in ledger['required_files_sha256']:
        path = model/name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(('Fixture only: ' + name).encode())
        ledger['required_files_sha256'][name] = subject.sha256(path)
    ledger_path = tmp_path/subject.LEDGER
    ledger_path.parent.mkdir(parents=True)
    ledger_path.write_text(json.dumps(ledger))
    monkeypatch.setattr(subject, 'LEDGER_SHA256', subject.sha256(ledger_path))
    metadata = model/'hub-metadata.json'
    metadata.write_text(json.dumps(dict(sha=subject.REVISION)))
    bindings = {subject.LEDGER: subject.sha256(ledger_path)}
    bindings.update({p.relative_to(tmp_path).as_posix(): subject.sha256(p)
                     for p in model.rglob('*') if p.is_file()})
    return ledger, model, bindings


def test_verify_complete_payload_without_tensor_imports(tmp_path, monkeypatch):
    ledger, _, bindings = fixture(tmp_path, monkeypatch)
    assert subject.verify_checkpoint(tmp_path, model_directory=ledger['directory'],
                                     revision=subject.REVISION, bindings=bindings) == ledger
    assert len(ledger['required_files_sha256']) == 11


@pytest.mark.parametrize('name', [
    'config.yaml', 'LICENSE', 'README.md', 'last_weights/motion_encoder.pt',
    'last_weights/text_encoder.pt', 'stats/motion/body/mean.npy',
    'stats/motion/body/std.npy', 'stats/motion/global_root/mean.npy',
    'stats/motion/global_root/std.npy', 'stats/motion/local_root/mean.npy',
    'stats/motion/local_root/std.npy'])
def test_self_consistent_protocol_cannot_substitute_pinned_file(tmp_path, monkeypatch, name):
    _, model, bindings = fixture(tmp_path, monkeypatch)
    changed = model/name
    changed.write_bytes(b'Substituted payload')
    bindings[changed.relative_to(tmp_path).as_posix()] = subject.sha256(changed)
    with pytest.raises(ValueError, match='Pinned critic checksum mismatch'):
        subject.verify_checkpoint(tmp_path, bindings=bindings)


def test_protocol_cannot_redefine_trusted_ledger(tmp_path, monkeypatch):
    ledger, model, bindings = fixture(tmp_path, monkeypatch)
    changed = model/'last_weights/motion_encoder.pt'
    changed.write_bytes(b'Substituted payload')
    ledger['required_files_sha256']['last_weights/motion_encoder.pt'] = subject.sha256(changed)
    ledger_path = tmp_path/subject.LEDGER
    ledger_path.write_text(json.dumps(ledger))
    for path in [changed, ledger_path]:
        bindings[path.relative_to(tmp_path).as_posix()] = subject.sha256(path)
    with pytest.raises(ValueError, match='ledger checksum mismatch'):
        subject.verify_checkpoint(tmp_path, bindings=bindings)


@pytest.mark.parametrize('damage', ['missing_binding', 'wrong_binding', 'metadata', 'revision', 'directory'])
def test_reject_unbound_or_misidentified_checkpoint(tmp_path, monkeypatch, damage):
    _, model, bindings = fixture(tmp_path, monkeypatch)
    kwargs = dict(bindings=bindings)
    if damage == 'missing_binding':
        del bindings[subject.LEDGER]
    elif damage == 'wrong_binding':
        bindings[subject.LEDGER] = '0'*64
    elif damage == 'metadata':
        path = model/'hub-metadata.json'
        path.write_text(json.dumps(dict(sha='different-revision')))
        bindings[path.relative_to(tmp_path).as_posix()] = subject.sha256(path)
    elif damage == 'revision':
        kwargs['revision'] = 'different-revision'
    else:
        kwargs['model_directory'] = '../outside'
    with pytest.raises(ValueError):
        subject.verify_checkpoint(tmp_path, **kwargs)


@pytest.mark.parametrize('name', ['last_weights/motion_encoder.pt', 'stats/motion/body/mean.npy'])
def test_scorer_rejects_substitution_before_import_or_output(tmp_path, monkeypatch, name):
    ledger, model, bindings = fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(score_text_motion, 'ROOT', tmp_path)
    changed = model/name
    changed.write_bytes(b'Substituted payload')
    bindings[changed.relative_to(tmp_path).as_posix()] = subject.sha256(changed)
    protocol = tmp_path/'protocol.json'
    protocol.write_text(json.dumps(dict(schema='strep-tmr-development-study-v1',
        split='development', fps=30, texts=[dict(feature_path='unused-a'), dict(feature_path='unused-b')],
        motions=[dict(path='unused-motion')], bindings=bindings,
        model_directory=ledger['directory'], checkpoint_revision=subject.REVISION)))
    original_import = builtins.__import__
    def no_runtime(name, *args, **kwargs):
        if name.split('.')[0] in {'torch', 'numpy', 'safetensors'}:
            raise AssertionError('Checkpoint must be rejected before importing tensor runtimes')
        return original_import(name, *args, **kwargs)
    monkeypatch.setattr(builtins, '__import__', no_runtime)
    with pytest.raises(ValueError, match='Pinned critic checksum mismatch'):
        score_text_motion.run(protocol, tmp_path/'output')
    assert not (tmp_path/'output').exists()
