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

The completed experiment below preserves both failures. Full decoded export checks remain decisive; all fourteen release capabilities remain unapproved.


## Completed result: lower worst residual trades away other failed constraints

Both fits finished and independent verification completed on 2026-09-30. The control reproduces the previous unit-scale NPZ, BVH, GLB and contact/body audits byte-for-byte. All original input, method snapshot, completion-artifact and paired-protocol checks pass. Full decoded GLB audits and native body/support measurements replay successfully, and original root/rotation/held-pose budgets pass for both outputs.

| Measurement | Control | Three restoration attempts |
| --- | ---: | ---: |
| Total fit/correction seconds | 321.32 | 497.80 |
| Maximum pin error, mm | 5.370261 | 5.336574 |
| Pin samples exceeding 5 mm / 61 | 2 | 2 |
| Approach speed excess, m/s | 0.000048219 | 0 |
| Approach acceleration excess, m/s² | 0.000060311 | 0 |
| Hold speed excess, m/s | 0.000035444 | 0 |
| Hold acceleration excess, m/s² | 0.002034130 | 0.132427080 |
| Release speed excess, m/s | 0.000250459 | 0.000518115 |
| Release acceleration excess, m/s² | 0.000254704 | 0.052806606 |
| Contact screen | Fail | Fail |

The three accepted step fractions are 1/32, 1/16 and 1/16. Thirteen larger nonlinear proposals were rejected. The maximum normalized proxy violation falls from 0.074057656 to 0.067894001, and no previously passing vector entry becomes failing. However, the policy permits already-failed entries to worsen: the hold-acceleration residual grows from 0.001266881 to 0.067894001, while release speed and acceleration also deteriorate. The decoded output confirms the tradeoff. A lower minimax score is therefore insufficient evidence of a useful repair. The extra objective evaluation recorded in the recipe refreshes diagnostics; evaluation counts exclude restoration Jacobian and backtracking calls, so elapsed time is the relevant cost comparison.

Global rate excess, added floor depth and all outside-window joint/basis/skin errors remain zero. Both body flag lists are empty and fixed raw/limb support allowances pass. Maximum physical root lifts are 0.747263 and 0.783682 mm; maximum rotation edits are 0.672750 and 0.704179 degrees. Both actual engine runs pass 284 pose observations, authored events at frames 85/100, automatic/reverse playback, callback and unloading checks. Independent verification rechecks these retained captures; it does not add new engine runs. These checks do not establish realism.

Evidence is retained in `reports/contact-constraint-restoration-v1` and `reports/contact-constraint-restoration-verification-v1`. The experiment's method freeze is accounted for. Keep restoration disabled by default. Before another motion experiment, strengthen both linear proposal and nonlinear acceptance to prevent worsening existing constraint violations, and test that policy on this reproduced tradeoff. This is a search safeguard, not an infeasibility proof or assurance of eventual convergence. Broader scene/partner coverage, held-out fixtures and human evidence remain necessary; this landing case is not the release definition.


The [stronger per-entry safeguard](contact-restoration-policy-v2.md#real-motion-evaluation-proposals-rejected-original-output-retained) is now evaluated: it rejects all trial sizes and preserves the original control byte-for-byte. It prevents the demonstrated regression but does not repair this landing.
