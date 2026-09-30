# Continuous hand-clearance controls

The terminal grid rejected every edited candidate, but the small-control
diagnosis found an Xminus example that missed the angular-speed cap by only
0.023351 rad/s. This experiment replaces discrete direction/elbow choices with
five continuous controls: one symmetric world-space wrist vector and an elbow
swivel for each actor. It retains the current motion and protected-contact
bounds; it does not establish a more permissive animation-quality policy.

## Search and validation

Only the final editable native key changes. Its neighboring keys retain their
original values. The control domain is the intersection of the existing 60 mm /
30-degree domain and the 0.8 m/s / 300-degree/s guide limits on both neighboring
intervals. The wrist displacement bound uses vector length. Native joint edits
retain the 45-degree budget. The source hand orientation is retained at the
edited key by the existing two-bone reach solver.

`VectorTerminalMotion` wraps the existing quantized batched replay with a
continuously changing wrist direction. Tests compare both actors under an
oblique scene placement against actual independently baked GLBs, including
between-key transforms and the unchanged suffix.

Original-bin joint speed/acceleration and world-angular speed/acceleration are
constrained on the final edge's seven original 120 Hz samples and two frozen
suffix samples. The optimizer uses a 9e-6 numerical margin; independently
decoded exports retain the existing 1e-5 tolerance. The incoming interval is
not constrained in this terminal solve, but full-clock motion is measured after
baking so incoming failures cannot be hidden.

At each of the seven edge times, all 2,933 hand-influenced vertices are queried
against the opposite actor's full mesh. Up to 32 nearest surface witnesses per
direction/time retain original source vertex IDs, target triangles, barycentric
coordinates and outward normals. Both skinned actors move when evaluating a
witness. Normals and triangle correspondence remain fixed during optimization;
this is a local search objective, not a clearance certificate.

SLSQP minimizes the worst witness penetration using an epigraph variable and
six optimization variables (five controls plus that scalar). Four starts use
the source, a -5 mm X offset, a -20 mm Z offset, and a combined -5 mm X/Z offset
with -1-degree swivels. Each start has at most 100 iterations, normalized
finite-difference step 1e-4 and objective tolerance 1e-9. A small control-norm
term breaks near ties.

The independently evaluated witness depth selects among physically feasible
observations. Solver success or an optimistic epigraph value cannot approve a
control. If the returned point misses a hard limit, fixed backoff factors toward
the source are re-evaluated; the limits themselves are unchanged. The source
always remains an eligible incumbent.

Selected controls are baked to actual GLBs. Native clocks, every other native
quaternion and sampled transforms outside the one-key support are checked.
Actual GLB motion is independently checked on the constrained terminal interval,
and full-clock positional/angular failures are recorded separately. Fresh
hand-to-full-mesh queries then audit all seven times in both directions. Full
body geometry over the whole timeline, engine import, human quality and a
compatible earlier approach remain separate requirements.

## Reproduction

The bound prior studies and ignored local character assets are required. Use a
fresh output directory:

```powershell
.venv/Scripts/python.exe -u scripts/fit_continuous_terminal_hand.py reports/scene-pair-terminal-hand-search-v1 reports/scene-pair-continuous-hand-v1
```

See [the terminal grid and rate diagnosis](paired-terminal-hand-search-v1.md).


## Completed result

The study produced 448 source witnesses from 14 directional hand queries. All four SLSQP starts reached the 100-iteration limit (status 9); none reported convergence. There were 5,523 recorded evaluations, including finite-difference probes, with 4,618 passing the terminal motion/domain gates. This is a bounded search result, not an optimum or infeasibility proof.

The retained controls at native time 2.041610718 s are:

| Control | Value |
|---|---:|
| Wrist offset X (mm) | -0.483479199 |
| Wrist offset Y (mm) | 0.371951793 |
| Wrist offset Z (mm) | 0.342672547 |
| Actor A elbow swivel (degrees) | 0.062209442 |
| Actor B elbow swivel (degrees) | -0.059328842 |

Actor B uses the opposite wrist offset. The selected evaluation is 3415. It passes the terminal interval and frozen suffix after actual GLB decoding. Batched-to-export matrix error is exactly zero for both actors; native clocks and every other quaternion key remain exact.

| Hand geometry | Source | Selected |
|---|---:|---:|
| Final-edge peak depth (mm) | 21.333458 | 20.844917 |
| Samples over 5 mm / 7 | 6 | 6 |

Fresh mesh queries confirm a reduction of 0.488542 mm. The fixed-witness objective predicts 20.844950 mm. Agreement here does not certify other candidates or omitted body surfaces.

Full-clock motion still fails:

| Actor | Positional violations | Angular-speed violations | Angular-acceleration violations |
|---|---:|---:|---:|
| A | 17 | 15 | 54 |
| B | 15 | 7 | 47 |

A terminal pass therefore does not yield a usable complete approach. The next experiment should include the incoming interval in the constrained replay and test intermediate hand-orientation freedom, which this wrist-position/elbow parameterization holds fixed at the editable key. Preserve the final protected contact and current motion caps. This is a proposed additional degree of freedom, not evidence that it will solve clearance.

The worker completed, but neither geometry nor complete-motion acceptance passed. No Studio replacement, engine approval, human review, training or new model/data acquisition occurred. All 14 release capabilities remain unapproved.

Validation: 625 public Python tests pass in the minimal environment, including five new continuous-control tests. The focused minimal suite passes 31 tests; 17 directly affected development tests pass. Tests cover actual GLB equivalence under oblique placements, both moving witness surfaces, a feasible continuous improvement, infeasible starting points, and rejection of a solver that falsely reports success with an invalid control and epigraph.

| Artifact | SHA-256 |
|---|---|
| Request | `259874e0b5fd1abc65d7bfbd0980e28e98d02248f596ede02878e097072f20c7` |
| Source witnesses | `06ee13ab17e9037e1bdaa0a78807b260162c78f4c7d7e3754de488f406860dc5` |
| Selected controls | `bedeaae1e92a6ec8a30fb5cd9ee440a00b31e92b6044f11019ab7536ee193bfe` |
| Solver reports | `dcc42dc78308a0a2bb522c302e690d8699a2d2d0b5718d39f7e7677d2422c7eb` |
| Decoded audit | `e03299312a885fb6968914932bed1eda66ddb2aabeebb0750fd18f2448d56d0e` |
| Fresh geometry | `82b17fb77a2f0070026169175efc0362df20a0136883cbcbb24929532bc41aad` |
