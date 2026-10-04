# Surface-facing audit of an imported object scene

`scripts/native_object_scene_surface.py` adds explicit surface-facing conditions to a completed [bounded imported scene](native-object-bounded-scene-v1.md). Close point positions and a collision-free sampled mesh do not establish anatomical grasp, force support or action quality. The original motion remains selected, and the prior scene decision is preserved separately.

```powershell
python scripts/native_object_scene_surface.py PATH_TO_BOUNDED_SCENE SURFACE_POLICY_JSON PATH_TO_FRESH_OUTPUT
```

The policy uses the existing [surface-contact schema](native-surface-contact-v1.md) and binds the exact contact JSON. It covers every declared contact. World/object targets need explicit unit normals in their declared coordinates; partner targets derive normals from their exact target vertices. Opposition angle, facing-side allowance and normal area/coherence thresholds are authored conditions. The pose-query budget must cover the complete population; it never truncates frames or points.

The workflow rechecks the full bounded-scene file inventory, source/method receipts, original-relative object handoff, actual actor and object producers, complete identical clocks and saved-result replay. It then measures point positions and incident-face normals using the **same imported CPU skin observations** and actual object Animation-resource poses. Passing source points cannot substitute for different imported points. Raw imported skin weights are not renormalized. Source triangle winding is preserved in the normal definition after complete imported triangle correspondence has been checked; outwardness or anatomical palms are not inferred.

For every existing contact clock and point, the existing normal evaluator retains all incident triangles, area/coherence reliability and degeneracy checks. Source/target normals must oppose within the authored angle, and both facing-side projections must meet the authored allowance. The earlier position/speed conditions still apply. Default object import and native authoring are recorded separately. A failed earlier scene cannot be approved by a passing additional surface audit.

All inputs and methods remain bound, and fresh outputs retain the policy, normal arrays, detailed results and file hashes. No asset is edited, no engine is launched and no collision query is rerun. The earlier complete scene geometry remains bound evidence. This audit does not establish continuous collision, self/object-object collision, dynamics, runtime/GPU behavior or human animation quality.

## Tests

The focused suite has 36 passing tests: 28 existing surface-contact tests and eight imported-scene tests. Synthetic observations exercise imported pose changes, shared point/normal epochs, object-pose drift, retained default-import failure, opposite-normal rejection, original-scene failure retention and changed/pending/unbound inputs. The complete workflow fixture explicitly mocks engine observations; it is not actual Godot or human evidence. An initial nested worker-lock failure is retained in the local test log and corrected without changing any earlier scene method or gate.

The combined 50-test suite also passes in an isolated copy containing source and recursively required test fixtures, with no vendor code, models or character assets. This includes the 14 angular-bound checks described below.

## Retained sphere hold

The real follow-up reuses the unchanged humanoid, ten source correspondences and actual imported producers from the preceding study: 18,056 vertices, 36,108 faces, 2,201 bound scene times and two declared spheres. The target named `box` is a 0.25 m radius sphere. No partner or ground plane is declared. This is one retained development hold, not held-out action or rig coverage.

The new policy explicitly supplies outward radial object-local normals at the ten existing sphere target points, with a 15° maximum opposition error, 0.5 mm backface allowance, minimum twice-area 1e-14 m² and minimum coherence 0.1. These are additional prototype diagnostic conditions; they do not replace or relax any original contact, motion, geometry or release requirement. Each mode evaluates 1,033 clocks per contact group, 4,132 actor-pose queries and 10,330 point-normal observations. Execution took 396.494 seconds on the local CPU.

All four native point-contact conditions still pass. Normal availability and both facing-side projections pass everywhere, but three of four groups fail opposition. Native authoring produces:

| Group | Maximum opposition error | Failed point-normal observations | Orientation/side result |
| --- | ---: | ---: | --- |
| Left grip | 15.493971° | 1,033 / 1,033 | Fail |
| Right grip | 14.776059° | 0 / 1,033 | Pass |
| Left neighbours | 47.135702° | 3,099 / 4,132 | Fail |
| Right neighbours | 46.595273° | 2,066 / 4,132 | Fail |

The aggregate added audit fails in both native authoring and default import. The prior sampled scene success remains true; the combined decision with these new conditions is false. No point, frame or poor outcome is omitted to obtain a pass. These failures may indicate unsuitable point/patch selection, overly strict authored conditions for a curved contact region, or motion defects; they do not by themselves prove the generator is wrong or establish a valid anatomical grasp.

Local evidence is under `reports/native-object-scene-surface-development-v1`. Independent replay reconstructs all complete incident populations from imported bones and raw skin weights, supplied normals and original point/object clocks. All 20,660 decisions across both modes agree. Maximum angle replay difference is 7.284e-14 degrees and maximum projection difference is 8.674e-19 m; these are numerical replay comparisons, not relaxed authored acceptance limits. Collision/containment queries are not rerun. Evidence: `reports/native-object-scene-surface-verification-v1/result.json`. The full project goal and all release requirements remain open.


## Why an object-only refit cannot meet these conditions

`scripts/rigid_normal_spread.py` computes a necessary angular bound for fixed source normal populations and fixed target normals sharing one rigid object pose. For source-pair angle `a_ij`, local target-pair angle `b_ij` and opposition errors `e_i`, `e_j`, rotation invariance and the spherical triangle inequality give `|a_ij - b_ij| <= e_i + e_j`. Therefore the maximum opposition error is at least half the largest pairwise spread difference. Translation has no effect on these directions.

This floating diagnostic retains every supplied frame and point. It is not a formal interval certificate, a continuous-time proof or a sufficient feasibility test: matching pair spreads can still require an improper reflection. Fourteen synthetic tests cover an attained 45° bound, independent common rotations, retention of a failing frame, chirality and invalid populations/limits.

All 1,033 shared native hold times reject the authored 15° condition:

| Fixed source population | Points | Smallest frame lower bound | Largest frame lower bound |
| --- | ---: | ---: | ---: |
| Left grip and neighbours | 5 | 26.458003° | 26.462404° |
| Right grip and neighbours | 5 | 26.439062° | 26.449911° |
| Both groups together | 10 | 41.290739° | 41.312101° |

All returned witnesses are independently recomputed with scalar direction angles. This relaxes the original 2° object rotation budget to arbitrary rotation solely to derive a necessary obstruction; no actual proposal or acceptance budget is changed. Additional object-only search cannot resolve the declared mismatch with the measured surfaces held fixed. The next investigation must distinguish contact-region/condition authoring from changes to the body or hand surfaces. New correspondences, normals, geometry, conditions or body edits are outside this conditional bound; none is ruled out or approved. Local evidence: `reports/rigid-normal-spread-development-v1/result.json`.
