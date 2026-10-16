import copy,sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_surface_frame import measure
from native_surface_frame_pair import pair
from test_native_surface_frame import data


LIMITS=dict(position_m=.005,normal_degrees=5,tangent_degrees=15)


def frames(gap=.004):
    p,f,s=data();j=np.zeros((len(p),3,3))
    return measure(p,j,f,s),measure(p+[0,0,gap],j,f[:,::-1],s)


@pytest.mark.parametrize('gap,passed',[(.004,True),(.014,False)])
def test_actual_pair_gap_is_separate_from_each_world_target(gap,passed):
    a,b=frames(gap);rows,jac=pair(a,b,LIMITS)
    assert bool(np.all(rows.residual()<=0)) is passed and jac.shape==(9,6)


@pytest.mark.parametrize('relationship',[dict(normal_sign=1),dict(tangent_sign=-1)])
def test_signed_normal_and_tangent_relationships_are_not_interchangeable(relationship):
    a,b=frames();rows,_=pair(a,b,LIMITS,**relationship);assert np.any(rows.residual()>0)


def test_independent_pair_jacobian_matches_fresh_geometry_on_both_actors():
    p,f,s=data();rng=np.random.default_rng(19);ja=rng.normal(size=(4,3,2))*.03;jb=rng.normal(size=(4,3,3))*.03
    a=measure(p,ja,f,s);b=measure(p+[0,0,.004],jb,f[:,::-1],s);rows,jac=pair(a,b,LIMITS);h=1e-6
    for k in range(5):
        values=[]
        for sign in (1,-1):
            pa=p+sign*h*ja[:,:,k] if k<2 else p
            pb=p+[0,0,.004]+(sign*h*jb[:,:,k-2] if k>=2 else 0)
            aa=measure(pa,ja,f,s);bb=measure(pb,jb,f[:,::-1],s);values.append(pair(aa,bb,LIMITS)[0].vectors.ravel())
        np.testing.assert_allclose(jac[:,k],(values[0]-values[1])/(2*h),atol=1e-9,rtol=2e-8)


def test_shared_control_basis_cancels_common_translation_without_duplicate_variables():
    p,f,s=data();j=np.repeat(np.eye(3)[None],4,axis=0);a=measure(p,j,f,s);b=measure(p+[0,0,.004],j,f[:,::-1],s)
    rows,jac=pair(a,b,LIMITS,shared_controls=True);assert jac.shape==(9,3)
    np.testing.assert_array_equal(jac,np.zeros_like(jac));assert np.all(rows.residual()<=0)


@pytest.mark.parametrize('fault',['ownership','normal-sign','tangent-sign','shared-width','bad-normal','nonfinite-jacobian'])
def test_ambiguous_ownership_invalid_frames_or_signs_reject(fault):
    a,b=frames();kwargs={}
    if fault=='ownership':kwargs['shared_controls']='yes'
    elif fault=='normal-sign':kwargs['normal_sign']=True
    elif fault=='tangent-sign':kwargs['tangent_sign']=0
    elif fault=='shared-width':
        kwargs['shared_controls']=True
        for k in ('origin_jacobian','normal_jacobian','tangent_jacobian'):b[k]=b[k][:,:2]
    elif fault=='bad-normal':a['normal_world']*=2
    else:b['normal_jacobian'][0,0]=np.nan
    with pytest.raises(ValueError):pair(a,b,LIMITS,**kwargs)
