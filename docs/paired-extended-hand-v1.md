# Earlier hand-approach correction with a verified warm start

The preceding [three-key study](paired-multikey-hand-v1.md) produced a nonzero
correction that obeyed the original motion limits, but still had 20.932848 mm
peak hand penetration and 15 failing hand sample times. Its worst remaining
vertices were chiefly hand-weighted. This experiment gives the wrist/hand
trajectory more time to change while preserving the final contact pose.

## Scope

Six editable native keys span 1.791051507 through 2.041610718 seconds, surrounded
by frozen keys at 1.740939498 and 2.091722488 seconds. There are 66 controls:
per-key symmetric wrist displacement, two elbow swivels, and separate hand
orientation vectors for both actors. Original guide rates, 45-degree native edit
budget, protected poses and original-bin sampled motion limits are unchanged.

The solve checks 47 original 120 Hz poses, indices 40 through 86, including
two frozen halo poses on each side. Hand geometry covers 43 times, indices 42
through 84, in both source/target directions. Each source hand has 2,933 eligible
vertices, queried against the other actor's full 18,056-vertex mesh. This does
not establish whole-body clearance or continuous collision freedom.

The two SLSQP starts are zero controls and the prior selected three-key controls
embedded unchanged into the later three editable poses. The three earlier
editable poses initially have zero controls. Each start has 100 iterations;
only physically feasible measured candidates can become the selected result.
Fixed source witnesses remain a search approximation, followed by fresh
selected-candidate mesh measurements and full-clock exported motion audits.

## Warm-start evidence

`hand_control_reuse.py` verifies the completed donor's request, selection,
decoded audit, source inputs, saved methods and both GLB hashes. Control and
replay methods must match the current implementation. The original native key
times must remain present and editable, and the frozen endpoint cannot move.
Embedding inserts zeros without resampling or changing the prior controls.

Before source geometry work, the driver compares the embedded control motion
against independently decoded donor GLBs on the expanded motion clock. It also
checks the expanded support's original motion caps, guide rates and native edit
budget. A donor's reported success alone is insufficient for reuse.

Source queries are verified separately against the same core source bindings;
adding control-donor provenance does not make those new file references part of
the source geometry identity. The expected source population is 86 directional
queries: 50 reusable from the three-key study, plus 36 earlier directions.

The solver's evaluation cache now retains at least one complete finite-difference
batch (`max(32, dimensions + 3)` entries), avoiding eviction within a 66-component
batch. It still caches actual measured depth and physical margins and does not
change tolerances or acceptance. A regression fixture verifies 67 unique
physical evaluations for a baseline plus all 66 perturbations without redundant
baseline evaluation.

## Reproduction and status

Local ignored assets and bound preceding studies are required. Use fresh output:

```powershell
.venv/Scripts/python.exe -u scripts/fit_continuous_terminal_hand.py reports/scene-pair-terminal-hand-search-v1 reports/scene-pair-extended-hand-v1 --hand-orientation --editable-keys 6 --witness-study reports/scene-pair-multikey-hand-v1 --warm-start-study reports/scene-pair-multikey-hand-v1
```

The focused development suite passes 39 tests and the minimal public Python
suite passes 659 tests. Tests cover both actors under oblique placements,
whole-clip preservation when adding earlier keys, exact native-key identity,
changed source/GLB/control evidence, failed decoded audits, changed control
methods, incomplete donor studies and finite-difference cache retention.
The preceding commit `698d661` passed hosted CI.

The real worker's warm-start replay completed with zero error for both actors,
and its expanded-support motion and guide checks passed. It verified/reused all
50 donor source queries and is measuring the additional source directions.

The experiment is running. No clearance improvement, publication or release
approval is claimed. Once terminal, compare selected geometry at matching times
against both the unchanged source and the three-key donor where their measured
clocks overlap. Record local regressions as well as peak depth, and diagnose
actual exported motion failures before deciding the next step. Studio remains
on its previously published evidence; all 14 release capabilities are unapproved.
