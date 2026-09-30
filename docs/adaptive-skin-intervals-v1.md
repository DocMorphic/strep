# Subdividing uncertain skin-motion intervals

`adaptive_surface_intervals.py` connects the native-interpolation movement
bounds to the existing triangle-crossing and full-vertex containment diagnostics.
Each requested interval ends in an explicit partition of terminal intervals:

- `crossing_observed`: an actual decoded pose contains a transverse triangle
  crossing, with a retained triangle pair and timestamp.
- `interior_vertex_observed`: a decoded vertex lies inside the other closed mesh,
  even when their boundaries do not cross.
- `surface_separation_bound`: the swept triangle boxes do not overlap and the
  sampled containment check finds no interior vertex.
- `unresolved`: depth, interval-count or floating time resolution limits prevent
  a conclusion, or touching/coplanar geometry remains ambiguous.

An observed crossing establishes an intersection at its witness time, not at
every time in that terminal interval. A separation bound concerns surfaces;
sampled containment and floating-point bounds do not certify continuous solid
clearance or self-collision. No outcome approves animation quality. Triangle
counts and overlap lengths are not penetration depth or a realism score.

## Procedure and preservation

For each interval, both movement-bound providers must return its exact clock
and exactly the same placed center vertices as independent pose sampling. The
audit checks closed, consistently wound meshes before containment. It uses the
center first; if swept boxes overlap, it also inspects the start and end unless
an intersection is already observed. Without an observed intersection or a
separation bound, it bisects the interval. Cached pose measurements avoid
repeating endpoint queries shared by children.

The depth and node budgets are explicit and bounded. Exhausted branches remain
in the final partition as unresolved; they are never discarded or treated as
clear. Every terminal partition is checked for exact start/end coverage and
adjacent boundaries. The full native key union can be supplied as root intervals
without assuming linear motion of the skinned vertices.

`audit_adaptive_skin.py` accepts the same hashed-clip and constant-placement
protocol as `audit_interval_skin.py`, requiring two actors with one primitive
each. It saves the input hashes, method snapshots, budgets, per-interval tree,
retained observations and final summary. The shared protocol loader was extracted
without changing the earlier audit's observations: all saved interval metrics
and candidate examples reproduce exactly.

The swept-box implementation now uses R-tree counts for all candidates instead
of iterating through every pair in Python. It still checks every source box,
retains the exact total count, and records the first sixteen examples. The
exhaustive-count test and the real three-interval replay both match the prior
implementation exactly, including the interval with 16,401,274 candidates.

## Validation and completed character audit

Twelve additional model-free tests exercise subdivision, a crossing missed at
the root's start/middle/end poses, closed-mesh containment with separated
boundaries, explicit occupancy observations, coplanar touching, depth/node
exhaustion, partition coverage, incorrect placed centers, open meshes and invalid
budgets. The 31 focused interval/bound checks and all 817 minimal public Python
checks pass, including after the R-tree count change.

The first character audit retains all three intervals from the preceding bound
study and adds [1.9, 1.94] seconds, with unchanged candidate GLBs and placements.
It uses depth 4 and at most 31 interval evaluations per root. All four roots
complete without needing subdivision: one has bounded surface separation and
three contain an observed crossing. Subdivision itself is covered by the
analytic moving-box tests; these four real intervals do not establish its
whole-clip behavior.

| Requested interval (s) | Retained witness time (s) | Proper triangle pairs counted | Full-vertex peak depths A / B (mm) |
| --- | ---: | ---: | ---: |
| 0 to 0.008333333 | 0.004166667 | 0 | 0 / 0 |
| 1.9625 to 1.970833333 | 1.966666667 | 60 | 7.540960 / 6.028708 |
| 2.0625 to 2.070833333 | 2.066666667 | 721 | 20.455668 / 20.791931 |
| 1.9 to 1.94 | 1.94 | 8 | 0 / 0 |

The final row is a real character crossing missed by both full-vertex depth
tests at the same pose. It is distinct from merely having depth below the 5 mm
screen. At 1.9 and 1.92 seconds, the queried geometry reports neither crossings
nor vertex penetration. No new quality threshold is inferred from these results.

`verify_adaptive_skin.py` independently decodes the bound meshes, checks complete
root partitions, and calls the separate barycentric linear-feasibility verifier
for each retained first crossing pair. All three witnesses pass. Their smallest
interior barycentric weight is 0.064427 and the largest normalized equality
residual is 1.53e-16. The verifier also reruns full-vertex depth at those same
three poses. It verifies three existence witnesses, not all 789 counted pairs,
and does not prove absence of false negatives or validate the separation bounds.

Completed local evidence:

- Protocol: `reports/adaptive-skin-protocol-v1.json`, SHA-256 `9342deaa2435238365bb660dd807ad3dec43bcf877a078087b68a131ce4d5353`.
- Audit: `reports/adaptive-skin-audit-v1/result.json`, SHA-256 `0fb386e42787bf9b4840d211cfd378e7542d4967eae08970aa8218f4390f5112`.
- Intervals: `1c7ed8ff4723d61e37c83ca40e146a76588889f40007cb43b49020e3c9152838`.
- Independent proof: `reports/adaptive-skin-proof-v1/result.json`, SHA-256 `b2a43c9f6c48d26b6f8aa4ea480102f4828a8c98248069ecfdce8eb37dc65859`.

```powershell
.venv/Scripts/python.exe scripts/audit_adaptive_skin.py reports/adaptive-skin-protocol-v1.json reports/<fresh-audit> --max-depth 4 --max-intervals 31
.venv/Scripts/python.exe scripts/verify_adaptive_skin.py reports/<fresh-audit> reports/adaptive-skin-protocol-v1.json reports/<fresh-proof>
```

## Full native-clock follow-up

A separate immutable protocol includes every adjacent timestamp in the union
of both clips' native channel clocks: 74 intervals over 0 to 3.6666667461395264
seconds. It retains the same clips, placements, tolerances and budgets. This
audit is running under `reports/adaptive-skin-full-audit-v1`; no final full-clock
outcome is claimed yet. Preserve its bound implementation until it exits.

One completed root within that running audit, [1.5404924154, 1.5906041861]
seconds, starts with 22,980,726 overlapping swept-box pairs. Seven interval
evaluations partition it into four terminal intervals with zero swept pairs
and clear sampled containment. This is actual decoded-character subdivision
evidence; it does not imply that the remaining roots pass.

No animation is changed, no model is trained, and no held-out prompt is used.
Reliable contact correction, cubic/STEP-jump handling, moving placements,
self-collision, human review and release approval remain open.
