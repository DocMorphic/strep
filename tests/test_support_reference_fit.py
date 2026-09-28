import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import numpy as np
from scipy.optimize import least_squares
from support_reference_fit import reference_pair


def test_full_support_can_reach_anchor_without_preserving_original_slide():
    reference=np.array([[.12,0.,0.],[.12,0.,.02]])
    jac=np.zeros((2,3,1));jac[:,0,0]=1.
    def residual(x,weight):
        positions=reference.copy();positions[:,0]+=x[0]
        r,j=reference_pair(positions,jac,reference,[0,1],weight)
        return np.r_[r,positions[:,0].mean()*40.]
    old=least_squares(lambda x:residual(x,0.),[0.]).x
    revised=least_squares(lambda x:residual(x,1.),[0.]).x
    np.testing.assert_allclose(.12+old[0],.12*900/2500,atol=1e-8)
    np.testing.assert_allclose(.12+revised[0],0.,atol=1e-8)


def test_unplanted_reference_and_faded_derivatives():
    reference=np.array([[.1,.2,.3],[.2,.3,.4]])
    jac=np.arange(12,dtype=float).reshape(2,3,2)/20
    x=np.array([.01,-.02]);positions=reference+np.einsum('vij,j->vi',jac,x)
    r,d=reference_pair(positions,jac,reference,[0,1],.25)
    eps=1e-7
    columns=[]
    for axis in range(2):
        plus=reference_pair(positions+eps*jac[:,:,axis],jac,reference,[0,1],.25)[0]
        minus=reference_pair(positions-eps*jac[:,:,axis],jac,reference,[0,1],.25)[0]
        columns.append((plus-minus)/(2*eps))
    np.testing.assert_allclose(d,np.column_stack(columns),atol=1e-8)
    original=reference_pair(positions,jac,reference,[0,1],0.)[0]
    np.testing.assert_allclose(r,np.sqrt(.75)*original)
    np.testing.assert_allclose(reference_pair(reference,jac,reference,[0,1],0.)[0],0.)
