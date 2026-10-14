"""Float32 grid coordinates retain the actual scalar root-axis coefficient."""
from pathlib import Path
import copy,sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_vertical_storage import coordinates
from test_native_vertical_root import grid_recipe,recipe
from rig_asset import RigAsset
from gltf_tools import local_matrix,write_glb
from rig_floor_comparison import compare
from strep import read,save,sha256
import native_vertical_root as root


@pytest.mark.parametrize('factor',[1.,np.nextafter(1.,2.),np.nextafter(1.,0.),-1.,-np.nextafter(1.,2.),-np.nextafter(1.,0.)])
def test_native_grid_maps_the_real_axis_coefficient_without_rounding_it(factor):
    values=np.array([[0.,0.,.5],[0.,0.,.25]])
    spacing,base,lower,upper=coordinates(values,np.array([0.,0.,factor]),.2,[1])
    # Both edit ranges have maximum magnitude in [0.5,1), so one native grid
    # unit is exactly 2^-24. The world-offset unit includes the actual factor.
    assert spacing[0]==2.**-24/abs(factor) and base[0]==0
    controls=np.array([17.,0.]);offsets=base+spacing*controls
    stored=(values[:,2]+offsets*factor).astype(np.float32)
    expected=np.array([.5+np.sign(factor)*17*2.**-24,.25],np.float32)
    np.testing.assert_array_equal(stored,expected)
    assert np.all(controls>=lower) and np.all(controls<=upper) and offsets[1]==0


def test_nonunit_axis_grid_runs_real_native_export_with_original_bounds(grid_recipe,tmp_path):
    path,value,source,floor=grid_recipe;rig=RigAsset.load(source)
    document=copy.deepcopy(rig.document);parent=int(rig.parents[value['source']['root_node']])
    matrix=local_matrix(document['nodes'][parent]);matrix[1,1]=1/np.nextafter(1.,2.)
    node=document['nodes'][parent]
    for key in ('translation','rotation','scale'):node.pop(key,None)
    node['matrix']=matrix.T.reshape(-1).tolist()
    write_glb(source,document,rig.binary);value['source']['sha256']=sha256(source)
    prior=read(floor);save(floor,compare(source,source,prior['times_s'],floor_y_m=prior['floor_y_m'],tolerance_m=prior['tolerance_m']))
    value['floor_reference']['sha256']=sha256(floor);save(path,value)
    axis=root.prepare(value,path.parent)[4]
    assert axis[1]==np.nextafter(1.,2.) and np.count_nonzero(axis)==1
    result=root.run(path,tmp_path/'proposal')
    assert result['sampled_conditions_pass'] and result['rate_failures']==[0,0,0,0]
    assert result['floor_failed_samples']==0 and result['all_linear_transforms_preserved']
    assert result['maximum_joint_displacement_m']<=value['maximum_displacement_m']
    assert result['maximum_horizontal_joint_drift_m']<=1e-7
    assert result['frozen_keys_and_other_tracks_preserved'] and result['original_selected']
