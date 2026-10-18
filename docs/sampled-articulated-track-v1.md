# Original-frame articulated evaluation

Development component, 2026-10-18. Building competing vertex constraints needs
many derivatives at a few original frames. Exponentiating all source frames
for every such derivative creates unnecessary work.

`SampledArticulatedTrack` extends the existing `ArticulatedTrack` with
`at_frames(controls, frame_indices)`. It returns local joint rotations and root
positions in the requested original-frame order. Source arrays, temporal
bases, selected joints, independent root permissions and edit budgets retain
the existing constructor and ownership rules. No action name is inspected.

The method checks control vectors over the **whole original clock** before
evaluating rotations only for the requested frames. An edit exceeding its
budget at an unrequested frame therefore still rejects. Original unselected
joints and protected rotations remain exact; selection does not reinterpret
indices as a new clock or resample the motion. Invalid, duplicated or out-of-
range frame IDs reject. The inherited full-clock path is unchanged.

All **202 focused source cases pass locally**, including the prior 181 and
21 new cases. Tests compare ordered and single-frame values with complete
evaluation, all original control Jacobian columns, separate root permissions,
protected/unselected values, violations outside the requested subset, invalid
selections and source ownership. Numerical pose/Jacobian comparisons are
technical checks; they do not add a physical acceptance tolerance.

The same **202 cases pass on hosted Windows and Ubuntu** at
`6a91e243fd2ad716ebbe8e7f5ed5b5fb43834f90`
([focused run](https://github.com/DocMorphic/strep/actions/runs/39139808709)).
In the real paired-character diagnostic, sampled world poses and complete
depth arrays match the full-clock reference exactly at four original frames.
All 49 retained positive-vertex directional derivative checks pass the
predeclared 0.1% technical threshold; complete depth pass masks also match.
All original surface vertices and triangles remain in those queries.

Source evidence: `reports/sampled-articulated-track-tests-v1` and
`reports/full-clock-positive-bundle-v1`. See the
[competing-vertex experiment](competing-vertex-bundle-v1.md) for the resulting
solver and nonlinear failures.
Sampling only reduces local derivative work. All original mesh vertices,
frames, motion limits, exported-file checks and remaining release obligations
still have to be evaluated before accepting an animation.
