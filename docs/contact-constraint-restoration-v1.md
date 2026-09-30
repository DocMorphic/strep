# Experimental pose-capable contact restoration

The [landing scale comparison](landing-root-scale-v1.md) leaves the original 5 mm pin and several phase-rate limits failing. Root-height-only edits cannot remove the retained horizontal pin error, and changing root coordinates alone does not resolve it. This experiment adds a different step after the existing fit: minimize the largest normalized constraint violation through coupled spline-rotation and physical root changes.

## Method and limits

The optional `constraint_restore_steps` argument defaults to zero. Studio behavior remains unchanged. The experimental path requires stationary body contacts, physical root boxes, all existing export guards and fixed native support references. Scene/object, partner, finger, regional and shared-pose fitting contexts are rejected rather than silently omitting their constraints.

Each iteration differentiates a constraint vector with respect to the existing localized rotation controls and root heights. Pins retain each quarter-frame sample. Each phase speed/acceleration, global speed/acceleration, full-skin floor, native reference displacement/added speed and fixed-patch support metric contributes its maximum violation. Maxima retain the underlying feasibility condition, but are nonsmooth and may obstruct search. All references, ceilings, 5 mm pin tolerance, 22 cm root and 40 degree rotation limits remain unchanged.

A linear program minimizes a common nonnegative violation for currently failed entries. Currently passing entries have no elastic slack. A second program minimizes the scaled step size at the first program's result. Rotation controls have a 0.01 dimensionless trust radius; physical roots have a 0.5 mm radius. These are proposal bounds, not larger original edit budgets. Up to ten halved proposals are checked against the complete nonlinear vector. A step must strictly decrease its largest violation (or reach zero) and introduce no newly failing vector entry. No nonlinear acceptance tolerance is added. Within an already-failed maximum group, individual sample regressions remain possible; final acceptance still checks every exported sample.

Rejected probes and exceptions restore the last accepted parameters. Held keys and original rotation/root parameterization remain active. After restoration the existing full export, body review and engine checks run normally. The differentiable proxy excludes channel quantization, so proxy feasibility cannot approve an exported clip. Search failure is not an infeasibility certificate. No anatomical, balance, force or perceptual-quality guarantee is added.

## Validation and planned comparison

Eighty-seven focused tests pass across bounded optimization, restoration, held/local poses, point positions/rates and native body/support objectives. Restoration tests cover a known coupled pose/root solution, constant conflicts, nonlinear backtracking, rejection of new violations, restoration after exceptions, invalid boxes and unsupported fitter contexts. Constraints that already pass still require valid physical bounds.

The matched landing experiment uses the original source, warm seed, request, four fitting stages and 60 iterations per stage in both arms. Fixed-patch support stays enabled, the optional body fitting penalty stays disabled, and the restoration step independently checks the original raw/limb body limits. The only intervention is zero versus three restoration attempts after the fit. Before the experimental arm runs, the control must reproduce the previous default-scale NPZ, BVH, GLB and contact/body audits byte-for-byte. Every input, method and output is retained under ignored `reports/contact-constraint-restoration-v1` with hashes. Methods stay frozen until workers finish and their evidence is accounted for.

No real-motion improvement is established at this publication. Full decoded export checks, original physical budgets and engine evidence determine the result. Both failures and successes will be retained; all fourteen release capabilities remain unapproved.
