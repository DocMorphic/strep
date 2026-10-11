"""Known animated plane crossings, complete vertex checks and paired failures."""
import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from gltf_tools import append_accessor,write_glb
from rig_floor_comparison import compare


def fixture(path,heights):
    document=dict(asset=dict(version='2.0'),nodes=[dict(name='Hip',children=[1]),dict(name='Mesh',mesh=0,skin=0,translation=[99,99,99])],
        skins=[dict(joints=[0])],scenes=[dict(nodes=[0])],scene=0,buffers=[dict(byteLength=0)],bufferViews=[],accessors=[],meshes=[])
    binary=bytearray();position=append_accessor(document,binary,[[0,.1,0],[1,.3,0],[0,.2,1]],'VEC3')
    joint_view=len(document['bufferViews']);start=len(binary);binary.extend(np.zeros((3,4),dtype='<u2').tobytes())
    document['bufferViews'].append(dict(buffer=0,byteOffset=start,byteLength=24))
    joints=len(document['accessors']);document['accessors'].append(dict(bufferView=joint_view,componentType=5123,count=3,type='VEC4'))
    weights=append_accessor(document,binary,[[1,0,0,0]]*3,'VEC4')
    document['meshes']=[dict(primitives=[dict(attributes=dict(POSITION=position,JOINTS_0=joints,WEIGHTS_0=weights))])]
    clock=append_accessor(document,binary,[0,.5,1],'SCALAR');values=append_accessor(document,binary,[[0,y,0] for y in heights],'VEC3')
    document['animations']=[dict(samplers=[dict(input=clock,output=values,interpolation='LINEAR')],channels=[dict(sampler=0,target=dict(node=0,path='translation'))])]
    document['buffers'][0]['byteLength']=len(binary);write_glb(path,document,binary);return path


def test_different_failure_population_and_witness(tmp_path):
    source=fixture(tmp_path/'source.glb',[0,-.2,0]);target=fixture(tmp_path/'target.glb',[-.2,0,-.2])
    before={p:p.read_bytes() for p in (source,target)};result=compare(source,target,[0,.5,1])
    assert result['paired_samples']==dict(both_fail=0,source_only_fail=1,target_only_fail=2,neither_fail=0)
    np.testing.assert_allclose(result['source']['depth_m'],[0,.1,0],atol=1e-8,rtol=0)
    assert result['source']['peak_sample']==1 and result['source']['peak_vertex']['flat_vertex']==0
    assert result['source']['peak_vertex']['skin_influences']==[dict(node=0,name='Hip',weight=1.)]
    assert all(p.read_bytes()==raw for p,raw in before.items())
    assert not result['cause_established'] and not result['contact_or_support_verified'] and not result['quality_approved']


def test_explicit_floor_changes_assessment_not_motion(tmp_path):
    path=fixture(tmp_path/'clip.glb',[0,0,0]);result=compare(path,path,[0,.5,1],floor_y_m=.2)
    assert result['paired_samples']['both_fail']==3
    np.testing.assert_allclose(result['source']['maximum_depth_m'],.1,atol=1e-8)


def test_exact_and_intermediate_times(tmp_path):
    path=fixture(tmp_path/'clip.glb',[0,-.2,0]);result=compare(path,path,[0,.25,.5,.75,1])
    np.testing.assert_allclose(result['target']['minimum_y_m'],[.1,0,-.1,0,.1],atol=1e-8)
    assert result['samples']==5 and result['paired_samples']['both_fail']==1


@pytest.mark.parametrize('clock',[[],[1,0],[0,0],[False,True],[0,True],[-1,0],[0,float('nan')],[0,float('inf')],[[0,1]],np.array([0,255,1],dtype=np.uint8)])
def test_invalid_clocks_rejected(tmp_path,clock):
    path=fixture(tmp_path/'clip.glb',[0,0,0])
    with pytest.raises(ValueError):compare(path,path,clock)


def test_clock_cannot_extrapolate(tmp_path):
    path=fixture(tmp_path/'clip.glb',[0,0,0])
    with pytest.raises(ValueError,match='beyond'):compare(path,path,[0,1.1])


@pytest.mark.parametrize('kwargs',[dict(floor_y_m=False),dict(floor_y_m=float('nan')),dict(tolerance_m=0),
    dict(tolerance_m=True),dict(tolerance_m=float('inf')),dict(source_animation=True)])
def test_explicit_numeric_parameters_required(tmp_path,kwargs):
    path=fixture(tmp_path/'clip.glb',[0,0,0])
    with pytest.raises(ValueError):compare(path,path,[0,.5,1],**kwargs)
