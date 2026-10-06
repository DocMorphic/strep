# Reusable stored-centered scene model

`scripts/native_stored_pair_model.py` turns the validated stored-centered setup into a backend library API. Its retained pair-fixture correction reaches 5.117411 mm worst penetration while preserving sampled native/contact/reference checks, but complete geometry still fails. No asset is approved.

## API and contract

The caller supplies an existing `SceneProblem` with explicit `StorageAdjustedEdits`/boundary permissions, anchor controls, exact exported clips for every edited actor, an anchor guide scene and guide geometry policy, and the original source geometry policy. The caller must first include the complete geometry clock in the original problem while preserving its original reference worlds and rate arrays. The guide changes only edited clip paths/hashes; it retains all participants, duration, selected animation indices, placements, contacts, object geometry/trajectories and geometry limits/planes/clock. Each frozen actor retains its actual source clip.

```python
from native_stored_pair_model import model

centered, native, native_jac, guides, gaps, surface_jac, report = model(
    problem, anchor_controls, anchor_files,
    guide_scene, guide_policy, guide_contacts_sha256, .02,
    source_policy=original_geometry_policy,
)
```

`centered_problem(...)` offers just verified curve setup and anchor decoding. `model(...)` additionally rebuilds every native and surface condition/derivative through the existing complete pair model. It returns the centered problem and full model arrays, preserving the caller's original editor, reference/cap inputs and original export/audit path. The stored-anchor report records clip hashes, editor binding, separate canonical policy-contract hashes, complete sample counts and measured pose differences. These are proposal diagnostics, not approval.

This is a backend API; it is not yet a new Studio action or standalone authoring-job CLI. Callers must retain input/provenance snapshots, worker ownership, exported failures and full decoded/geometry acceptance.

## Frozen-participant regression and versions

API review after the first full producer and complete-model consumer terminate reproduces a failure: shifting an unedited partner's reference worlds by 10 mm is accepted as its actual playback even though its source clip is unchanged. The failing test, its terminal exit 1 and the original implementation are retained. The new guard explicitly compares frozen playback against the source sampler and rejects the mismatch. Original references may not replace an unedited participant's actual motion.

The full study ran the archived initial API. After the guard fix, a separate current-version check reproduces its entire centering report and every native anchor vector/cap/scale exactly. Both study actors are explicitly edited, so the added frozen branch is not taken; no completed derivative study or solve is rerun. All other method bytes and original inputs remain unchanged. The subsequent stored repair archives the current API version.

Sixteen new cases plus forty-six existing curve/pair/depth cases pass: 62 tests, zero skips. Tests cover actual complete model construction, source-editor/reference preservation and rejection of changed geometry limits/planes/clocks, contact intent, object shape/path, edited/frozen payloads, placement, participant count, unsupported editors, missing geometry times and frozen-reference drift. CI adds exactly one suite.

## Complete retained fixture study

The generated cube-skin pair retains thirty controls, fourteen starting storage corrections, all nine original rate arrays, 29290 native norms, 1707 native times and 1673 geometry times. All 276776 surface conditions remain represented by 118061 equivalent rows and 158715 independently verified exact dominance implications, with 2852 partner depth witnesses. Complete native Jacobian replay matches exactly; all thirty scalar derivative columns replay within 4.440892098500626e-13. The independent consumer imports neither the new API/proxy nor guard/reduction/solver implementations.

Primary depth restoration returns AlmostSolved after 32 iterations. The surface phase reports InsufficientProgress and minimum-norm does not run; the last primary proposal is retained only for measurement. Predicted native excess is about -3.46e-9 and normalized depth deficit .01930685, without a nonlinear feasibility certificate.

| Fraction | Stored native failures | Centered smooth failures | Legacy smooth failures | Contact failures | Complete geometry depth |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 39 | 33 | 33 | 0 | 5.095609 mm, failed |
| 0.5 | 3 | 0 | 18 | 0 | Not assessed |
| 0.25 | 9 | 0 | 15 | 0 | Not assessed |
| 0.125 | 3 | 0 | 12 | 0 | Not assessed |

Every raw fraction fails native acceptance while all cumulative original-reference bounds pass. The full proposal has 30446 triangle records, 60 contained vertices and 1599 failed geometry samples. The centered/legacy values share each fraction's controls; they are not matched alternative solver runs.

## Fixed-control half-step repair

The unchanged bounded search tests two absolute neighboring Float32 component choices across three retained raw probes. The first neighbor increases native failures from 3 to 6 and remains rejected; the second clears them. Final correction count is fifteen, below the unchanged maximum 64; each component is one signed neighbor of the new nearest stored payload, never a repeated incremental ULP walk. Contacts and all original reference/edit bounds pass.

Complete repaired geometry improves from 5.139443 to 5.117411 mm, with 30427 triangle records, 72 contained vertices and 1599 failed samples. It still fails the unchanged 5 mm limit and crossing checks. No complete unrepaired half-step geometry exists, so no isolated geometry effect is attributed to storage repair. Original-reference displacement is at most 1.389911 mm and rotation-key change at most 0.219233 degrees, below 30 mm/5 degrees.

Both appended index 5 variants retain all five original animations and original binary prefixes and reproduce every selected native world byte. A separate consumer imports neither search nor storage wrappers and replays every raw payload/world, original rate/contact/reference checks, library append and geometry population/limits/transport. Geometry predicates are not independently recomputed.

The fifteen-correction clip is pinned only as an unapproved next-model anchor. Rebuild all stored offsets and witnesses before another solve. Broader actions/rigs/objects/partners, authoring-job integration, engine and developer/animator cleanup review remain open. No new model sampling/training, production anatomy, engine, rendering/GPU, physics or human-quality result is claimed. All fourteen release evidence arrays remain empty.

## Retained receipts

Generated studies stay in ignored `reports/`. SHA256:

- reusable-stored-depth-probe-v1: `c33a8514653461d9dea24360060bd83b4df65b0185dd62caf7cdd798203ac49a`
- reusable-stored-depth-independent-v1: `4e6206ed9631b60bda354a601e8b8525fd28911f1ffcb0e6b93e9dcf117a82a4`
- reusable-stored-depth-storage-v1: `d3e6d143f5c984d212d409928795f0a87d8e0f13dec64b1e7e4311a1f3c6bac0`
- reusable-stored-depth-storage-independent-v1: `ac8943287d0beb3d7bf8f151195f987a2ba732b7cc29888a8d96dd52d61d61c8`
- frozen_actor_reproduction: `dd0f22373e39f998bc1ee81a1ced6c7db6e2a93789dbf63cc95041669c9e3425`
- guard_anchor_check: `734e994cc281878829a1b7dae317cf62c8b9da0f3b1b52be5c15fbdb7fce096e`
- tests: `c7dcf702a69540e8e9aa483843a6b8a48bc2deea661fb1862c4185de2db4abf0`
- unapproved_anchor: `387737cefa08a9a528206686b3b2853b0e3c5b4e64f9d808c01807f2d51fd0d1`
