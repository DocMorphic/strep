# Separate joint and root search steps

Development component, 2026-10-18. Uniformly shortening a proposed pose edit
also shortens its floor-repair translation. In the previous rejected pair,
the linear floor model at protected joint frames requires at least 0.85851
of that direction to clear all those floor failures. The half and quarter
steps therefore cannot repair them. This is a diagnosis of that direction,
not a physical impossibility claim.

`group_trust_step` gives each original three-component control group its own
Euclidean search-step radius. A caller can constrain local joint changes while
allowing the root translation needed for floor repair. Radius zero freezes a
group. Radii are proposal settings, separate from original author permissions.

The implementation substitutes `delta[g] = radius[g] * eta[g]` into every
supplied scalar row and physical affine vector. The existing solver bounds
each `eta` vector by one. Crucially, **all original author control balls**
`norm(original_controls[g] + delta[g]) <= 1` are added as hard affine cones.
The original controls are not reset or rebased. A larger search radius never
allows a larger final authored edit. Every supplied physical cone and hard
row remains present, including rows with zero controllable derivatives.

The helper bounds complete allocations, validates all control columns and
group radii, and strictly rechecks the original author balls and actual group
step norms on the returned proposal. The movement penalty applies to the
normalized search variables. Existing solver defaults and implementation are
unchanged. The caller must still evaluate complete nonlinear motion and saved
assets; no physical tolerance or animation approval comes from this helper.

All **221 focused source cases pass locally**, including the previous 202 and
19 new cases covering independent joint/root steps, nonzero original controls,
exact vector norms, frozen groups, mandatory infeasibility, retained physical
cones, ownership and invalid/incomplete inputs. The same **221 cases pass on
Windows and Ubuntu** at `3714af945cd0530165676f7bb0f1985a1ec8774a`
([hosted run](https://github.com/DocMorphic/strep/actions/runs/39141089657)).

## Actual paired-character proposal

The existing 545-row model retains all 496 original conditions and 49 positive
surface-point cuts, with 504 hard model rows. Its original 24 author balls and
11 physical vector cones remain. The new substitution adds 24 original-author
cones alongside its normalized search-step balls. The original five-degree
joint and two-centimetre root limits remain fixed. A root search radius of two
allows a change from an already edited pose; every final root vector still
has to satisfy its original unit ball. It does not grant a four-centimetre
translation from the original motion.

With root step radius two, joint radii 0.125 and 0.25 are locally infeasible;
0.5 supplies a strictly checked proposal. The study evaluates that full
proposal once. It does not repeat uniform half/quarter backtracking that would
shorten required floor repairs. All original required/protected global checks
pass, including the complete native motion tracks. Geometry checks frames
0..54 before rejecting B-to-A penetration at frame 54. The remaining 65 frames
are explicitly unchecked. The original 496-row nonlinear retention guard and
search-progress target are unchanged; no accepted state is advanced.

All sixteen global rows are evaluated, but actor A's already-failing palm
normal remains negative (normalized margin -1.447532416). It is outside the
original required/protected subset; passing that subset is not a claim that
every physical global condition passes. A separate complete-row audit catches
and corrects an overly broad progress-audit label. The original evidence is
preserved and that label is explicitly superseded by the scope-correction
receipt; no physical failure is converted into a pass.

Full original-surface replay identifies one failing vertex, 2982. It was
already inside the warm surface and already part of the bundle:

| Measurement | Penetration |
| --- | --- |
| Warm point | 4.930954 mm |
| Linear point prediction | 4.736748 mm |
| Actual proposed point | 5.005844 mm |

The 0.269096 mm model error exceeds the 0.1 mm proposal interior. The actual
point still fails the unchanged 5 mm boundary by 0.005844 mm. This is nonlinear
prediction error, not a missing point in the bundle or a rounding allowance.
No derivative is recomputed for this diagnostic; the previously qualified
original-state point derivative supplies the prediction.

A fresh experiment increases only the 49 point **search interiors** to 0.5 mm,
leaving physical criteria, all other rows and source-relative permissions
unchanged. Joint step radii 0.125, 0.25, 0.5, 0.75, 1 and 2 all report local
infeasibility. This includes the original control domain subject to the
solver's existing interior reserves. It does not prove physical impossibility.
No nonlinear candidate is tested from that infeasible model.

The next model must refresh geometry and global motion derivatives at an
explicitly unadopted exploratory pose. Such internal exploration must retain
the original source-relative edit limits and the fixed final required and
protected masks. A rejected exploratory pose cannot advance the accepted
guard, change the reference or select a Studio clip.

## Evidence and remaining work

Local evidence: `reports/block-trust-diagnosis-v1`,
`reports/conic-group-trust-tests-v1`, `reports/full-clock-group-trust-solve-v1`,
`reports/full-clock-group-trust-validation-v1`,
`reports/full-clock-group-trust-counterexample-v1`,
`reports/full-clock-group-trust-solve-v2`, `reports/group-trust-progress-v1`,
`reports/group-trust-global-invariants-v1` and
`reports/group-trust-scope-correction-v1`. The final audit replays
resources, source bindings, transformed model bounds, observed floor rows,
the exact point failure, hosted logs and the unchanged accepted control state.
Tensor jobs retain a 2 GiB cap and numeric jobs 512 MiB, with the unchanged
600 MiB available-memory reserve, 15-second stable admission and 300-second
execution limit. Previous results remain immutable.

No animation is accepted, exported or selected by these studies. The model
weights, data and training remain unchanged. The release matrix still requires
broad action/rig/object/partner, independent raw/native/saved and continuous
collision, engine and human-quality validation. The entire-project goal
remains active.
