"""Full symmetric vector derivatives against uncached posed-surface oracles."""
from pathlib import Path
import sys
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from central_coupled_contacts import contact_linearize,CentralCoupledContactModel
from cached_contact_norms import CachedContactNorms
from native_contact_norms import ContactNorms
from native_scene_norms import rows
from test_native_contact_norms import prepared
from test_native_surface_contact import scene_fixture,policy
from test_cached_contact_norms import make
from strep import save


def oracle(problem,p,digest,value,column,offsets):
    reference=ContactNorms(problem,p,digest)
    def sample(h):
        other=value.copy();other[column]+=h
        return reference.sample(problem.worlds(other,quantized=False))[:2]
    a,ag=sample(offsets[0]);b,bg=sample(offsets[1] if len(offsets)==2 else 0.)
    divisor=offsets[0]-(offsets[1] if len(offsets)==2 else 0.)
    return ((a.vectors-b.vectors)/divisor).ravel(),(ag-bg)/divisor


def compare(problem,p,digest,value,decoded=None):
    contact=CachedContactNorms(problem,p,digest)
    decoded=problem.worlds(value) if decoded is None else decoded
    system,jac,meta=contact_linearize(contact,value,decoded,.02,step=1e-4)
    reference=ContactNorms(problem,p,digest);base,gaps,identity=reference.sample(decoded)
    count=base.vectors.size
    np.testing.assert_array_equal(system.caps[:len(base.caps)],base.caps)
    np.testing.assert_array_equal(system.scales[:len(base.caps)],base.scales)
    np.testing.assert_allclose(system.vectors[:len(base.caps)],base.vectors,atol=1e-12,rtol=0)
    np.testing.assert_allclose(system.residual(),reference.residual(decoded),atol=1e-10,rtol=0)
    assert meta['identity']==identity['identity']
    for col,offsets in enumerate(meta['actual_difference_offsets']):
        vector,side=oracle(problem,p,digest,value,col,offsets)
        actual=jac[:,col].toarray().ravel()
        np.testing.assert_allclose(actual[:count],vector,atol=1e-8,rtol=0)
        np.testing.assert_allclose(actual[count::3],-side,atol=1e-8,rtol=0)
        np.testing.assert_array_equal(actual[count+1::3],np.zeros(len(gaps)))
        np.testing.assert_array_equal(actual[count+2::3],np.zeros(len(gaps)))
    assert meta['norm_rows']==3*len(base.caps) and meta['stored_nonzero_jacobian_elements']==jac.nnz
    assert not meta['small_coefficients_discarded']
    return system,jac,meta


@pytest.mark.parametrize('partner',[False,True])
@pytest.mark.parametrize('hold',[False,True])
def test_world_and_partner_derivatives_keep_every_original_clock(tmp_path,partner,hold):
    problem,p,digest=prepared(tmp_path,partner=partner,hold=hold)
    _,_,meta=compare(problem,p,digest,problem.initial)
    assert meta['central_difference_columns']==problem.size and meta['column_proxy_evaluations']==2*problem.size
    assert meta['one_sided_difference_columns']==0
    assert len(meta['identity'])==len(problem.rows[0]['times'])


@pytest.mark.parametrize('centroid',[False,True])
def test_moving_object_and_complete_centroid_incident_surfaces(tmp_path,centroid):
    _,rig,reader,spec,path,_=scene_fixture(tmp_path);row=spec['contacts'][0]
    q=Rotation.from_euler('z',60,degrees=True);v=rig.vertices(reader.sample(1.))[0]
    local=np.array([0.,.2,0.]);position=v-q.apply(local)
    spec['objects']['prop']=dict(geometry=dict(schema='strep-object-geometry-v1',shape='sphere',radius_m=.2),keyframes=[
        dict(time_s=t,translation_m=position.tolist(),rotation_xyzw=Rotation.from_euler('z',angle,degrees=True).as_quat().tolist()) for t,angle in [(0.,0),(2.,120)]])
    row['target']=dict(space='object',object='prop',points_m=[local.tolist()])
    if centroid:row.update(vertices=[[6,0,0],[6,0,1]],reduction='centroid')
    row.update(mode='hold',interval_s=[.8,1.2],limits=dict(position_m=.5,relative_speed_m_s=.5))
    save(path,spec);problem,p,digest=make(spec,path,policy(path,spec))
    compare(problem,p,digest,problem.initial+np.array([.02,-.01,.03]))


