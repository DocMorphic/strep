import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from contact_pair_barriers import SeparatedPairBarriers
from triangle_crossing import classify


class Skin:
    def evaluate(self, world, frames, vertices): return world[frames, vertices]


def fixture():
    a = np.array([[0., 0, 0], [1., 0, 0], [0, 1., 0], [2., 0, 0], [3., 0, 0], [2, 1., 0]])
    b = np.vstack([a[:3]*.6+[.1, .1, .002], (a[3:]-[2, 0, 0])*.6+[2.1, .1, .002]])
    faces = np.array([[0, 1, 2], [3, 4, 5]])
    worlds = [np.array([a]), np.array([b])]
    placements = [dict(rotation=np.eye(3), translation=np.zeros(3)) for _ in range(2)]
    return SeparatedPairBarriers([Skin(), Skin()], placements, [faces, faces], worlds, frame=0), worlds


def test_source_separation_is_hard_for_new_crossing():
    cuts, world = fixture(); assert cuts.add([[0, 0]]) == 1
    assert np.all(cuts.margins(world) > 0)
    candidate = [v.copy() for v in world]; candidate[1][0, 0, 2] = -.002
    assert classify(candidate[0][0, :3], candidate[1][0, :3])['kind'] == 'proper_crossing'
    assert np.any(cuts.margins(candidate) < 0)
    assert not cuts.record()['quality_approved']


def test_accumulation_never_rebases_existing_axes_or_floors():
    cuts, world = fixture(); cuts.add([[0, 0]]); first = cuts.record()['rows'][0]
    world[1][0, :, 2] += 2.  # External mutation must not alter the original source.
    assert cuts.add([[0, 0], [1, 1]]) == 1
    assert cuts.record()['rows'][0] == first
    assert cuts.record()['pairs'] == 2 and cuts.record()['scalar_rows'] == 18
    assert cuts.record()['rows'][1]['original_gap_m'] < .003


def test_nonseparated_batch_does_not_partially_modify_existing_pool():
    cuts, _ = fixture(); cuts.add([[0, 0]]); before = cuts.record()
    # A newly created instance whose second pair is already intersecting.
    _, worlds = fixture(); worlds[1][0, 3, 2] = -.002
    faces = np.array([[0, 1, 2], [3, 4, 5]])
    places = [dict(rotation=np.eye(3), translation=np.zeros(3)) for _ in range(2)]
    other = SeparatedPairBarriers([Skin(), Skin()], places, [faces, faces], worlds, frame=0)
    with pytest.raises(ValueError, match='strictly separated'): other.add([[0, 0], [1, 1]])
    assert other.record()['pairs'] == 0 and cuts.record() == before


def test_empty_and_duplicate_batches_keep_fixed_population():
    cuts, world = fixture(); assert cuts.add([]) == 0 and cuts.margins(world).size == 0
    assert cuts.add([[0, 0], [0, 0]]) == 1
    assert cuts.add([[0, 0]]) == 0 and cuts.margins(world).shape == (9,)


def test_invalid_pair_indices_fail_closed():
    cuts, _ = fixture()
    for pairs in [[[0, 9]], [[-1, 0]], [[0., 0.]], [0, 1]]:
        with pytest.raises(ValueError, match='indices'): cuts.add(pairs)


def test_exported_record_cannot_mutate_frozen_axes():
    cuts, _ = fixture(); cuts.add([[0, 0]]); expected = cuts.record()
    record = cuts.record(); record['rows'][0]['axis'][0] = 17.
    cuts.add([[1, 1]])
    assert cuts.record()['rows'][0] == expected['rows'][0]
