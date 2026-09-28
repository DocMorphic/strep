# Preserve joint targets during root cleanup

Development work, 2026-09-28. This extends Studio's root cleanup to completed joint edits; it does not approve their animation quality.

The root solver now has an adapter for joint edits. It retains the original world-position goals and orientations, exact rotation channels, untouched local channels, fixed context outside the edit window, the original envelope-scaled root budget, original root-step allowance and all authored support targets. It also guards acceleration at the requested joint nodes throughout the clip, as well as declared mesh patches, root acceleration, floor depths, contact positions and contact edges. Candidate checks use decoded exported GLBs, including key and midpoint geometry. They do not certify continuous collision or physical realism.

The two existing joint-edit cases from the frozen authoring intake both yield bounded root improvements. Root acceleration energy falls from 104.139 to 102.996 and from 97.578 to 97.079. Their peak and P95 root accelerations are unchanged. Maximum additional root displacements are 2.306mm and 1.725mm. World-goal errors do not increase beyond the existing one-micrometre export allowance, orientations remain identical, and outside-window transforms remain exactly unchanged. Their previous floor/support failures remain failures.

`reports/joint-root-correction-v1` contains the frozen protocol, implementation, both inputs, all proposals and exported candidates. `reports/joint-root-correction-audit-v1` independently checks both selected clips and their inputs in Godot: four GLBs and244 actor-frames. These are development cases, not held-out generalization evidence.

## Studio workflow

Select **Joint target candidate**, then **Smooth root motion**. It creates a new immutable job, with before/candidate comparisons, original joint recipe/targets, contact targets, root tracks, audit and package. Root cleanup descendants retain the first joint edit's baseline, envelope and world goals; they do not reset the original budget. The UI explicitly keeps “failed joint checks” when the source failed. The selected input opens first.

Actual UI-submitted job `20260928-105143-aed550d4` reproduces the first independently checked study output exactly. API-submitted chain `20260928-105220-0d84b0dc` preserves the original context and passes export/package/engine checks, but its improvement is negligible: energy102.995962→102.995914, approximately0.000046%. This historical result is retained. It motivated a stricter Studio acceptance floor: at least0.1% relative energy reduction as well as the existing absolute threshold. This is an engineering threshold for useful cleanup, not a naturalness or physics claim. Original study policies and historical jobs are unchanged.

The final-policy retry returned byte-identical input as intended. Three actual Studio jobs pass independent target/root/package/HTTP checks and six GLB imports over366 actor-frames. Twenty-two focused Python and eight selection tests pass. The retry is recorded in `reports/joint-dynamics-studio-v1/minimum-reduction-job.json`. Independent verifications and screenshots live in that same report directory. Tests include deliberately worsened joint targets despite unchanged rotations, displaced fixed context, violated envelope budgets and the negligible chained improvement. Backend tests also cover original recipe preservation, chaining and changed parent-request rejection.

Finger-only posture edits remain excluded: their original operation promises a fixed body and supplies no root-edit budget. We preserve that contract rather than assigning an unsolicited body edit. A future combined body/finger workflow must explicitly define and retain both sets of targets.

## Remaining work

This improves reuse of authored edits in the offline workflow. It does not repair existing support failures or partner interpenetration, establish calibrated agility/strength/stamina mappings, or replace independent animator review. The broad support study continues under its unchanged implementation. The completed partner trial needs a materially different collision formulation; repeating its previous projected solve is not justified. All release gates remain open under the same project-wide goal.
