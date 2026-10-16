"""Staging retains the exact paired native rows and complete selected meshes."""
from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from test_native_pair_contact_objectives import separated
from native_pair_key_guides import PairKeyGuides
from native_contact_actor_validation import native_rows,geometry_cache


def test_staged_native_rows_recombine_to_exact_complete_pair_population(separated):
    models,_=separated;pair=PairKeyGuides(models,[],fit_contacts=True);value=pair.initial.copy();value[:]=np.tile([.005,-.004,.003],4)
    worlds=pair.worlds(value);combined,_=pair.norms(value,worlds);stages=[]
    for i,name in enumerate(pair.names):stages.append(native_rows(models[name],value[pair.offsets[i]:pair.offsets[i+1]],worlds[name]))
    for key in ('vectors','caps','scales'):np.testing.assert_array_equal(np.concatenate([getattr(r,key) for r in stages]),getattr(combined,key))


def test_selected_mesh_cache_keeps_all_vertices_faces_and_actual_placements(separated):
    models,_=separated;pair=PairKeyGuides(models,[],fit_contacts=True);worlds=pair.worlds(pair.initial)
    ids=[0,len(pair.times)//2,len(pair.times)-1]
    for name,m in models.items():
        data,report=geometry_cache(m,worlds[name],ids);p,r=m.actor['placement']
        np.testing.assert_array_equal(data['times_s'],pair.times[ids]);np.testing.assert_array_equal(data['sample_indices'],ids)
        for i,index in enumerate(ids):np.testing.assert_array_equal(data['vertices_world_m'][i],m.rig.vertices(worlds[name][index])@r.T+p)
        assert len(data['faces'])==report['faces'] and data['vertices_world_m'].shape[1]==len(m.skin.nodes)
        assert not report['complete_time_population'] and not report['quality_approved']


def test_full_clock_cache_is_explicit_and_caller_cannot_mutate_original_clock(separated):
    m=separated[0]['A'];data,report=geometry_cache(m,m.source_world,np.arange(len(m.times)))
    assert report['complete_time_population'];data['times_s'][0]+=1;assert data['times_s'][0]!=m.times[0]


@pytest.mark.parametrize('indices',[[],[True],[0,True],[1,0],[0,0],[-1],[999999],[0.5]])
def test_invalid_or_incomplete_clock_declarations_reject(separated,indices):
    m=separated[0]['A']
    with pytest.raises(ValueError):geometry_cache(m,m.source_world,indices)


def test_cache_budget_rejects_without_truncating_the_requested_population(separated):
    m=separated[0]['A']
    with pytest.raises(ValueError,match='no samples or vertices discarded'):geometry_cache(m,m.source_world,[0,1],maximum_bytes=1)


@pytest.mark.parametrize('fault',['shape','nan'])
def test_incomplete_actor_observations_cannot_become_partial_native_checks(separated,fault):
    m=separated[0]['A'];worlds=m.source_world.copy()
    if fault=='shape':worlds=worlds[:-1]
    else:worlds[0,0,0,0]=np.nan
    with pytest.raises(ValueError):native_rows(m,m.initial,worlds)
    with pytest.raises(ValueError):geometry_cache(m,worlds,[0])
