# Three-key hand trajectory correction

This development experiment extends the failed single-key hand-orientation
search across three existing editable poses. It tests whether more trajectory
freedom can reduce the late partner-hand collision while keeping the original
motion limits and final contact pose. It is not a release or universal-motion
claim. See [the preceding experiment](paired-oriented-hand-v1.md).

## Controls and audit scope

Each editable pose has eleven controls: a symmetric scene-space wrist offset
(three components), two elbow swivels, and separate scene-space hand rotation
vectors for the two actors (six components). The three editable times are
1.941387296, 1.991499066 and 2.041610718 seconds. Their surrounding frozen keys
are at 1.891275048 and 2.091722488 seconds.

The parameter domain bounds Euclidean wrist displacement and each hand rotation
vector, as well as each elbow angle. Adjacent parameter differences, including
the zero endpoint controls, obey the source plan's wrist/elbow guide rates and
a 300 degree/second hand rotation-vector rate. These guide bounds do not certify
decoded angular velocity: the actual sampled joint-motion constraints remain
separate and mandatory. Native quaternion edits remain limited to 45 degrees.

The solve constrains 29 original 120 Hz poses (indices 58 through 86), including
two unchanged poses on each side of the affected support. Hand geometry covers
25 poses (indices 60 through 84), in both source/target directions. Each source
hand includes 2,933 vertices and is queried against the other actor's full
18,056-vertex mesh. This is a hand-to-body screen, not full-body clearance.

The 26 donor directional source queries are reused only after input, method,
population and witness checks. The earlier 24 directions are measured anew.
The solver uses fixed source correspondences and outward normals as a search
objective; those values are not treated as final mesh-clearance evidence.

Two SLSQP starts use 100 iterations each: zero controls, and a tapered three-key
version of the prior oblique wrist/elbow/hand seed. Only controls independently
passing every physical margin can become the incumbent. Solver status or an
epigraph value cannot override that gate. After selection, actual float32 GLBs
are decoded and audited against the complete 148-pose source clock, stored
frozen keys and protected poses. Fresh directional hand queries then measure
the selected candidate across all 25 affected times.

## Reproduction and validation

Local ignored assets and hash-bound prior studies are required; use a fresh
output directory:

```powershell
.venv/Scripts/python.exe -u scripts/fit_continuous_terminal_hand.py reports/scene-pair-terminal-hand-search-v1 reports/scene-pair-multikey-hand-v1 --hand-orientation --editable-keys 3 --witness-study reports/scene-pair-oriented-hand-v1
```

Tests verify both actors under oblique scene placements at all three editable
keys, independently decoded GLB playback, shared sampler isolation, exact
frozen quaternion keys, unchanged arm tracks during a hand-only edit, complete
support halos, and adjacent-rate/diagonal-vector rejection. A 33-dimensional
optimizer fixture verifies the final key is active. The focused development
suite passed 22 tests, and the minimal public Python suite passed 642 tests.
The preceding commit `3aeee85` passed hosted CI.

## Completed result

The worker completed with 936 source witnesses and 8,265 recorded evaluations
(including finite differences and repeated controls). Of these, 189 passed the
motion/domain gate. Both starts reached their 100-iteration limit without
convergence. The first returned point failed physical constraints; its 0.9
backoff passed. The second returned point passed physical constraints, but its
epigraph underestimated the measured objective. Selection still used measured
depth, choosing evaluation 8,025 with a witness peak of 20.927519 mm.

Fresh mesh queries confirm a **21.433380 to 20.932848 mm** peak reduction on the
same 25-time hand population: **0.500532 mm** improvement. However, **15 / 25**
times fail the 5 mm threshold both before and after. Eight times have increased
penetration by more than 1e-8 m; the largest regression is **0.938765 mm** at
1.991666667 seconds (sample 72). No previously passing time becomes failing.
Reducing the maximum alone does not establish local non-regression or clearance.

