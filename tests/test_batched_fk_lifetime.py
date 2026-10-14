"""Batch transforms must not retain pose arrays until cyclic GC runs."""
from pathlib import Path
import sys,gc,weakref
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from paired_guarded_temporal import world_from_local


def test_input_and_output_batches_release_without_cyclic_collection():
    enabled=gc.isenabled();gc.disable()
    try:
        local=np.tile(np.eye(4),(12,4,1,1));world=world_from_local(local,[2,-1,1,-1])
        source_ref,result_ref=weakref.ref(local),weakref.ref(world)
        del local,world
        assert source_ref() is None and result_ref() is None
    finally:
        if enabled:gc.enable()


def test_unordered_forest_matches_independent_matrix_products_exactly():
    local=np.tile(np.eye(4),(7,4,1,1))
    local[:,1,:3,:3]=Rotation.from_euler('z',np.linspace(-.3,.4,7)).as_matrix()
    local[:,1,0,3]=3.;local[:,2,1,3]=2.;local[:,0,2,3]=1.;local[:,3,0,3]=-4.
    expected=np.stack([(local[:,1]@local[:,2])@local[:,0],local[:,1],local[:,1]@local[:,2],local[:,3]],axis=1)
    np.testing.assert_array_equal(world_from_local(local,[2,-1,1,-1]),expected)


def test_long_valid_chain_does_not_depend_on_python_recursion_limit():
    count=1500;local=np.tile(np.eye(4),(1,count,1,1));local[:,:,0,3]=1.
    parents=list(range(1,count))+[-1];world=world_from_local(local,parents)
    np.testing.assert_array_equal(world[0,:,0,3],np.arange(count,0,-1))


@pytest.mark.parametrize('parents',[[0],[1,0],[2,0,1]])
def test_cycles_still_reject(parents):
    local=np.tile(np.eye(4),(2,len(parents),1,1))
    with pytest.raises(ValueError,match='Cyclic node hierarchy'):world_from_local(local,parents)
