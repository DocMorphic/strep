# Full-vector contact bounds in minimax proposals

Development component, 2026-10-18. The preceding sequential high-five trial
retained all three point contacts, then rejected later collision proposals
that lost them. Its scalar distance linearization permits sideways movement
outside a contact sphere even when the predicted distance row passes.

`minimax_step` now accepts optional complete `affine_vectors` (B by 3),
`affine_jacobian` (B by 3 by N), and positive `affine_radii` (B). All three
must be supplied together. Every vector receives a hard second-order cone:

```
norm(vector[b] + jacobian[b] @ delta) <= radius[b]
```

These cones have no peak-violation slack. Every original scalar row,
protected halfspace, original-relative control ball and trust bound remains
present. A fixed impossible cone returns no proposal; it is never silently
dropped. A local solver failure is not a proof of nonlinear infeasibility.
All affine data are owned copies, finite and bounded; shapes, complete
columns, up to 8,192 vectors and the original 64 MiB model budget are checked.

The solver searches inside each radius by a relative 1e-8 reserve. Returned
affine norms must pass the supplied radii exactly, with zero additional
physical tolerance. A test injects an apparent solved point only 1e-13
outside a radius and verifies rejection. The component does not infer units
or contact geometry: the caller must supply a consistent vector model.

Output trust checks now compare against the original caller bounds rather
than the solver's tighter internal search box. This avoids rejecting valid
points for rounding across an internal margin while keeping the original
trust bounds and control-vector balls exact. Nothing is clipped, and no
physical budget or tolerance is widened.

All **174 focused cases pass locally**, including the previous 157 and
17 new contact-cone cases. Tests reproduce scalar sideways drift, verify its
vector-constrained replacement, include both actors and the last contact,
retain fixed cones and original control balls, reject invalid/incomplete
inputs and enforce strict affine acceptance. Two earlier test runs remain
archived: they exposed an internal-box false rejection and an axis-aligned
degenerate scalar fixture. The final fixture tests sideways contact drift
away from that unrelated degenerate optimum.

Local source evidence: `reports/conic-affine-contact-tests-v3`.
All **174 cases also pass on both hosted Windows and Ubuntu**, run
`39131624181`, at `a64047788ddf76228ee95174eaf673a9e5ecfdfa`.

## Same-state paired comparison

One fresh proposal starts at the exact retained state from the preceding
sequential study. The original scalar step at trust 0.25 rejected all three
fractions. The vector comparison keeps the same trust, source clips, scene,
contact intervals, five-degree joint/two-centimetre root permissions, twelve
scalar rows and tighter interior search targets.

The complete scalar Jacobian and baseline are reused only after exact array,
source, evaluator and permission checks. The earlier conic implementation
is checked against its archive and public `d306cc2` source. The nine components
of the three actual generated-partner/world contact vectors are differentiated
afresh. All twelve scalar and nine vector directional checks pass the
predeclared 0.1% test. Reusing the old Jacobian at the same state is not a
second independent generation run.
An ablation with the current solver and the vector cones disabled reproduces
the archived scalar direction exactly, isolating the cone change from the
internal-box output-check fix.

The full step still loses two point contacts in actual nonlinear geometry.
The half step preserves every previously passing condition and lowers the
maximum normalized working violation from 1.387311302 to 1.077693631. Only
that half step is retained. A vector cone for an affine approximation does
not solve nonlinear articulation by itself.

Independent raw/saved replay again checks four exports and 8,666,880 vertex-
times using the original complete motion policies and contact intervals.

| Measurement | Previous retained raw | Vector half step raw | Vector half step saved |
| --- | --- | --- | --- |
| Palm gap, 30 mm development screen | 29.535 mm | 28.912 mm | 28.912 mm |
| Frame-60 deepest partner penetration, 5 mm screen | 11.837 mm | 10.289 mm | 10.288 mm |
| Actor A deepest floor penetration, 5 mm screen | 6.283 mm | 5.870 mm | 5.870 mm |
| Actor B deepest floor penetration, 5 mm screen | 5.757 mm | 5.607 mm | 5.607 mm |

All three paired point contacts pass in raw and saved representations.
Floor and partner depth still fail. Both actors fail source physical
nonregression and now both fail the original native motion ceilings. Thus
local collision improvement has not produced a usable approved animation.
The 30 mm point screen is an existing development diagnostic, not a claim
that a nearly three-centimetre palm gap is visually convincing.

All original buffer bytes, 284 unselected channels and 1,342 protected keys
remain exact. Saved joint edits stay below 3.247596/1.614228 degrees and root
shifts below 5.770716/4.461635 mm. Maximum saved skin component discrepancy
is below 0.000669 mm, within the separate 1e-5 m fidelity check.

Only original frame 60 has complete two-direction partner collision queries;
the other 119 partner frames and continuous/edge-only/self/force/semantic,
engine and human checks remain unverified. No output is adopted or selected.
A first replay launch deferred before starting because the producer still
held its worker lock; after its terminal result was consumed, an identical
fresh replay completed. The completed producer used 1,084,125,184 bytes peak
under its 2 GiB cap; replay used 257,142,784 under 512 MiB. Both retain the
600 MiB available-memory guard.

Evidence: `reports/contact-vector-scene-probe-v1`,
`reports/contact-vector-scene-replay-v2` and
`reports/contact-vector-progress-v1`. Detailed generated files remain local.
The next proposal needs a fresh relinearization at this improved state;
the cached previous Jacobian cannot be reused there. Complete motion and
full-clock partner validation must accompany further correction.

This is exact geometry for an affine approximation. Actual articulated
motion remains nonlinear, and full mesh, original/raw/saved motion,
serialization permissions, engine and human review gates remain mandatory.
The existing failed studies and qualified partial reference stay unchanged.
The entire-project goal remains active.
