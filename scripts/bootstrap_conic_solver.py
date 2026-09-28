"""Retain a pinned experimental solver without altering the active environment."""
import hashlib
import json
from pathlib import Path
import urllib.request
import zipfile
import sys
from strep import ROOT,save,sha256,now

VERSION='0.11.1'
FILENAME='clarabel-0.11.1-cp39-abi3-win_amd64.whl'
EXPECTED='557d5148a4377ae1980b65d00605ae870a8f34f95f0f6a41e04aa6d3edf67148'


def run():
    dest=ROOT/'vendor'/('clarabel-'+VERSION);report=ROOT/'reports/conic-solver-bootstrap-v1.json'
    if dest.exists() or report.exists():raise ValueError('Preserve previous dependency bootstrap')
    metadata=json.load(urllib.request.urlopen('https://pypi.org/pypi/clarabel/'+VERSION+'/json'))
    entry=next(item for item in metadata['urls'] if item['filename']==FILENAME)
    if entry['digests']['sha256']!=EXPECTED:raise ValueError('Published wheel hash differs')
    wheel=ROOT/'assets/solver-wheels'/FILENAME;wheel.parent.mkdir(parents=True,exist_ok=True)
    data=wheel.read_bytes() if wheel.exists() else urllib.request.urlopen(entry['url']).read()
    if hashlib.sha256(data).hexdigest()!=EXPECTED:raise ValueError('Downloaded wheel hash differs')
    if not wheel.exists():wheel.write_bytes(data)
    dest.mkdir(parents=True)
    with zipfile.ZipFile(wheel) as archive:
        for item in archive.infolist():
            target=(dest/item.filename).resolve()
            if not target.is_relative_to(dest.resolve()):raise ValueError('Wheel path outside destination')
        archive.extractall(dest)
    sys.path.insert(0,str(dest));import clarabel
    if clarabel.__version__!=VERSION:raise ValueError('Imported solver version differs')
    files={str(p.relative_to(dest)):sha256(p) for p in dest.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    licenses=[p for p in files if 'license' in p.lower()]
    if not licenses:raise ValueError('Missing wheel license')
    save(report,dict(at=now(),version=VERSION,wheel=str(wheel),wheel_sha256=EXPECTED,download_url=entry['url'],vendor=str(dest),files=files,licenses=licenses,
        imported_version=clarabel.__version__,implementation_sha256=sha256(__file__),
        sources=['https://pypi.org/project/clarabel/0.11.1/','https://clarabel.org/stable/python/getting_started_py/'],
        scope='Experimental Windows CPython solver; pinned official wheel verified and extracted locally. No packages installed or upgraded in the active venv. This is not product deployment or animation quality evidence.'))
    print(dict(version=clarabel.__version__,files=len(files),licenses=licenses,vendor=str(dest)))


if __name__=='__main__':run()
