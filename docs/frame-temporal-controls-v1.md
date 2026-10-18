# Frame-local derivatives and temporal authoring controls

Development component and diagnostics, 2026-10-18. A single temporal amplitude
forces an entire correction curve to have one shape. `FrameTemporalControls`
maps complete frame-local derivatives into multiple convex temporal knots,
while retaining explicit control blocks, group identities and every column.
Constant groups use their knot mean, so a root declared constant remains
constant. The map owns its weights, rejects incomplete/nonfinite layouts, and
rejects an oversized complete lift before allocating its output. Row chunks
change working storage, not coverage. The lift's complete allocation limit
remains 64 MiB; it never truncates rows or columns.

```python
coordinates = FrameTemporalControls(
    weights, blocks=2, groups=12, constant_groups=(11,)
)
expanded_controls = coordinates.embed(original_controls)
expanded_surface_jacobian = coordinates.lift(surface_jacobian, original_frames)
```

The weights are modulation of the caller's existing edit envelope. They are
not a new sample clock or permission declaration. The caller retains the
original rig, protected keys and physical edit limits. A row must name its
actual original frame. **Do not lift interval or global-peak derivatives as
though they belonged to one frame.** Those derivatives require the full new
track, including every relevant neighboring pose and motion interval.
Floating frame evaluations exceeding a control ball reject; they are not
clipped. The module does not generate motion or establish acceptance.

All **349 focused source cases pass locally**, including the existing 307
and 42 new cases. The new tests compare complete column maps across knot counts
and chunk sizes, check independent nonlinear finite differences, constant-root
behavior, embedding and ownership, and reject missing/invalid/out-of-budget
inputs. Both source workflows include the new suite. Evidence:
`reports/frame-temporal-controls-tests-v2`; the earlier passing v1 remains
preserved before the test gained its own standalone import-path setup.
The first hosted dispatch,
[run 39154259698](https://github.com/DocMorphic/strep/actions/runs/39154259698),
passes 26 existing guidance/skin cases on each OS. It does not cover the new
timing-map suite. The corrected full-group dispatch,
[run 39154504770](https://github.com/DocMorphic/strep/actions/runs/39154504770),
passes **349 cases on each Windows/Ubuntu job** at source commit
`ea2bea4825bef00ebdaa609abd5b453052462fd2`. Both dispatches' logs and receipts
remain retained and their scopes stay separate.

## What the real-clip diagnostics establish

These studies deliberately reuse the previously qualified all-violator model
center, **before the most recent retained/exported step**. They do not pretend
to measure derivatives at the latest exported pose. Existing exports, actual
Godot captures, source files and the qualified reference remain unchanged.

First, the complete 6,984-row/72-column model is tested with all extra search
reserves removed. Original author balls, physical boundaries, currently passing
conditions and mandatory point cuts remain hard. Requiring every scalar
condition, all failing partner conditions, or either failing partner direction
separately returns `PrimalInfeasible`. Repairing the failed normal alone has a
usable local direction. This distinguishes an unresolved local body constraint
problem from a failure caused solely by the caller's extra search targets. The
existing solver still uses its 1e-8 numerical interior reserve. Infeasible
statuses are not independently verified dual certificates or proof about exact
boundary feasibility. No direction from this diagnostic is selected as an
animation.

The three-knot experiment retains the same 11 selected joints per actor,
five-degree rotation caps, two-centimetre constant root offsets, edit envelope
and 61 protected rotation frames. It expands to 216 controls. An anchored
evaluation reproduces the old starting pose arrays exactly. All 16 scalar and
33 vector components are differentiated through the full source clocks again;
all directional checks pass the unchanged 0.001 relative criterion. Values and
vectors agree exactly with the old center. Collapsing the derivatives through
the old-control embedding recovers the old scalar Jacobian within 5.56e-17 and
the vector Jacobian within 1.13e-17. Original native reference values and frozen
motion caps remain bound; they are not recomputed from an edited baseline.

All 480 geometric rows and 6,488 selected point rows are lifted and saved with
the new 16 global rows: the complete model still has 6,984 rows, with every
expanded column present. A **separate hard-feasibility projection** tests the
same hard constraints and affine norm cones. It does not optimize the 6,445
soft-point minimax objective. For a hard-feasible witness, an unbounded soft
epigraph can satisfy every saved soft inequality; its required value remains
reported. This is a feasibility diagnostic, not a solution of the complete
correction objective, a memory-budget bypass for that objective, or a physical
clearance certificate. The all-body hard variants remain locally infeasible
with three knots; the normal-only variant remains feasible.

Finally, each of the 22 failed geometry frames is checked independently, with
global contact/orientation/motion conditions and cross-frame coupling explicitly
absent. The four coarse geometry rows alone are feasible at every frame.
Enforcing every selected point at that frame returns `PrimalInfeasible` at 17
frames: 33, 35-38 and 54-65. Individual-row affine upper bounds over the original
author balls do not prove any single failing row unreachable. The conflicts
appear when conditions are combined. Even the weaker independent-frame local
problem can fail, so additional temporal subdivision alone is insufficient for
those **affine models**. Nonlinear repair or global impossibility is not proved.

Evidence: `reports/physical-target-feasibility-v1`,
`reports/temporal-hard-model-v1`, `reports/temporal-hard-feasibility-v1` and
`reports/frame-local-feasibility-v1`. Tensor jobs retain a 2 GiB tree cap,
numerical jobs 512 MiB, and all retain the 600 MiB free-memory reserve. Original
physical limits and acceptance thresholds stay fixed. No model inference,
training, new animation selection, clean-target or release approval occurs.
The whole-project goal and all broad-action, rig, scene, engine and genuine
human-review requirements remain active.
