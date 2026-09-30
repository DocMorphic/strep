# Directional forearm approach comparison

Six alternative displacement objectives did not produce a replacement for the
published correction. Four proposals passed affine hard checks, but only one of
their eight full/half-step exports passed preliminary decoded checks. That one
moved inward and increased retained-witness overlap. A fresh mesh measurement of
the rejected sideways half-step showed only a small depth improvement.

## Protocol

Use the completed `scene-pair-relinearized-v2` matrix and its bound cumulative
starting controls. This is the earlier accepted refined correction, whose decoded
peak is 22.522270 mm, **not** the later published 22.426395 mm correction. The
saved continuous-pose peak is 22.522268 mm. Reusing the matrix gives every direction
the same base, witness population, motion rows and empirical proposal reserves.

At its deepest refreshed witness (actor A vertex 6703, actor B triangle 8334,
sample 34, 1.675 s), construct a deterministic orthonormal frame from the surface
normal. Maximize relative source-to-barycentric-target displacement in both signs
of its normal and two tangents. This changes the objective from minimizing peak
depth to exploring different directions; it does not assume displacement equals
clearance or natural motion.

All six solves retain 8,557 surface rows and 35,778 norm rows, including original
and refreshed witness constraints. Incremental trust is five degrees; original
five-degree cumulative native edit budgets still apply. Original positional and
angular motion bins, protected contact keys, per-time depth caps and surface
distance bounds remain unchanged. Scale is 0.025 and quadratic regularizer is
5e-6. These are diagnostic settings, not a matched objective-only comparison with
the prior half-degree minimax run.

The new solver lives separately from the historical minimax implementation so
existing evidence and its bound solver hashes stay valid. `Solved` and
`AlmostSolved` are not sufficient: independent affine residual checks retain the
existing tolerances. Only passing steps are exported, at fractions 1 and 0.5.
Every attempted GLB and rejected review is retained locally. Other fractions and
other directions have not been evaluated by this study.

## Results

| Direction | Affine directional gain (mm) | Affine hard checks | Full export | Half export |
|---|---:|---|---|---|
| normal plus | 0.400457 | Pass | Reject | Reject |
| normal minus | 0.046528 | Pass | Reject | Preliminary pass, worse witness depth |
| tangent plus | 2.091130 | One norm failure | Not exported | Not exported |
| tangent minus | 2.826727 | Pass | Reject | Reject |
| bitangent plus | 2.217928 | Pass | Reject | Reject |
| bitangent minus | 2.542253 | One norm failure | Not exported | Not exported |

The only preliminary pass has retained-witness depth 22.545421 mm. The normal-plus
half-step fails one angular observation and surface bounds. Tangent-minus and
bitangent-plus half-steps each fail five positional observations and surface
bounds; their angular checks pass. Neither passing affine constraints nor a
smaller retained-witness peak suffices for acceptance.

The tangent-minus half-step received a separate diagnostic audit:

- Both exported clips reconstruct exactly. Independent all-joint positional and
  scalar angular replay reproduce the reported failures and classification.
- Decoded directional displacement is 1.416330 mm. Original plane and distance
  excesses reach 0.015676 and 0.027543 mm respectively; refreshed bounds also fail.
- Fresh full-mesh queries in both directions at **only 1.675 s** measure
  22.454101 mm depth, versus 22.522268 mm in the continuous starting pose and
  22.568796 mm in the raw source. The approximately 0.068168 mm improvement over
  the continuous base is small relative to the displacement and the 5 mm target.
- Its depth at this one time already exceeds the latest published correction's
  complete local-clock peak of 22.426395 mm. It is not a replacement candidate.

No new full-timeline geometry audit, engine acceptance, Studio publication, human
approval or release approval follows. This experiment does not prove all possible
arm paths infeasible. It shows that these six local objectives, tested at these
two fractions under the existing envelope, did not solve the overlap. Next
investigate an approach planned around the partner geometry rather than spending
a full mesh audit on these rejected candidates. Keep the current comparison and
all original limits/evidence intact when defining a separately authored attempt.

## Reproduction and evidence

These commands require the ignored local model/asset/evidence inputs; the public
source repository does not bundle them. Output directories must be fresh.

```powershell
.venv/Scripts/python.exe -u scripts/study_pair_directions.py reports/scene-pair-relinearized-v2 reports/scene-pair-directional-v1
.venv/Scripts/python.exe -u scripts/audit_pair_direction_peak.py reports/scene-pair-directional-v1 reports/scene-pair-directional-peak-v1 --direction tangentminus --trial 1
.venv/Scripts/python.exe -m pytest -q tests/test_directional_pair_proposal.py tests/test_pair_direction_peak.py tests/test_coupled_pair_constraints.py tests/test_scene_pair_relinearization.py
```

The development and minimal runtimes each pass 44 focused tests. They cover
direction construction, actual small pinned conic problems, zero-radius equality
constraints, solver-status rejection, immutable input/clip bindings, cumulative
control reconstruction and retained failed trials. The pinned-solver integration
is optional in fresh hosted CI without the local bootstrap; other checks run
without model weights.

Both real workers completed successfully and are terminal. The directional study
binds 60 local artifacts. The peak audit binds its request, independent replay and
two directional full-mesh queries:

| Artifact | SHA-256 |
|---|---|
| Peak audit request | `995c9d69b512c267952e1144d8f25cda5d6443872333b7f440cb5c03abbcbb3b` |
| Independent replay | `b1f9e76fc2d63e6e6ed8b6913505afbd11e3f8656893ca25fa0b43385d9ebdad` |
| Single-time geometry | `afc28cfde52986fea5052989b5b28119b36a041b9b32f30ac2ae1f41fe9ae5af` |

All 14 project release capabilities remain unapproved. This is development
evidence for one interaction and cannot establish general action coverage.
