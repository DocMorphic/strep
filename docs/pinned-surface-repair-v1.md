# Articulated clearance with a declared foot target

The root-only preflight found that lifting the kick character enough to clear the floor would violate a separately declared right-foot position target. This follow-up tests articulated correction with the root fixed. It finds no acceptable changed clip within its finite search budget. Original assets, source motion limits and failed proposals remain available; this is development evidence, not release approval.

## Public fitting option

The normal `native_scene_fit.py` entry point now accepts `--storage-repair-search paired` with an explicit typed component repair policy. This exposes the existing coordinated search previously used through study-specific helper configuration. The request and result record the selection, and the implementation archive binds the paired-search source. The default remains the existing single-component search.

```powershell
python scripts/native_scene_fit.py contacts.json permissions.json fresh-fit --proposal-model surface-vector --geometry-policy geometry.json --boundary-edit boundary.json --storage-repair-policy component-policy.json --storage-continuation original-bound-start.json --storage-repair-search paired --storage-repair-stages 2 --storage-repair-probes 8 --iterations 1 --vector-difference-step 0.001 --plane-guidance minimum-envelope
```

Inputs must be prepared with matching scene, boundary-authoring, component-policy and continuation digests. The continuation remains bound to the original rig and motion, rather than using a repaired clip as a new source-rate reference. A newly declared contact requires an explicit authoring/state binding. The search does not invent contact intent.

Paired proposals coordinate two absolute nearest-Float32 component choices on one permitted track: distinct components at one key, or the same component at adjacent editable keys. Existing one-neighbor and correction-count bounds still apply. Every exported neighbor receives complete native-condition checks. A partial repair that still fails does not become the returned candidate. Returned exports additionally receive the full geometry audit in surface fitting. This option is currently available through the Python API and CLI; no Studio search selector is claimed here.

## Actual constrained trial

The test starts from the previously replayed, motion-feasible kick candidate. The source remains the original Kenney development transfer, with its original 120-Hz motion caps, four rate arrays and `1e-5` tolerance. Permissions retain 30-degree track edits, 22-cm maximum joint displacement, preserved endpoints and four left-leg rotation tracks (nodes 50–53). Root node 21 remains unchanged. There are 72 controls, 107,527 original native conditions and one additional authored position condition.

The separate target preserves one right-foot-dominated surface vertex at its original world position at 0.733333349 seconds, within 5 mm. Its world height is 1.586907 m: it is a raised-foot position example, **not detected planted-foot support**, a contact inferred from the model, or anatomical approval. The original baseline contact list remains intact.

One surface iteration uses the existing maximum 0.02 trust fraction, a 0.001 difference step, no restoration, and minimum-envelope guidance. Optional paired storage repair is bounded to two stages and eight probes per stage. Actual returned geometry covers every 1,029 triangle-referenced vertices and 1,604 faces at all 2,017 floor times. The floor remains Y=0 with 5-mm tolerance.

| Returned candidate | Native failures | Unrounded failures | Peak floor depth (mm) | Failed floor times |
| --- | ---: | ---: | ---: | ---: |
| Start | 0 | 0 | 47.229222 | 232 |
| Full proposed step | 3 | 4 | 42.958846 | 228 |
| Quarter step | 1 | 1 | 46.214081 | 231 |
| One-sixteenth step | 1 | 0 | 46.978732 | 232 |
| Final retained trial start | 0 | 0 | 47.229222 | 232 |

All ten changed returned proposals fail at least one native condition, so none is accepted. Six smaller proposals have zero unrounded failures but still fail after serialization. These results support retaining decoded checks; they do not establish global infeasibility or justify weakening the motion limits. The final position error is `3.140185e-16` m, far below its unchanged 5-mm target tolerance, while the floor screen still fails.

The completed trial takes 747.297 seconds with 756 resource observations. Fresh numerical replay reconstructs all twelve returned exports, exact GLB bytes, complete pose/residual/control/cap/scale/clock arrays and unrounded residuals. It independently rechecks the final complete floor population, original rate-cap arrays and fixed root. Replay takes 84.031 seconds with 101 resource observations. Both recorded resource traces replay with matching bindings. Internal motion-only storage neighbors are archived but are not all independently numerically replayed in this follow-up.

The first setup attempt requests a 0.04 trust fraction and is rejected before optimization by the existing 0.02 ceiling. Its failure and all 35 resource observations remain retained; the corrected run uses a fresh output directory. No ceiling or admission policy is enlarged.

Private records are under ignored `reports/kick-pinned-articulated-v1`, `reports/kick-pinned-articulated-v2`, `reports/kick-pinned-articulated-replay-v1` and `reports/native-surface-pair-validation-v1` / `v2`. Generated character payloads and reports stay excluded from public Git.

## Validation and remaining work

The new public-option tests verify rejection before source loading, policy compatibility, actual exported-byte/complete-observation equivalence for an already feasible start, original cap preservation and archived method identity. The first batch passes 134 checks but one new fixture omits a required geometry-policy argument and reaches the wrong rejection. Its failure remains retained. After that fixture is corrected, all six new-option checks pass; source behavior is unchanged. Together the runs verify all 135 selected checks, including existing fitting, continuation and coordinated-repair regressions. The first batch takes 89.141 seconds/106 resource observations; the targeted retry takes 12.203 seconds/30 observations. Both resource traces replay. The declared inventories now contain 491 Python/43 Node source modules and 53 focused Python/3 Node modules.

All eight [contact and rig regression jobs at 96a518e](https://github.com/DocMorphic/strep/actions/runs/38597574619) pass on Windows and Linux. That verifies the preceding preflight source and compatibility contracts, not this new option or realistic kick motion. The full model-free source run remains in progress at the time of this report.

Further correction should address target-rig geometry and contact constraints during transfer rather than assume repeated tiny stored-key changes will solve morphology errors. Position-and-orientation retargeting has research precedent in [GMR](https://arxiv.org/abs/2510.02252); its humanoid-robot setting does not validate arbitrary game skins. NVIDIA also documents that Kimodo can miss constraints and exhibit foot sliding in its [limitations](https://research.nvidia.com/labs/sil/projects/kimodo/docs/key_concepts/limitations.html). These sources motivate a measured transfer comparison; they are not evidence of an implemented or passing alternative here.

No model generation, training, reserved held-out cases, engine execution, new human ratings or cleanup measurements occur in this trial. All fourteen capability approvals and release/calibration gates stay unchanged and unapproved. The entire-project goal remains active, including diverse actions, editing/style controls, scene/partner interactions, transitions, engine/runtime validation and developer review.
