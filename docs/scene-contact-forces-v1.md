# Supplied-rig scene contact and object forces

`scripts/scene_object_contact_forces.py` connects the conditional rigid-object force solver to the actual supplied GLB skin, authored object contacts and complete declared sampled scene geometry. A feasible target force allocation alone cannot pass the combined sampled check when the character misses the grip, presents the wrong surface normal, slips or intersects an object.

The request binds the original scene, surface policy and geometry policy by SHA-256. It requires an explicit object, mass, body inertia about its center of mass, object-local COM offset, world gravity, complete support phases, friction and a total-force cap for **every original correspondence** to that object. Provenance notes must explain the body and contact assumptions. Contacts must be sticking holds; touch/impact models are outside this implementation. All original contacts to the selected object are included, with at most sixteen points. Normals must match the unique outward normal of the actual box, sphere or cylinder at the authored local target. Ambiguous corners cannot supply an inferred normal.

The object origin is not assumed to be its COM: the explicit offset follows the original rotation before translation differences and COM-relative torque calculations. An added uniform clock of 3–900 samples includes the exact original clip endpoints. This is an explicitly declared differentiation clock, not a claim that the original nonuniform keys were uniform. The geometry audit keeps the union of **every original geometry time, every original contact time and every added force time**. Nothing is shortened to a convenient successful interval. Unknown support phases and cross-phase derivative stencils remain recorded but unassessed; endpoints have no estimate. Free flight cannot overlap a declared hold even at an endpoint.

At each force sample, actual surface points and winding normals come from the supplied skinned mesh. A supported assessment requires the full three-key contact stencil, original position/speed/opposition/side conditions and complete declared scene geometry. The conditional force result remains separately visible when these checks fail. Known supported samples with missing active contacts are assessed, rather than skipped. The combined result also requires the complete original surface and geometry audit to pass. This conservative sampled condition is not a continuous collision certificate.

Original request/policies/GLBs and method sources are frozen into a fresh ignored output. Pipeline stages preserve surface observations, streaming geometry observations, explicit force witnesses or exclusions, and all failed results. Original and copied input hashes and current/archived methods are checked again before completion. Changing an input after measurement produces a failed pipeline, preserving the partial evidence. Existing outputs cannot be overwritten.

## Validation

**95 focused tests pass in 21.82 seconds**: thirteen new scene-force regressions plus the 82 existing force, immutable force-workflow, rigid-dynamics and primitive-geometry checks. The new fixtures are closed skinned synthetic meshes, not human motion quality evidence. Both box and cylinder contact fixtures satisfy the combined sampled condition. Adding an unrelated body/object intersection keeps the conditional force witnesses but rejects the combined result. A 20 kg assumption fails the force check while preserving successful geometry. Tests also cover a rotated nonzero COM, complete contact population, mismatched primitive normals, invalid inertia, free-flight endpoint contradiction, sample limits, unsupported touch and mutation after actual measurements. All 27 test-supervisor resource records independently replay; sampled peak process-tree RSS is 151,724,032 bytes.

The public source inventory includes this fixture suite: 428 Python modules and 41 Node suites. Hosted validation of this new source is separate from the local checks. The tiny fixture job uses its explicit 512 MiB estimate plus the unchanged 600 MiB reserve. Actual full-skin/full-geometry studies retain the **2 GiB estimate plus 600 MiB reserve**, even if a sampled peak is lower.

## Run with provisioned local dependencies

Save a `strep-scene-object-contact-forces-v1` request using the implementation/tests as complete examples, then use the owned supervisor:

```powershell
.venv/Scripts/python.exe scripts/run_guarded_job.py --worker scripts/scene_object_contact_forces.py --output reports/my-scene-force-guard --expected-rss-mib 2048 --stable-seconds 15 --admission-seconds 600 --max-seconds 3000 -- reports/my-scene-force-request.json reports/my-scene-force-assessment
```

This adds an assessment component; it does not correct a clip or change a checkpoint. Hypothetical friction/caps are not calibrated human strength or gameplay-stat mappings. Winding normals do not identify anatomical palms. Actor reaction, whole-body balance, joint dynamics, slipping/impacts, self-collision, engine playback and human usability remain separate requirements. Every result keeps quality, release and training approval false. Continue the single full-project goal and the broader held-out action/scene/rig/style/transition evaluation.
