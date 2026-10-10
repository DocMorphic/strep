"""Verify the supported TMR payload before importing tensor/model runtimes."""
from pathlib import Path
from strep import read, sha256


LEDGER = 'benchmarks/text-motion-evaluator-v1.json'
LEDGER_SHA256 = 'ade2591a8044609a85518a39e29471ffbe48a1da10a92472a573f05f942d0e0c'
REVISION = 'e427752ae3446dedba49e928c93ddc9f0e413401'


def verify_checkpoint(root, *, model_directory=None, revision=None, bindings=None):
    """Return the pinned ledger; a protocol cannot redefine its trusted hashes."""
    root = Path(root).resolve()
    ledger_path = (root/LEDGER).resolve()
    if (not ledger_path.is_relative_to(root) or not ledger_path.is_file()
            or sha256(ledger_path) != LEDGER_SHA256):
        raise ValueError('Supported TMR checkpoint ledger checksum mismatch')
    ledger = read(ledger_path)
    if (ledger['schema'] != 'strep-optional-text-motion-evaluator-v1'
            or ledger['repo_id'] != 'nvidia/TMR-SOMA-RP-v1'
            or ledger['revision'] != REVISION
            or (revision is not None and revision != REVISION)
            or (model_directory is not None and model_directory != ledger['directory'])):
        raise ValueError('Only the pinned TMR-SOMA-RP-v1 payload is supported')
    model = (root/ledger['directory']).resolve()
    if not model.is_relative_to(root) or not model.is_dir():
        raise ValueError('Existing in-project pinned checkpoint directory required')
    required = {LEDGER: LEDGER_SHA256}
    for name, digest in ledger['required_files_sha256'].items():
        path = (model/name).resolve()
        if (not path.is_relative_to(model) or not path.is_file()
                or sha256(path) != digest):
            raise ValueError('Pinned critic checksum mismatch: ' + name)
        required[path.relative_to(root).as_posix()] = digest
    metadata_path = model/'hub-metadata.json'
    if read(metadata_path)['sha'] != REVISION:
        raise ValueError('Pinned critic metadata revision mismatch')
    required[metadata_path.relative_to(root).as_posix()] = sha256(metadata_path)
    if bindings is not None and any(bindings.get(name) != digest for name, digest in required.items()):
        raise ValueError('Every pinned checkpoint input and ledger must be bound')
    return ledger
