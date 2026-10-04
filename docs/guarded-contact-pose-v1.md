# Contact-protected pose search

`scripts/guarded_contact_pose.py` adds a guarded search around the existing `ContactPose` API. It starts from the unchanged source pose and requires complete declared geometry to pass at that pose and both unchanged clip endpoints. It retains the original contact points, normals, limits, source rig and object trajectories.

```python
from guarded_contact_pose import fit

controls, result = fit(problem, original_geometry_policy, contacts_sha256,
                       iterations=6, trust=0.15, solve_iterations=30,
                       maximum_seconds=240, maximum_calls=3000,
                       maximum_surface_rows=20000, observer=save_trial)
```

`problem` is a validated `native_contact_pose.ContactPose`. This remains a Python diagnostic API, without a Studio interface or portable command. It does not write a clip or select a correction for playback.

Every proposal must preserve each individual normalized condition: a previously passing row stays at or below zero, and a failing row cannot exceed its value at the retained pose. Point distances, normal opposition, both facing projections and joint displacements remain separate rows. No acceptance epsilon is added to their authored limits. The largest positive violation cannot increase, and the sum of squared positive violations must decrease by more than `1e-12` to replace a pose.

SLSQP proposes local steps within an explicit raw-coordinate trust box. The existing smooth rotation-norm balls continue to enforce physical rotation limits. Complete scene surface queries supply fixed witness-plane constraints for the proposal. The witness floor is the smaller of its current gap and minus the declared penetration allowance, so the retained pose remains feasible for those conservative planes. These planes guide the solve; they cannot certify collision acceptance.

Each proposed direction receives up to six explicit backoffs. Every evaluated backoff receives a complete triangle and containment audit, including candidates that already fail a contact row. Only candidates passing both guards can replace the retained pose. Witnesses are rebuilt from retained geometry and geometry failures; an explicit accumulated-row limit rejects overflow instead of returning a subset. The final retained pose receives another complete audit. An optional observer receives the seed, every backoff and the final pose, with contact reports and complete geometry arrays; derivative evaluations are not full audited trial observations.

The geometry clock explicitly contains three isolated times: zero, the interior probe time and clip duration. The original geometry policy's other fields remain unchanged. This clock does not replace the original full motion audit or test interpolation between these poses. All actors, declared objects, partner pairs and declared world planes are included by the existing geometry evaluator. Self-collision and object/object collision remain outside that evaluator's scope.

Iteration, local solver, elapsed-time, cached proposal-measurement and accumulated witness-row budgets are explicit. `maximum_calls` counts uncached proposal measurements used by the local solver, rather than setup, guide construction, backoff or final audit measurements. Elapsed time can exceed the chosen budget by an in-flight geometry query, observer write or mandatory final audit. Budget exhaustion keeps the audited retained pose and reports the reason; iteration exhaustion is also recorded as a budget stop. Optimizer success is not an acceptance condition.

Missing source normals or unavailable initial full geometry reject before optimization. No failed search establishes that correction is impossible. Even a successful single-pose witness leaves temporal coupling, rate caps, native serialization, imported skin, dynamics, anatomy and human review unverified. Original clips remain selected; quality and release approval are always false.

## Validation

Fifteen synthetic tests cover individual-row protection despite aggregate improvement, complete shape/finite checks, unchanged endpoint/source samples, actual closed-mesh geometry populations, mandatory audit of all rejected backoffs, invalid initial geometry, budget exhaustion and invalid budgets. The closed mesh fixture retains all original faces and a declared object. An initial open-mesh fixture correctly failed containment and was replaced for the success-path test; incomplete geometry rejection remains tested. These tests provide no human quality evidence.

All 65 focused guard, pose and surface tests pass in a fresh source-only copy without vendor code, model weights or character assets. The public Windows/Linux source workflow includes the new guard tests; remote completion is reported separately from local validation.

## Retained sphere-hold experiment

The guarded search uses the same ten object correspondences and surface policy as the preceding [unprotected pose probe](native-contact-pose-v1.md), at 3.914583333 seconds. It starts from zero correction on the canonical source GLB. Twelve explicit forearm, wrist and first-finger channels retain newly declared 45-degree single-pose rotation permissions and a 0.22 m joint displacement condition. These permissions do not reset the original clip's edit permissions or temporal caps. Point limits remain 5 mm, normal opposition 15 degrees, facing allowance 0.5 mm and declared geometry penetration 5 mm.

The experiment stops at its 3,000 cached proposal-measurement budget after 155.109 seconds. Two local solves each reach their 30-iteration limit without solver success. Four backoffs receive complete mesh audits, and two are retained. A full first step fails both individual contact protection and geometry with 8.994412 mm of depth upper bound. Its half step passes. A later full step has passing geometry at 4.863912 mm but fails contact protection; its half step passes both. This demonstrates why neither a lower aggregate error nor geometry alone can select a pose.

| Contact group | Source point maximum | Retained point maximum | Source normal maximum | Retained normal maximum |
| --- | ---: | ---: | ---: | ---: |
| Left grip | 2.015470 mm | 1.923011 mm | 15.427091 degrees | 9.717055 degrees |
| Right grip | 2.007782 mm | 1.707064 mm | 14.701341 degrees | 9.530711 degrees |
| Left neighbours | 4.678915 mm | 4.311464 mm | 47.083186 degrees | 40.869125 degrees |
| Right neighbours | 4.676915 mm | 4.073582 mm | 46.548447 degrees | 40.733416 degrees |

All normals remain available and every original condition row is protected. Worst positive normalized violation falls from 2.060035 to 1.674845, and its squared sum falls from 8.362135 to 5.581800. The retained maximum rotation change is 11.315675 degrees. Complete declared geometry at the retained pose and both unchanged endpoints passes with a maximum depth upper bound of 0.550813 mm. The two neighbouring surface normals above 40 degrees still fail their 15-degree conditions, so no valid pose witness is found.

The scene includes the original sphere hold and an unchanged second moving sphere, one humanoid with 18,056 vertices and 36,108 faces, and no partner or world plane. All six saved observations (seed, four backoffs and final) preserve complete geometry arrays. Independent Rodrigues/hierarchy reconstruction, scalar full skinning and complete incident-face contact calculations agree with those observations. All four retention decisions, 36 saved actor/object geometry reductions and 974 positive analytic sphere-depth witnesses replay. Complete collision and containment queries are not rerun by the verifier.

The source reader's normalized skin weights differ from the earlier raw Godot import epoch. This experiment does not validate imported playback, generate a corrected motion curve, establish anatomical correctness, test self-collision or provide human review. The retained failure does not establish infeasibility. No clip is exported or selected, no release evidence is added, and the full project goal remains active. Local evidence remains ignored under `reports/guarded-contact-pose-development-v1`, `reports/guarded-contact-pose-verification-v1` and `reports/guarded-contact-pose-clean-source-v1`.

The subsequent [native pose lift](native-pose-lift-v1.md) exports this donor onto an actual editable curve. Although pose and payload checks pass, its full contact-speed and source motion-rate audit fails. The isolated geometry pass here does not apply to that exported motion.