Both selected GLBs have zero batched/scalar replay error, exact stored frozen
keys, unchanged outside-support poses, and zero original-bin positional or
angular violations over the full 148-pose clock. Maximum native quaternion edit
is 3.928398 degrees. The physical motion result is a real nonzero edit, unlike
the unchanged source retained by the preceding one-key study. It is still an
unacceptable interaction because hand penetration remains substantial.

No full-body whole-clock mesh audit, engine audit, Studio replacement, human
approval, training or model/data acquisition occurred. All 14 release
capabilities remain unapproved.

## Return diagnosis and next experiment

`diagnose_oriented_hand_returns.py` verifies completed study artifacts and method
snapshots, exports the selected controls and both solver returns, independently
decodes their complete clocks, and identifies the joints/times that violate
the unchanged caps. It also compares source and candidate hand geometry at
matching times and maps each actor's peak source vertex through the skin palette.
It does not generate new mesh measurements or approve a candidate.

```powershell
.venv/Scripts/python.exe -u scripts/diagnose_oriented_hand_returns.py reports/scene-pair-multikey-hand-v1 reports/scene-pair-multikey-hand-diagnosis-v1
```

The diagnosis completed. The selected controls and second return have no
decoded motion violations. The first return has 2 positional-speed, 8
positional-acceleration, 3 angular-speed and 3 angular-acceleration violations.
Its largest acceleration excesses are 0.025534 m/s^2 at B's forearm and
0.038583 rad/s^2 at B's index-finger end joint, both at 1.941666667 seconds.
These are measured failures, not evidence that increasing a solver tolerance
would be acceptable.

The selected candidate's deepest A vertex (776, at 2.033333333 seconds) is
94.17% weighted to `LeftHand`. B's deepest vertex (6871, at 2.066666667 seconds)
is 81.01% weighted to `LeftHand`, with ring/pinky and forearm contributions.
This attribution does not identify a uniquely thumb-driven residual. The next
experiment should extend the coherent wrist/hand adjustment earlier in the
permitted approach, warm-start from these verified feasible controls, preserve
the contact endpoint and existing caps, and re-audit matching times for local
regressions. Do not claim global infeasibility from these two finite starts.

The final minimal public Python suite passes **647 tests**. The return evidence
tests reject incomplete studies, modified artifacts, changed snapshots and
changed current methods. The main worker and diagnostic are terminal; the
implementation commit `8d2d0b6` passed hosted CI.


## Evidence hashes

| Artifact | SHA-256 |
|---|---|
| Study: request | `6e504ae42338150e32cf9f32a1779cba2ea3fa49f6df239a336bba590b90a3ca` |
| Study: witnesses | `4fc493c920d484f1165b4a992202dfbabf1d0a131b6f1eadb1de4eac0547b57e` |
| Study: source_queries | `f3e8aa9d6125e38aa7611ea669a218b118ce0bb07299c78b6350b99afdafd42e` |
| Study: selected | `7cb4340854ec8eeee3200f14142c25ff935e9e8e8e47de97bdd467516befa7b2` |
| Study: solvers | `a70a32d43bc2f3b44f0160d142d8f4cf412afa1d7476856b018d82f81586fcc0` |
| Study: evaluations | `c261fd94782284262e8a80ea5c0325aa9a637fcbc01f256124290876da321359` |
| Study: decoded | `da154139ee8d9db6b6c5f048774cb98dd733a3d5955f8fe3274f73de8c4f99fd` |
| Study: geometry | `f62de74d2f66902221ad2b7fd12ca05599e4959d9042793fd634f41db6dd8b58` |
| Diagnosis: request | `a88453801a4d6f00d81fa0ab2d35bb4aad0712017c15446282aa5d69fcf7af3d` |
| Diagnosis: returns | `71521797288d6b2f5bd404c3e80dcfb174a73b0948c9f89f96802c97982be78b` |
| Diagnosis: geometry_attribution | `076718f8d9f5de2bb374ee67d6a098d637cc35a21bb199025411b8c21d69a7ce` |
| Diagnosis: hand_comparison | `f4d8d39bfbdf4227cdac9632d0fb935317c061eac6cfb18ba65a98aa0ff05298` |
