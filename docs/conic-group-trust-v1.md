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
cones, ownership and invalid/incomplete inputs. Hosted results and the actual
545-row scene experiment will be recorded separately when complete.

Local evidence: `reports/block-trust-diagnosis-v1` and
`reports/conic-group-trust-tests-v1`. The unchanged release matrix still
requires broad action/rig/object/partner, engine and human-quality validation.