@pytest.mark.parametrize('side',[-1,1])
def test_box_boundary_has_explicit_matching_origin_one_sided_fallback(tmp_path,side):
    problem,p,digest=prepared(tmp_path);x=problem.initial.copy()
    x[0]=problem.lower[0] if side<0 else problem.upper[0]
    _,_,meta=compare(problem,p,digest,x)
    assert meta['central_difference_columns']==2 and meta['one_sided_difference_columns']==1
    assert meta['column_proxy_evaluations']==5
    assert meta['actual_difference_offsets'][0]==[-side*1e-4]


def test_decoded_anchor_does_not_replace_matching_continuous_derivative_origins(tmp_path):
    problem,p,digest=prepared(tmp_path);x=problem.initial.copy();decoded=problem.worlds(x)
    stamp=np.searchsorted(problem.times,1.)
    decoded['A'][stamp,3,:3,:3]=Rotation.from_euler('x',.03).as_matrix()@decoded['A'][stamp,3,:3,:3]
    compare(problem,p,digest,x,decoded)


@pytest.mark.parametrize('option,value',[('step',True),('step',0.),('step',float('nan')),('step',.1),('trust',0.),('trust',True),('maximum_elements',True),('maximum_elements',0),('maximum_elements',1)])
def test_invalid_parameters_and_nonzero_overflow_cannot_return_partial_rows(tmp_path,option,value):
    problem,p,digest=prepared(tmp_path);contact=CachedContactNorms(problem,p,digest)
    kwargs=dict(step=1e-4,maximum_elements=60000000);trust=.02
    if option=='trust':trust=value
    else:kwargs[option]=value
    with pytest.raises(ValueError):contact_linearize(contact,problem.initial,problem.worlds(problem.initial),trust,**kwargs)


@pytest.mark.parametrize('fault',['identity','caps','scales','shape'])
def test_changing_sample_population_or_limits_is_rejected(tmp_path,monkeypatch,fault):
    problem,p,digest=prepared(tmp_path);contact=CachedContactNorms(problem,p,digest);original=contact.sample;calls=0
    def tamper(worlds):
        nonlocal calls
        system,gaps,meta=original(worlds);calls+=1
        if calls>1:
            if fault=='identity':meta['identity'][0]['point']+=1
            if fault=='caps':system.caps[0]+=1e-8
            if fault=='scales':system.scales[0]+=1e-8
            if fault=='shape':gaps=gaps[:1]
        return system,gaps,meta
    monkeypatch.setattr(contact,'sample',tamper)
    with pytest.raises(ValueError,match='population'):contact_linearize(contact,problem.initial,problem.worlds(problem.initial),.02)


def test_full_coupled_model_keeps_original_native_rows_and_individual_contact_guards(tmp_path):
    problem,p,digest=prepared(tmp_path,hold=True);model=CentralCoupledContactModel(problem,p,digest)
    x=problem.initial.copy();worlds=problem.worlds(x);native=rows(problem,x,worlds)
    before=ContactNorms(problem,p,digest).residual(worlds)
    system,jac,meta=model.linearize(x,worlds,.02,step=1e-4);n=len(native.caps);c=len(before)
    np.testing.assert_array_equal(system.caps[:n],native.caps);np.testing.assert_array_equal(system.scales[:n],native.scales)
    np.testing.assert_allclose(system.residual()[:n],problem.constraints(x,worlds),atol=1e-9,rtol=0)
    np.testing.assert_allclose(system.residual()[n:n+c],np.minimum(before,0),atol=1e-9,rtol=0)
    np.testing.assert_allclose(system.residual()[-c:],before,atol=1e-9,rtol=0)
    np.testing.assert_array_equal(jac[3*n:3*(n+c)].toarray(),jac[-3*c:].toarray())
    assert meta['hard_rows']==n+c and meta['complete_native_rows']==n and meta['complete_surface_contact_rows']==c
    assert meta['native']['central_difference_columns']==problem.size==meta['contact']['central_difference_columns']
    assert meta['independent_decode_and_full_geometry_required'] and not meta['quality_approved'] and not meta['release_approved']


def test_source_caps_and_asset_changes_still_reject(tmp_path):
    problem,p,digest=prepared(tmp_path);model=CentralCoupledContactModel(problem,p,digest);worlds=problem.worlds(problem.initial)
    problem.caps['A'].caps[0][0,0]+=1e-8
    with pytest.raises(ValueError,match='caps changed'):model.linearize(problem.initial,worlds,.02)
    problem,p,digest=prepared(tmp_path);contact=CachedContactNorms(problem,p,digest)
    path=Path(next(iter(problem.scene.inputs)));path.write_bytes(path.read_bytes()+b'mutation')
    with pytest.raises(ValueError):contact_linearize(contact,problem.initial,problem.worlds(problem.initial),.02)
