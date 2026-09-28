"""Bundle local browser dependencies and create an immutable model-free review ZIP."""
import argparse
from pathlib import Path
import shutil
import zipfile
from strep import ROOT,read,save,sha256,now


def package(packet,archive):
    packet=Path(packet).resolve();archive=Path(archive).resolve()
    if archive.exists() or archive.is_relative_to(packet):raise ValueError('Use a new archive outside the packet')
    manifest=read(packet/'manifest.json')
    if (packet/'runtime').exists():raise ValueError('Preserve an already packaged packet')
    allowed={'manifest.json','viewer.html','LICENSE.txt'}|{c['path'] for c in manifest['cases']}
    actual={p.relative_to(packet).as_posix() for p in packet.rglob('*') if p.is_file()}
    if actual!=allowed:raise ValueError('Unexpected packet files; do not package organizer data')
    for case in manifest['cases']:
        path=(packet/case['path']).resolve()
        if not path.is_relative_to(packet) or sha256(path)!=case['sha256']:raise ValueError('Changed or escaping reviewer asset')
    runtime=packet/'runtime';runtime.mkdir()
    three=ROOT/'assets/viewer/node_modules/three'
    # Retain the distributed module paths, including relative addon dependencies.
    shutil.copytree(three/'build',runtime/'three/build')
    shutil.copytree(three/'examples/jsm',runtime/'three/examples/jsm')
    shutil.copyfile(three/'LICENSE',runtime/'three/LICENSE')
    shutil.copyfile(ROOT/'scripts/soma-preview-skin.js',runtime/'soma-preview-skin.js')
    html=(packet/'viewer.html').read_text(encoding='utf-8')
    html=html.replace('../../assets/viewer/node_modules/three/','./runtime/three/').replace('../../scripts/soma-preview-skin.js','./runtime/soma-preview-skin.js')
    if '../../' in html:raise ValueError('Viewer still references workspace files')
    (packet/'viewer.html').write_text(html,encoding='utf-8')
    shutil.copyfile(ROOT/'scripts/serve_review_packet.py',packet/'serve.py')
    (packet/'README.txt').write_text('''Strep independent animation review

This packet contains clips and local viewer files. No motion model, account, network download or Strep workspace is needed. A browser with WebGL and Python 3 are required.

Extract the complete ZIP to a folder. From that folder, run:
  python serve.py
On Windows with the Python launcher you can use:
  py -3 serve.py
Then open http://127.0.0.1:8771/viewer.html . Use --port NUMBER if that port is occupied. Do not open viewer.html as a file:// URL. Ctrl+C stops the local server.

Use a separate browser profile for each reviewer. Enter your own ratings only. Save each reviewed clip and export the JSON before clearing browser data. Send the JSON to the organizer using a separately agreed channel; this page does not upload it.

Condition and seed labels are hidden. Action descriptions and explicit missing-context limits are visible. Missing object/partner geometry cannot receive a scene contact score. These single-actor clips do not establish complete interaction quality. Do not infer release approval from this form.

Actual cleanup means editing the downloaded GLB, recording active seconds and operations, and retaining abandoned/time-limited work. Playback time is not cleanup time.

SOMA preview and skin helper: NVIDIA Kimodo / Strep modifications, Apache-2.0 (LICENSE.txt). Three.js: MIT (runtime/three/LICENSE). This is a model-free reviewer packet, not a motion-model redistribution or release certification.
''',encoding='utf-8')
    inventory={p.relative_to(packet).as_posix():sha256(p) for p in sorted(packet.rglob('*')) if p.is_file()}
    save(packet/'package-integrity.json',dict(schema=1,created_at=now(),files=inventory,
        scope='Local integrity inventory, not a publisher signature. No organizer key or model weights included.'))
    archive.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED) as z:
        for path in sorted(packet.rglob('*')):
            if path.is_file():z.write(path,path.relative_to(packet).as_posix())
    with zipfile.ZipFile(archive) as z:
        if z.testzip() is not None:raise ValueError('Archive CRC failure')
    return dict(archive=str(archive),archive_sha256=sha256(archive),bytes=archive.stat().st_size,
                packet_id=manifest['packet_id'],clips=len(manifest['cases']),files=len(inventory)+1)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('packet',type=Path);p.add_argument('--archive',required=True,type=Path)
    a=p.parse_args();print(package(a.packet,a.archive))
