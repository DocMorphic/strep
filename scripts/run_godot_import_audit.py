"""Verify actual engine-imported meshes and sampled animation against GLB sources."""
import argparse
import shutil
import subprocess
from pathlib import Path
import numpy as np
from strep import ROOT,read,save,sha256,now
from gltf_tools import read_glb,accessor,sample_animation


def run(output):
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=False);project=output/'project';project.mkdir()
    (project/'project.godot').write_text('config_version=5\n[application]\nconfig/name="Strep import audit"\n[rendering]\nrenderer/rendering_method="gl_compatibility"\n',encoding='utf8')
    script=ROOT/'scripts/godot_import_audit.gd';shutil.copyfile(script,project/'audit.gd')
    cases=[dict(id='attached-box-'+str(seed),path=(ROOT/f'reports/object-attachment-v1/palm-attached-box-seed-{seed}/portable/scene.glb').as_posix(),frames=180) for seed in [11,22]]
    cases.append(dict(id='high-five-point-fit',path=(ROOT/'reports/scene-fitting-v4/assets/high-five-seed-11/A/soma.glb').as_posix(),frames=120))
    save(output/'request.json',dict(cases=cases));save(output/'pipeline.json',dict(status='processing'))
    executable=ROOT/'.cache/godot/4.7.2-stable/Godot_v4.7.2-stable_win64_console.exe'
    args=[str(executable),'--headless','--path',str(project),'--script','audit.gd','--',str(output/'request.json'),str(output/'engine-output.json')]
    with (output/'engine.log').open('w',encoding='utf8') as log:
        result=subprocess.run(args,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode:save(output/'pipeline.json',dict(status='failed',exit_code=result.returncode));raise RuntimeError('Godot audit failed; inspect engine.log')
    report=read(output/'engine-output.json');checks=[]
    for case in report['cases']:
        doc,binary=read_glb(case['path']);node_by_name={n.get('name'):i for i,n in enumerate(doc['nodes'])};skin=doc['skins'][0]
        if len(case['bone_names'])!=len(skin['joints']):raise ValueError('Engine joint count changed')
        node_indices=[node_by_name[n] for n in case['bone_names']];position_error=0.;rotation_error=0.;object_error=0.
        for f,item in enumerate(case['frames']):
            expected=sample_animation(doc,binary,0,f);actual=np.array(item['bones'])
            position_error=max(position_error,float(np.abs(actual[:,3]-expected[node_indices,:3,3]).max()))
            rotation_error=max(rotation_error,float(np.abs(actual[:,:3].transpose(0,2,1)-expected[node_indices,:3,:3]).max()))
            if item['object'] is not None:
                actual_object=np.array(item['object']);world=expected[node_by_name['Interaction_box']]
                object_error=max(object_error,float(np.abs(actual_object[3]-world[:3,3]).max()),float(np.abs(actual_object[:3].T-world[:3,:3]).max()))
        meshes=[m for m in case['meshes'] if m['weights']]
        if len(meshes)!=1:raise ValueError('Unexpected skinned mesh count')
        mesh=meshes[0];attributes=doc['meshes'][0]['primitives'][0]['attributes'];weights=np.concatenate([accessor(doc,binary,attributes['WEIGHTS_'+str(i)]) for i in [0,1]],axis=1)
        indices=np.concatenate([accessor(doc,binary,attributes['JOINTS_'+str(i)]) for i in [0,1]],axis=1)
        imported=np.array(mesh['weights']).reshape(-1,8);bones=np.array(mesh['bones']).reshape(-1,8)
        if len(mesh['positions'])!=len(weights):raise ValueError('Engine vertex count changed')
        np.testing.assert_allclose(mesh['positions'],accessor(doc,binary,attributes['POSITION']),atol=1e-6)
        weight_error=float(np.abs(imported-weights).max())
        np.testing.assert_array_equal(bones,indices)
        if max(position_error,rotation_error,object_error)>1e-4 or weight_error>1e-4:raise ValueError(f'Engine fidelity mismatch: {position_error}, {rotation_error}, {object_error}, {weight_error}')
        checks.append(dict(id=case['id'],source_sha256=sha256(case['path']),frames_checked=len(case['frames']),bones=len(node_indices),vertices=len(weights),influences=8,
            max_joint_position_error_m=position_error,max_rotation_element_error=rotation_error,max_object_transform_error=object_error,max_weight_error=weight_error,animation_duration_s=case['duration_s']))
    save(output/'verification.json',dict(created_at=now(),engine=report['engine'],checks=checks,script_sha256=sha256(script),runner_sha256=sha256(__file__),
        scope='Actual Godot runtime GLB import, all-frame AnimationPlayer seek and imported mesh data. No GPU skin rendering, physics, event dispatch, retargeting or animator approval.'))
    save(output/'pipeline.json',dict(status='complete'));print(checks)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();run(args.output)
