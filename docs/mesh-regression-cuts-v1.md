# Repairing newly observed mesh crossings

The full 53-time audit of the continued coupled candidate failed at 12 times,
with 272 new proper triangle pair-time crossings and seven increases in maximum
vertex depth. Optimizing only the historical signed witnesses did not address
these changes. This experiment adds constraints for every newly observed proper
pair, while retaining the original motion, palm, edit and witness limits.

## Frozen donor constraints

The source diagnostic, completed continuation, donor assets, clocks, controls,
archived methods and rejected exported GLBs are hash-bound and replayed before
solving. The new constraints use the same 368 arm/finger controls and exact final
rejected seed; they do not restart from a more favourable earlier candidate.

Each new pair gets a fixed projection axis chosen from its original donor
triangles. All nine vertex-pair projections must exceed a fixed floor of
`min(0, donor minimum gap) - 1e-8 m`. Initially unresolved projections would be
reported explicitly. In this case all 272 donor pairs have positive projection
gaps. There are 2,448 new scalar rows, covering the full new-crossing population
from 1.615660071 to 2.066666667 seconds, without worst-pair sampling or a count cap.
Axes and floors remain frozen throughout the solve.

These are local proposal constraints, not a complete collision model. They do
not encode every possible new crossing or vertex-depth maximum, and passing
them cannot bypass the unchanged 53-time full-mesh guard. The 1e-8 m floor reserve
does not relax any existing motion or geometric acceptance threshold. Fixed-axis
projection residuals are not measurements of penetration depth.

The initial run permits three relinearizations with a normalized trust radius
of 0.001 per proposal. The witness restoration proposal permits elastic slack only on the original
signed witnesses and the new pair rows; all already-passing motion, palm and
edit groups remain hard. Actual internal steps must preserve those hard groups,
improve the worst normalized margin, and keep the original objective below its
donor ceiling. Numerical feasibility is necessary before mesh validation, never
an animation-quality approval. Rejected states are recorded separately from
selected output clips.

## Reproduction

```powershell
.venv/Scripts/python.exe scripts/study_coupled_window_repair.py reports/window-triangle-controls-v1 reports/triangle-hand-repair-v1 reports/<fresh-output> --mesh-repair-study reports/coupled-rejected-mesh-v1 --iterations 3
```

This requires the bound local studies and assets, excluded from Git. Five new
model-free tests verify complete pair-time retention, frozen donor floors,
existing-pair exclusion, exact sample clocks, topology agreement and rejection
of an empty repair population. Fresh geometry and independent exported-clip
checks remain necessary for any changed selected output.


## Completed restoration

The first proposal takes an admissible internal step: the worst normalized margin
improves from -0.020993921 to -0.009095176, a 56.68% reduction in the worst
constraint violation. Its fixed-axis objective increases from 3.224708 mm to
3.388868 mm, still below the donor ceiling of 3.580942 mm. This is a tradeoff
between proposal metrics, not a measured animation-quality improvement.

At that internal state, all original motion-rate, palm, arm and 3,610 finger
edit/adjacent-correction rows pass. However, 273 of the 962 old signed witnesses
and 391 of the 2,448 new projection rows fail. The second linearization reports
`AlmostSolved`, but every one of its eight backoffs violates a hard motion row.
The run stops after two linearizations; no remaining budget is spent repeating
that proposal. Selected GLBs remain byte-identical to the donors. No new mesh
audit or Studio promotion occurs.

All 2,793 bound inputs, 67 archived/current methods and 12 output files were
rehashed after completion. The complete minimal suite passes all 970 tests.
Study `reports/coupled-mesh-cuts-v1` binds:

- Result: `4bf98b01ed7936400020c2bc4bc50d31166e525b40992edb2f7119a249239dcf`.
- Request: `741c7e3157ffe6d53051cec68e0512337c7214a0f539f2521122bcb910d80bec`.
- Iteration summary: `225b46cd7d4dafe340f651b666bb9071737a15682c8906515f6a1c7f97a0e3bb`.
- Final constraints: `30a6824d9f3c2f8fb75e87f741044a4edebc954948097e5d05aada4d0ca1e541`.
- Frozen mesh cuts: `7debb53703d1f9b4d2d9b925cf2474c698d983199d16744ce3a37ff35d3755fd`.

The next bounded check replays the saved second direction at all 256 fractions
`i/256`, using exact serialized controls and unchanged hard bounds. It verifies
the source state, original caps/clocks, archived methods and frozen donor cuts.
It cannot turn an infeasible ray sample into a selected output.

```powershell
.venv/Scripts/python.exe scripts/study_coupled_window_repair.py reports/window-triangle-controls-v1 reports/triangle-hand-repair-v1 reports/<fresh-ray-output> --mesh-ray-study reports/coupled-mesh-cuts-v1
```


## Completed exact replay

All 256 fractions fail at least one hard motion constraint; none advances the
internal state. Even the best hard minimum margin is negative
(-6.116580e-9 normalized). The eight fractions shared with the original backoff
reproduce its objective and constraint metrics within 1e-12, with identical
eligibility and failed-witness counts. This is evidence against further blind
refinement of the same direction, not proof that the overall repair is infeasible.

The final internal state still has 273 old witness and 391 new projection-row
failures. Both selected outputs remain unchanged donors. No fresh mesh-audit
pass, Studio promotion, held-out evaluation, training or release approval is
claimed. Next compare the unrounded and serialized motion margins for the
stalled direction to diagnose the proposal mismatch; test additional proposal
headroom only if that evidence supports it, without relaxing actual acceptance.

All 2,873 bound inputs, 67 archived/current methods and nine output files were
rehashed. Study `reports/coupled-mesh-ray-v1` binds:

- Result: `2bd807b9b29ebdd481455c1df21d1bd2044c7060641e6adf2c1445e26ddadac6`.
- Request: `348b5799b80bfb6f3ca0f742dce636cf64a684306f0130e1ea180e51dd7a3b56`.
- Iteration summary: `9352d108621be0d4f1458d9602a2bca2a82c28a8512de31b33f1d1ef5418b8e1`.
- Final constraints: `30a6824d9f3c2f8fb75e87f741044a4edebc954948097e5d05aada4d0ca1e541`.
