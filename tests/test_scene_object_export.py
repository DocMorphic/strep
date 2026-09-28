"""Regression: imported rigid objects must preserve near-gimbal rotations."""
import subprocess
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from strep import ROOT,read
from scene_object_export import export_objects
from gltf_tools import read_glb,write_glb
from rig_clip_import import AnimationSampler


def test_actual_godot_complete_trs_preserves_near_gimbal_rotation(tmp_path):
    # Independently held rotation near a 90-degree Euler singularity, not an
    # identity-axis fixture which would miss the AnimationMixer fallback.
    q=np.array([.2358392328,.6666833162,-.6665127277,.2359533310]);q/=np.linalg.norm(q)
    scene=dict(fps=30,frame_count=4,objects=dict(crate=dict(shape='box',size_m=[.2,.3,.4],keyframes=[dict(frame=0,translation_m=[1,2,3],rotation_xyzw=q.tolist())])))
    target=tmp_path/'objects.glb';export_objects(scene,target)
    doc,binary=read_glb(target);expected=AnimationSampler(doc,binary,0).sample(0)[0,:3,:3]
    (tmp_path/'project.godot').write_text('config_version=5\n',encoding='utf8')
    engine=ROOT/'.cache/godot/4.7.2-stable/Godot_v4.7.2-stable_win64_console.exe'
    def observe(path,filename):
        result=subprocess.run([str(engine),'--headless','--path',str(tmp_path),'--script',str(ROOT/'scripts/godot_rotation_playback_diagnostic.gd'),'--',str(path),str(tmp_path/filename),'Object_crate'],capture_output=True,text=True,timeout=30,creationflags=subprocess.CREATE_NO_WINDOW)
        assert result.returncode==0,result.stdout+result.stderr
        return np.array([s['actual_basis'] for s in read(tmp_path/filename)[0]['samples']]).transpose(0,2,1)
    actual=observe(target,'complete.json')
    assert np.max(np.abs(actual-expected))<1e-5
    # Negative control reproduces the prior export defect on the pinned engine.
    doc['animations'][0]['channels']=[c for c in doc['animations'][0]['channels'] if c['target']['path']!='scale']
    old=tmp_path/'incomplete.glb';write_glb(old,doc,binary)
    assert np.max(np.abs(observe(old,'incomplete.json')-expected))>1e-5
