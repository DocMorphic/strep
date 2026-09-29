# Regional constraint updates and bounded restarts

Scene fitting now supports optional regional inequality multipliers and initialization from an earlier candidate. The fixed regional penalty remains the default. The comparison below does not support replacing that default: staged regional multipliers worsen clearance on this development case.

## Implementation

`--region-constraint-mode augmented` gives each normalized regional residual its own multiplier. It requires the existing balanced family reduction. Zero multipliers and an initial penalty of 200 reproduce the original balanced objective mathematically, including its first-stage gradient. Multipliers remain fixed during each L-BFGS subproblem and update only after reevaluating the accepted parameters. The penalty grows by four between stages. Authored limits and frozen witness vertices remain unchanged. Floating-point arithmetic can still produce different optimization trajectories.

`--initialization path/to/candidate.npz` recovers correction spline controls relative to the **original source clip**. It inverts the bounded rotation map, handles physical finger parameters, and rejects seeds beyond the original budgets or outside the original spline representation. Initialization does not multiply a new budget onto the candidate. The CLI also checks source-relative bounds, unchanged root X/Z and foot-contact labels, and reconstruction with original bone offsets before fitting. The seed is hashed as an input; the source, constraint targets and independent audit remain tied to the original clip.

For the retained seed, the maximum recovered rotation-vector discrepancy is 3.067e-8 radians. Both restarted candidates independently pass their original source-relative edit budgets. This is a supported initialization path for compatible solver candidates, not unrestricted import of an arbitrary rig or animation.

## Matched development comparisons

All runs use the same five-frame box repair fixture, full skin coverage, separate per-vertex object inequalities, balanced regional loss, six stages of 100 iterations, and a 600-second limit. The two original-pose runs share source inputs. The two restarts share the same candidate seed and original source. Restart times below exclude the seed's 83.547-second generation cost, so they are not equal-total-compute comparisons with the original-pose runs.

| Initialization / region treatment | Fit time | Minimum object clearance | Maximum hand normal error | Maximum anchor error | Peak joint acceleration |
| --- | ---: | ---: | ---: | ---: | ---: |
| Original / fixed penalty | 83.547 s | +1.601 mm | 10.958° | 4.531 mm | 6.473133 m/s² |
| Original / augmented | 85.031 s | -3.575 mm | 10.476° | 5.010 mm | 6.295783 m/s² |
| Same candidate seed / fixed penalty | 84.250 s | +1.722 mm | 9.670° | 4.424 mm | 6.443118 m/s² |
| Same candidate seed / augmented | 83.891 s | +1.124 mm | 9.924° | 4.999 mm | 6.407093 m/s² |

Every variant fails all 34 independent exported contact samples and all 17 geometry samples. Both restarts meet the sampled 10-degree normal and 5 mm anchor limits, but still miss the 2 mm clearance and complete distributed-contact conditions. Source peak acceleration is 6.180514 m/s²; all candidates exceed it. Peak joint speed stays 0.363166 m/s. Neither passing bounds nor improved orientation approves the interaction.

The restarted augmented variant's native residuals isolate the remaining contact terms: patch-clearance deficits reach 0.587 mm and selected-witness upper-gap excess reaches 0.072 mm. The other normalized regional families pass at native keys. These measurements do not establish why the optimizer stalls, whether another witness is feasible, or whether all constraints can be jointly satisfied.

## Validation

Fifty-five focused tests pass, including regional loss/gradient equivalence, finite-difference checks, accepted-point multiplier updates, invalid layout/stage rejection, inversion of body/finger controls, original-budget preservation, and rejection of unrepresentable seeds. Existing scene jobs include the initialization implementation in their revision and snapshot dependencies; their defaults are unchanged.

Independent GLB audits check full skin and contact requirements at integer and quarter frames, plus source-relative hard budgets and native FK consistency. Actual Godot imports match 30 new actor-frames across six GLBs and 77 bones, with maximum position error below 0.230 micrometres; ten baseline frames reuse earlier engine evidence. No browser, animator, semantic or release approval is implied.

In a provisioned workspace, using fresh output paths:

```powershell
.venv\Scripts\python.exe scripts/fit_scene_regions.py path/to/original-scene.json --actor A --contact left-grip --contact right-grip --output reports/new-restart --region-loss balanced --stages 6 --iterations 100 --seconds 600 --full-object-skin --object-constraint-mode per_vertex --region-constraint-mode augmented --initialization path/to/prior-candidate.npz
.venv\Scripts\python.exe scripts/audit_scene_region_fit.py reports/new-restart reports/new-restart-audit
```

Local results and preserved implementations live under `reports/region-box-augmented-regions-v1`, `reports/region-box-augmented-warm-v1`, `reports/region-box-fixed-warm-v1`, their audit folders, and `reports/region-augmented-comparison-v1`. The prior fixed baseline is `reports/region-box-object-constraints-long-v1/per_vertex`. Generated assets and machine-specific outputs are excluded from Git.

Next investigate frozen witness selection and constrained clearance together, while retaining temporal regression measurements. Do not promote stronger penalties alone or repeat this short fixture as evidence of broad motion support. Longer clips, varied actions/objects/rigs, partner reliability and human review remain required. All 14 release capabilities remain unapproved.

Follow-up: [witness reselection and interior solver margins](contact-witness-refresh-v1.md) repair the sampled native/exported box contact and clearance while retaining the acceleration regression.
