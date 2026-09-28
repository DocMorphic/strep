import sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
import trimesh
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from dynamic_contact_witness import DynamicWitnessSurface
from rig_clearance_fit import right_jacobian


class Actor:
    def __init__(self,vertices,placement):
        self.vertices=vertices;self.rotation=np.eye(3);self.translation=np.asarray(placement);self.dim=6
        self.rig=SimpleNamespace(vertices=lambda pose:pose)
    def pose(self,frame,x):return self.vertices@Rotation.from_rotvec(x[3:]).as_matrix().T+x[:3]
    def skin_pair(self,frame,x,ids):
        points=self.pose(frame,x)[ids]+self.translation
        rotation=Rotation.from_rotvec(x[3:]).as_matrix();axis=rotation@right_jacobian(x[3:])
        moved=self.vertices[ids]@rotation.T
        jac=np.zeros((len(ids),3,6));jac[:,:,:3]=np.eye(3)
        jac[:,:,3:]=np.cross(axis.T[None,:,:],moved[:,None,:]).transpose(0,2,1)
        return points,jac


def fixture(keys=None):
    mesh=trimesh.creation.icosphere(subdivisions=1)
    actors=[Actor(mesh.vertices,[0,0,0]),Actor(mesh.vertices,[.61,.23,.17])]
    fitter=SimpleNamespace(actors=actors,sizes=[6,6],witness_faces=mesh.faces)
    return DynamicWitnessSurface(fitter,.5,keys if keys is not None else [(0,1,11),(1,0,17)]),fitter


def test_dynamic_values_and_derivative_match_independent_requeries():
    surface,f=fixture();x=np.array([.01,-.03,.02,.02,.015,-.03,-.02,.01,.025,-.01,.03,.02])
    value,jac=surface.clearance(x,.003);eps=1e-6
    fd=np.column_stack([(surface.clearance(x+np.eye(len(x))[i]*eps,.003)[0]-surface.clearance(x-np.eye(len(x))[i]*eps,.003)[0])/(2*eps) for i in range(len(x))])
    np.testing.assert_allclose(jac,fd,atol=2e-6,rtol=2e-5)
    vertices=[a.pose(.5,p)+a.translation for a,p in zip(f.actors,np.split(x,2))]
    expected=[]
    for source,target,vertex in surface.keys:
        mesh=trimesh.Trimesh(vertices[target],f.witness_faces,process=False)
        expected.append(-trimesh.proximity.signed_distance(mesh,[vertices[source][vertex]])[0]-.003)
    np.testing.assert_allclose(value,expected,atol=1e-12)


def test_margin_changes_without_stale_geometry_and_pose_changes_requery():
    surface,_=fixture();x=np.zeros(12)
    a=surface.clearance(x,0)[0];b=surface.clearance(x,.01)[0]
    np.testing.assert_allclose(a-b,.01)
    x[0]+=.1;c=surface.clearance(x,0)[0]
    assert np.max(abs(c-a))>1e-3


def test_empty_rows_preserve_derivative_shape():
    surface,_=fixture([]);v,j=surface.clearance(np.zeros(12))
    assert v.shape==(0,) and j.shape==(0,12)


@pytest.mark.parametrize('keys',[[(0,0,1)],[(0,1,-1)],[(0,1,1.5)],[(0,1,True)],[(0,1,1),(0,1,1)]])
def test_invalid_witnesses_rejected(keys):
    with pytest.raises(ValueError):fixture(keys)
