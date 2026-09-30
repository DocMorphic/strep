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
50 donor source queries, completed the 36 additional directions, and entered
the optimization phase.

The optimization, fresh 43-time geometry audit and bound return diagnosis are
complete. The selected correction is unchanged from the three-key donor.
Studio retains its previously published evidence; all 14 release capabilities
remain unapproved. See the completed audit below.

## Comparison with the previous correction

The return diagnostic now also writes `warm-start-comparison.json` when a warm
start is declared. `hand_geometry_comparison.py` requires the exact donor
request/result already bound by the current study, verifies the donor geometry
hash and complete clock, and compares equal sample IDs, timestamps and vertex
populations. The 25 donor times must all remain present; the 18 additional
candidate times are explicitly outside this comparison and still belong to
the complete source-versus-candidate audit.

Both ordered directional depths are compared separately, alongside each time's
pair maximum. Thus a lower pair peak cannot conceal increased penetration for
the other actor. The report includes new failing times, maximum per-time and
per-direction increases, and the count of directional observations worsened
by more than 1e-8 m. A real donor self-comparison reproduced its 20.932848 mm
peak and 15 failing times with exactly zero directional changes.

Focused comparison/return-evidence checks pass 29 tests, including rejection of
duplicate/missing times, shifted timestamps, changed hand/full vertex counts,
nonfinite or negative depths, modified/unbound donor geometry and incomplete
studies. No new optimization or mesh outcome is inferred from these checks.

At that implementation stage, the minimal public Python suite passed 673 tests. Commit `531c60e` passed hosted CI. The worker completed with its imported method snapshots unchanged.

## Completed optimization and mesh audit

Both starts reached their 100-iteration limit (status 9). The solver recorded
14,423 evaluations, including finite differences, with 69 motion/domain-feasible
observations. It selected evaluation 7,204: the embedded three-key warm start,
whose measured witness peak remains 20.927519 mm. The first return has a minimum
normalized margin of -0.070409 and no passing tested backoff. The second return
has a -0.009725 minimum margin; its 1% backoff passes but is worse than the warm
start. Neither return is a new accepted correction.

The selected A/B exports exactly match the prior candidate file hashes:

- A: `8df9ecace1cec2b7c2cd3be67a8820e4f60e323ced323d6b7284843287edd64f`
- B: `13adf945e5fe0537898c394106cabf94be21cfd0e0c409e61247c67ad9db2b5b`

The complete 148-pose decoded motion audit has zero positional, angular-speed
or angular-acceleration violations for either actor, and zero batched replay
error. Those passes retain the prior correction; they do not demonstrate that
the six-key search improved it. The fresh 43-time hand audit and bound return
diagnosis both completed before any of their imported source files were changed.

The [updated interaction-model survey](interaction-research-v4.md) records why
the inspected alternatives do not establish a qualified replacement model.

The full hand audit has 17 failing times (42, 43 and 69 through 83) at the 5 mm
threshold, with a 20.932848 mm peak. Against the unchanged source on the same
43-time clock, the peak improves by 0.500532 mm but the failing population stays
the same; the largest per-time regression is 0.938765 mm. Those changes were
already present in the warm start. Against the three-key donor, all 50 ordered
directional observations at its 25 shared times are exactly unchanged. The 18
earlier times are explicitly outside that donor comparison, not omitted from
the complete audit. Two of them fail at 8.718181 and 6.748842 mm.

The diagnostic independently exports both optimizer returns. Return 0 has three
positional-acceleration violations, including actor A's forearm at 7.350083
versus 6.866606 m/s2. Return 1 has two positional-acceleration and three angular-
acceleration violations, including actor A's index end at 86.811775 versus
85.975655 rad/s2. The selected donor has zero violations. Failed returns are
retained as evidence, not accepted by relaxing limits.

The result does not prove the six-key domain infeasible. It shows no improvement
in this bounded search. The next controlled comparison removes the symmetric
wrist-offset restriction while retaining the same clock, individual actor caps,
protected final pose, original source and verified warm start.

Local immutable evidence:

- Study request: `21942438b678f2da0ea33aa518c3a543b1231acdcf71aec4db25a039c3d2f425`
- Fresh geometry: `ac74dcf62f95db98e4687fa5fbb4a8506c3dc2a33ded50b4d62155e133d15062`
- Diagnosis request: `2768ef7a7f5c5ad3416b2fd6fe60bdfb0f8b487589f1d6316fb61c8e5280f7d1`
- Return audits: `f5d24e8f2d212ef1d0919dd3789d9472690d11577168ea31876e70ef8b14832c`
- Donor comparison: `b4511abc9c0ed6ca98bb1a9323738fbe8b1b07bc65fb72354cc70db30d74e1ce`

The original diagnosis used source commit `9871092` and the completed local
study snapshots. A reproduction must use matching methods; changing control
interpretation must not silently reinterpret that recorded evidence.
