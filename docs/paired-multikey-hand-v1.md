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

## Study status

The study is running. No candidate, clearance improvement or release approval
is asserted until its output audits finish. Historical studies and Studio's
published candidate remain unchanged.
