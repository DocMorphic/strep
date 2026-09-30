"""Verify required evidence while retaining additional declared parent inputs."""
from strep import sha256


def bind_inputs(required, declared):
    if not isinstance(required, dict) or not isinstance(declared, dict): raise ValueError('Evidence maps required')
    if any(declared.get(path) != digest for path, digest in required.items()):
        raise ValueError('Required evidence binding differs')
    result = {}
    for path, digest in declared.items():
        if sha256(path) != digest: raise ValueError('Declared evidence changed')
        result[path] = digest
    return result
