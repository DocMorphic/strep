# Object-only contact preflight

`scripts/rigid_contact_preflight.py` turns a completed imported [surface audit](native-object-scene-surface-v1.md) into a source-bound authoring diagnosis. It answers a specific question: can a rigid object correction satisfy the authored normal opposition limit while the measured character surfaces and object-local target normals stay fixed?

```powershell
python scripts/rigid_contact_preflight.py PATH_TO_IMPORTED_SURFACE_AUDIT PATH_TO_FRESH_OUTPUT
```

Use `--mode default-import` to diagnose that observation epoch separately. Native authoring is the default. This command uses saved CPU observations and rechecks the original imported scene receipts. It launches no engine, generates no new motion and changes no asset or target. It requires the retained input files and method versions used by the audit; a changed input requires a new audit.

The output directory must be fresh and outside both the imported audit and its original bounded scene. The result records the exact audit, original contact declarations, policy, observation mode, methods and file hashes. It retains all contact samples, point identities, active populations, exact times and witness pairs. Original assets remain selected.

For each rigid object, the preflight visits the union of its contact clocks without rounding or interpolation. At each time it combines all active object-local target normals and measured source normals, including contacts from different actors. Different objects and disjoint times cannot constrain one another. Centroid contacts retain their complete authored vertex group as one normal point.

The [angular-spread bound](native-object-scene-surface-v1.md#why-an-object-only-refit-cannot-meet-these-conditions) gives a necessary maximum error for any common proper object rotation; translation cannot change directional spread. A witness identifies two authored points, their source and target angular separation, the resulting lower bound and the exact sampled time. The diagnostic allows arbitrary object rotation solely to obtain this necessary bound; it does not change the actual object's movement or rotation budget.

| Result | Meaning |
| --- | --- |
| `incompatible_fixed_surfaces` | At least one sampled object time has a necessary error above the authored limit plus a conservative numerical comparison reserve. |
| `unknown_normal_unavailable` | No reported conflict, but at least one complete active population contains an unavailable normal. |
| `not_ruled_out` | This necessary test did not establish a conflict. It does not construct a feasible object pose or animation. |
| `not_applicable` | No rigid object contact is declared. World and deforming partner targets require separate checks. |

Missing normals keep the complete frame unknown; no point is dropped to get a favorable decision. A known conflicting frame remains reported even if other frames are unknown. World and partner contacts remain explicitly listed outside this test. Invalid or oversized complete populations fail rather than truncate. The limits are 20,000 times per object and 256 active points per time.

A 1e-8 degree comparison reserve makes floating rejection more conservative. It is not an authored acceptance allowance or a formal interval certificate. All actual opposition, position, speed, geometry and motion conditions still apply unchanged.

When a conflict is reported, inspect the contact region and authored local normals or investigate body/hand corrections, then remeasure the resulting motion. The report cannot reject edits that change those inputs. Do not silently delete points, raise a limit or reinterpret an existing benchmark to obtain a pass. Matching pairwise spread does not prove a proper rotation exists; chirality, point positions, body reach, dynamics and full scene geometry remain separate.

This is an offline command and JSON diagnosis. It is not yet exposed in the Studio contact panel. It does not infer anatomical palms, prove continuous-time safety, assess force support or provide human animation-quality approval.

## Validation

Twenty-three synthetic tests cover overlapping contacts from multiple actors, separate objects, disjoint and nearly identical clocks, centroid identity, unavailable normals, unsupported target kinds, observation modes, unchanged authored limits, complete input validation, immutable transport and fresh output requirements. Together with the 14 angular-spread tests, all 37 focused checks pass. Mocked transport fixtures do not constitute real engine or anatomy evidence.

The actual command reuses the unchanged imported sphere hold and reproduces the independently replayed lower bound at all 1,033 original clocks. It retains four contacts, 4,132 contact-time records and all 10,330 point-normal observations. Every object time reports a conflict. The strongest witness is `left-grip-neighbours:2` against `right-grip-neighbours:2` at 3.914583333 seconds, requiring at least 41.312101 degrees against the authored 15-degree limit. No normal is unavailable and no contact is outside the object test. The run takes 87.653 seconds, including retained receipt checks; no object or actor is edited. This is one development hold, not held-out action, rig or anatomical evidence.

All 37 tests also pass from a fresh isolated source copy with no vendor code, models or character assets. Actual evidence is under `reports/rigid-contact-preflight-development-v1`; source-only validation is under `reports/rigid-contact-preflight-clean-source-v1`. All 14 release capability evidence lists remain empty, and acceptance fields are unchanged.

Source CI now keeps an in-progress run alive while a newer commit waits in the same concurrency group, following [GitHub's concurrency behavior](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/control-deployments). The latest pending commit can replace an older pending commit; this does not guarantee a run for every queued commit. No test or gate is removed. The full project goal remains active.
