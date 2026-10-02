"""Independent analytical foot drift and bound native geometry diagnostics."""
import copy
from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from native_contact_diagnostics import measure, patch_metrics
from gltf_tools import append_accessor, write_glb
from strep import sha256
from test_native_support import fixture


def test_flat_height_can_coexist_with_sliding_fixed_vertices():
    points = np.array([[[0., 0., 0.], [1., 0., 0.]], [[.03, 0., .04], [1.03, 0., .04]]])
    result = patch_metrics(points, [0.,1.,0.], 0., [0., .5], [0,1])
    assert result['minimum_region_height_m'] == result['maximum_lowest_region_height_m'] == 0
    assert result['maximum_patch_vertex_tangential_drift_m'] == pytest.approx(.05)
    assert result['maximum_patch_vertex_tangential_speed_m_s'] == pytest.approx(.1)
    assert not result['planted_contact_certified']


def test_tilted_plane_removes_normal_motion_from_drift_and_preserves_height():
    normal = np.array([0.,1.,1.])/np.sqrt(2)
    points = np.array([[[0.,0.,0.]], [[0.,0.,0.]]])+np.array([0., .02])[:,None,None]*normal
    result = patch_metrics(points, normal, -.01, [0.,.2], [0])
    assert result['maximum_patch_vertex_tangential_drift_m'] < 1e-17
    assert result['maximum_patch_vertex_tangential_speed_m_s'] < 1e-16
    assert result['maximum_sampled_region_penetration_m'] == pytest.approx(.01)
    assert result['maximum_lowest_region_height_m'] == pytest.approx(.01)


@pytest.mark.parametrize('fault', ['nonfinite','clock','duplicate','empty','normal','shape'])
def test_invalid_geometric_populations_rejected(fault):
    points=np.zeros((2,2,3)); normal=[0.,1.,0.]; times=[0.,1.]; patch=[0,1]
    if fault=='nonfinite': points[0,0,0]=float('nan')
    if fault=='clock': times=[1.,1.]
    if fault=='duplicate': patch=[0,0]
    if fault=='empty': patch=[]
    if fault=='normal': normal=[0.,2.,0.]
    if fault=='shape': points=points[:,:,:2]
    with pytest.raises(ValueError): patch_metrics(points,normal,0.,times,patch)


def test_native_translation_exposes_drift_without_changing_mesh_or_source(tmp_path):
    source,rig,reader,spec=fixture(tmp_path)
    digest=sha256(source)
    document=copy.deepcopy(rig.document); binary=bytearray(rig.binary)
    clock=reader.channels[-1][2]; positions=np.tile([0.,1.2,0.],(len(clock),1))
    positions[:,0]=.05*clock
    positions[:,1]+=.06*np.maximum(0,np.abs(clock-1)-.3)
    accessor=append_accessor(document,binary,positions,'VEC3')
    document['animations'][0]['samplers'][1]['output']=accessor
    candidate=tmp_path/'sliding.glb';write_glb(candidate,document,binary)
    result=measure(source,candidate,spec);support=result['supports'][0]
    assert result['inputs_sha256'][str(source.resolve())]==digest==sha256(source)
    assert support['times_s'][0]==.8 and support['times_s'][-1]==1.2
    assert support['patch_vertices']==3 and support['region_vertices']==3
    assert support['source']['maximum_patch_vertex_tangential_drift_m']<1e-15
    assert support['candidate']['maximum_patch_vertex_tangential_drift_m']==pytest.approx(.02,abs=1e-8)
    assert support['candidate']['maximum_patch_vertex_tangential_speed_m_s']==pytest.approx(.05,abs=1e-6)
    assert not result['changes_acceptance_gates'] and not result['planted_contact_certified']
    assert not result['quality_approved']


def test_misbound_source_and_changed_geometry_rejected(tmp_path):
    source,rig,_,spec=fixture(tmp_path)
    bad=copy.deepcopy(spec);bad['glb_sha256']='0'*64
    with pytest.raises(ValueError,match='another'): measure(source,source,bad)
    document=copy.deepcopy(rig.document);document['nodes'][3]['name']='different-foot'
    candidate=tmp_path/'changed.glb';write_glb(candidate,document,rig.binary)
    with pytest.raises(ValueError,match='geometry'): measure(source,candidate,spec)


def test_same_accessor_identity_does_not_hide_changed_vertex_payload(tmp_path):
    source,rig,_,spec=fixture(tmp_path)
    document=copy.deepcopy(rig.document);binary=bytearray(rig.binary)
    position=document['accessors'][document['meshes'][0]['primitives'][0]['attributes']['POSITION']]
    view=document['bufferViews'][position['bufferView']]
    values=np.frombuffer(binary,dtype='<f4',count=9,offset=view.get('byteOffset',0)+position.get('byteOffset',0))
    values[0]+=.1
    candidate=tmp_path/'changed-payload.glb';write_glb(candidate,document,binary)
    with pytest.raises(ValueError,match='payload'): measure(source,candidate,spec)
