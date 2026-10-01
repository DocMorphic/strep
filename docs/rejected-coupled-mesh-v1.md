# Full-interval mesh audit of the rejected coupled candidate

The continued witness solver stalled with three old signed-witness violations,
despite passing the original motion-rate and palm limits. This diagnostic
examines the actual mesh of that rejected final state to determine whether
the fixed witness objective is overlooking other geometric regressions.

## Procedure and scope

The completed continuation, inputs, exact final controls, original reference,
sample clocks and archived methods are verified before replay. The candidate is
exported as `rejected-diagnostic-0.glb` and `rejected-diagnostic-1.glb`; these are
diagnostic artifacts, never selected Studio outputs. Both files are independently
decoded. Their native clocks, unselected channels, outside-window motion and
agreement with the candidate's predicted serialized poses are checked.

Decoded original export motion caps and stricter proposal motion/palm limits
are reported separately from the old witness failures. These fields can report
failure without suppressing the geometry investigation. Diagnostic completion
does not mean that the animation passes acceptance.

The mesh audit uses all 53 previously declared edit-interval samples, including
native key partitions, their midpoints and historical observations. At every
time, it examines the complete triangle candidate population and both full
vertex-depth directions for the donor and rejected candidate. Full observations
are saved per time before comparison. The existing fixed-baseline mesh policy
checks new proper/uncertain triangle pairs, degenerate faces and increases in
directional maximum depth. Neither a passing comparison nor a smaller aggregate
count certifies collision-free or realistic motion.

The study leaves `accepted_for_publication`, `quality_approved`,
`collision_free_certified` and `selected_for_studio` false regardless of the
geometry outcome. The full interval is sampled, not continuously certified.

## Reproduction

```powershell
.venv/Scripts/python.exe scripts/study_coupled_window_repair.py reports/window-triangle-controls-v1 reports/triangle-hand-repair-v1 reports/<fresh-output> --geometry-study reports/coupled-witness-continued-v1
```

This requires the bound local assets and earlier studies; all generated
diagnostic artifacts remain excluded from Git. Three additional model-free
tests check complete populations, ordered clocks, saved observations, and the
fact that even a passing mesh diagnostic cannot approve or promote a clip.


## Completed result

The independently decoded candidate preserves the original export motion caps,
stricter proposal motion/palm bounds, native clocks, unselected channels and
outside-window motion. The same three old witness constraints remain violated.

The full geometry comparison fails **12 of 53 samples**. It introduces **272
new proper triangle pair-time crossings**, with no new uncertain pairs. Seven
of the 106 directional maximum-depth observations increase beyond the unchanged
1e-8 m comparison tolerance. The largest increase is **0.258332 mm**, from actor
A into B at 1.715883613 seconds. Aggregate proper pair-time crossings decrease
from 4,780 to 4,757; the count decrease does not cancel new crossings or deeper
penetration. These totals use the same 53-time clock on both sides and must not
be compared directly with earlier 14-time totals.

This reveals geometric regressions much larger than the remaining subnanometre
old-witness excess. Further repair needs fresh geometry constraints or a revised
approach trajectory; repeatedly refining only the three old witness rows is not
a sufficient next experiment. Keep all original motion, palm and mesh limits.
No animation was promoted, and no release capability was approved.

All 2,613 bound inputs, 66 archived/current methods and 113 output files were
rehashed after completion. The existing 962-test minimal suite and three new
diagnostic tests passed, covering 965 distinct tests. Local study
`reports/coupled-rejected-mesh-v1` binds:

- Result: `ca0f6dc35db5100cf16f80f184b1f55f7a9ebbc6ecae17103c54eea6a9a57cf9`.
- Request: `c3ce1364157934c85817917b41e3848444b2b940f9e2f9be9fa399f9047271a4`.
- Mesh comparison: `0079cfda8e7f84cb1a3c023b459262cae00a8900cda99e9eb3b5824848befae1`.
- Decoded diagnostic: `f48b7ad01574084e5136bbdcc178a27fa7215098de18b901f2972b72c3d18e0b`.
