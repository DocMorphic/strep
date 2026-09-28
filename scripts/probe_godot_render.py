"""Bounded graphics-backend probe, with a minimized hidden-startup window."""
import subprocess
from pathlib import Path
import shutil
import numpy as np
from PIL import Image
from strep import ROOT, read, save, sha256, now


def engine_command(script, project, *args):
    engine = ROOT/'.cache/godot/4.7.2-stable/Godot_v4.7.2-stable_win64_console.exe'
    acquisition = read(engine.parent/'acquisition.json')
    if sha256(engine) != acquisition['executables'][engine.name]:
        raise ValueError('Pinned engine executable changed')
    return [str(engine), '--path', str(project), '--display-driver', 'windows',
            '--rendering-method', 'gl_compatibility', '--rendering-driver', 'opengl3',
            '--audio-driver', 'Dummy', '--disable-render-loop', '--script', script, '--', *map(str, args)]


def run_engine(command, log, timeout=120):
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = subprocess.SW_HIDE
    with Path(log).open('w', encoding='utf-8') as stream:
        result = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT,
            timeout=timeout, startupinfo=startup, creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode:
        raise ValueError('Graphics process failed; inspect '+str(log))


def project_file(path):
    Path(path).write_text('config_version=5\n[application]\nconfig/name="Strep render audit"\n'
        '[display]\nwindow/size/viewport_width=256\nwindow/size/viewport_height=256\nwindow/size/mode=1\n'
        '[rendering]\nrenderer/rendering_method="gl_compatibility"\ntextures/default_filters/use_nearest_mipmap_filter=false\n', encoding='utf-8')


if __name__ == '__main__':
    output = ROOT/'reports/godot-render-probe-v1'
    output.mkdir(exist_ok=False)
    project_file(output/'project.godot')
    shutil.copyfile(ROOT/'scripts/godot_render_probe.gd', output/'godot_render_probe.gd')
    command = engine_command('godot_render_probe.gd', output, output)
    save(output/'request.json', dict(at=now(), command=command))
    run_engine(command, output/'engine.log')
    pixels = np.array(Image.open(output/'probe.png').convert('RGB'))
    bright = np.all(pixels > 200, axis=2)
    info = read(output/'render-info.json')
    if not info['adapter'] or info['display']=='headless' or not 1000 < bright.sum() < 60000:
        raise ValueError('Probe did not produce a nonempty hardware-backed render')
    save(output/'verification.json', dict(at=now(), info=info, bright_pixels=int(bright.sum()),
        image_sha256=sha256(output/'probe.png'), scope='Graphics availability only, not character validation.'))
    print(info, 'bright pixels', bright.sum())
