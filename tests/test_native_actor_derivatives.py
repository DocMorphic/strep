from pathlib import Path
import copy,sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from test_native_pair_contact_objectives import separated
from native_contact_actor_validation import native_rows
from native_actor_derivatives import linearize
from native_pair_key_guides import PairKeyGuides


@pytest.mark.parametrize('at_box',[False,True])
def test_current_derivatives_match_independent_pair_native_rows(separated,at_box):
    models,_=separated;model=models['A'];pair=PairKeyGuides(models,[],fit_contacts=True);point=np.tile([.01,-.02,.015],2)
    if at_box:point[0]=1.;point[1]=-1.
    source=native_rows(model,model.initial,model.source_world)
    before=(source.caps.copy(),source.scales.copy());base,jac,meta=linearize(model,point,source_caps=source.caps,source_scales=source.scales)
    def actual(value):
        both=pair.initial.copy();both[:model.size]=value;rows,_=pair.norms(both,pair.worlds(both,quantized=False));return rows.vectors[:len(source.caps)]
    # Independently sampled pair rows at twice the production step. A 2e-6
    # reference amplifies angular-acceleration cancellation on this fixture.
    columns=[];h=2e-4
    for column in range(model.size):
        d=np.eye(model.size)[column]*h
        if abs(point[column])==1:
            d*=-np.sign(point[column]);columns.append(((-3*actual(point)+4*actual(point+d)-actual(point+2*d))/(2*d[column])).ravel())
        else:columns.append(((actual(point+d)-actual(point-d))/(2*h)).ravel())
    np.testing.assert_allclose(jac.toarray(),np.stack(columns,axis=1),atol=3e-6,rtol=3e-5)
    expected=native_rows(model,point,model.worlds(point));np.testing.assert_array_equal(base.vectors,expected.vectors)
    np.testing.assert_array_equal(base.caps,before[0]);np.testing.assert_array_equal(base.scales,before[1])
    assert meta['all_control_columns_evaluated'] and meta['original_source_epoch'] and not meta['quality_approved']
    assert ('one-sided-second-order' in meta['difference_schemes'])==at_box


def test_bounded_stencils_match_closed_form_and_keep_small_nonzeros(monkeypatch):
    from types import SimpleNamespace
    import native_actor_derivatives as module
    from native_scene_norms import NormRows
    m=SimpleNamespace(size=3,name='analytic',seed=np.zeros((1,1,3)),initial=np.zeros(3),source_world=np.zeros(3),lower=-np.ones(3),upper=np.ones(3),check=lambda:None,controls=lambda x:x,worlds=lambda x,quantized=True:np.asarray(x))
    def rows(model,value,worlds):
        a,b,c=worlds
        return NormRows([[np.sin(a),np.cos(b),c**3],[a*b,b*b,c*c],[1e-12*a,0,0]],[10,10,10],[1,1,1])
    monkeypatch.setattr(module,'native_rows',rows);point=np.array([1.,-1.,.2]);_,jac,_=linearize(m,point,source_caps=[10]*3,source_scales=[1]*3)
    expected=np.zeros((9,3));expected[0,0]=np.cos(1);expected[1,1]=-np.sin(-1);expected[2,2]=3*.2**2;expected[3,:2]=[-1,1];expected[4,1]=-2;expected[5,2]=.4;expected[6,0]=1e-12
    np.testing.assert_allclose(jac.toarray(),expected,atol=5e-9,rtol=1e-6);assert jac[6,0]!=0


def test_supplied_complete_worlds_anchor_vectors_without_replacing_original_bounds(separated):
    m=separated[0]['A'];source=native_rows(m,m.initial,m.source_world);worlds=m.worlds(m.initial)
    base,_,meta=linearize(m,m.initial,source_caps=source.caps,source_scales=source.scales,worlds=worlds)
    np.testing.assert_array_equal(base.vectors,native_rows(m,m.initial,worlds).vectors);assert meta['caller_provided_worlds'] and meta['anchor_original_native_pass']


@pytest.mark.parametrize('fault',['caps','scales','short','bool','nan','outside','seed','step','budget','worlds'])
def test_changed_or_incomplete_native_epoch_and_budget_reject(separated,fault):
    m=copy.copy(separated[0]['A']);source=native_rows(m,m.initial,m.source_world);value=m.initial.copy();kwargs=dict(source_caps=source.caps.copy(),source_scales=source.scales.copy())
    if fault=='caps':kwargs['source_caps'][0]+=.001
    elif fault=='scales':kwargs['source_scales'][0]*=2
    elif fault=='short':value=value[:-1]
    elif fault=='bool':value=[False]*m.size
    elif fault=='nan':value[0]=np.nan
    elif fault=='outside':value[0]=1.01
    elif fault=='seed':m.seed=m.seed.copy();m.seed[m.active[0],m.active_tracks[0],0]=.001
    elif fault=='step':kwargs['step']=True
    elif fault=='budget':kwargs['maximum_nonzeros']=1
    else:kwargs['worlds']=m.source_world[:-1]
    with pytest.raises(ValueError):linearize(m,value,**kwargs)
