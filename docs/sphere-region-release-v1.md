# Release return experiments

Two 24-frame return profiles preserve the passing geometry from the [approach and floor corrections](sphere-region-boundaries-v1.md), but neither removes the whole-clip speed regression. These are development experiments; all 14 release capabilities remain unapproved.

The release endpoint remains frame 121. Both variants edit only frames 122–144 and return to the original V13 motion at frame 145. All 157 other frames are exactly equal to the floor-corrected input, including approach and grasp. No contact event, clip length, model checkpoint, or original edit budget changes.

`region_release_blend.py` interpolates physical rotation-vector edits between the frozen grasp endpoint and each original frame. Convexity preserves the original joint norm balls; geometry still requires a separate audit. V1 uses a symmetric quintic return. After its speed peak was localized to the right index finger at frames 130.75–131, V2 moves decay earlier using `(1-t)^8 * (1+8t+36t²)`. Both profiles have zero first and second endpoint derivatives. This is adaptive development work, not a held-out comparison.

| Clip | Peak joint speed (m/s) | Peak joint acceleration (m/s²) |
| --- | ---: | ---: |
| Original V13 comparison | 1.409751 | 38.516182 |
| Prior corrected 12-frame return | 1.742135 | 46.718854 |
| V1: symmetric 24-frame return | 1.697571 | 36.587825 |
| V2: earlier 24-frame return | 1.670456 | 42.927208 |

V1 reduces acceleration below the original comparison but retains higher speed. V2 further reduces speed, while increasing acceleration relative to V1 and the original. It is not an across-the-board improvement. Right-hand release-boundary relative speed changes from 0.120362 m/s in the prior clip to 0.139982 in V1 and 0.117453 in V2. The corresponding left-hand values are 0.121723, 0.103389 and 0.130222 m/s. Global peaks and individual boundaries must both remain visible; no variant is promoted to a production default.

Both actual exported GLBs retain all 245 passing grasp samples, zero geometry failures across 717 integer/quarter-frame samples, and zero original edit-budget failures. Minimum floor height is 2.001973 mm and minimum sphere clearance is 2.069914 mm. Maximum joint edit is 38.502996 degrees. The auditor reconstructs native edits independently, verifies protected frames and source hashes, and evaluates the decoded exports. For V2 it computes the return weight using an independent binomial expansion.

Godot imports both variants and matches all 360 actor-frames with 77 bones. Maximum position discrepancy is 0.385 micrometres. Eighteen focused tests pass across release profiles, grasp transport, floor constraints and approach geometry. These checks do not approve anatomy, continuous or triangle-interior collision, self-collision, balance, forces, naturalness, gameplay events or animator cleanup time. The original fixed-point grasp condition is still unsolved; these clips use the explicitly authored region condition.

An offline side-by-side preview renders the actual SOMA skin and sphere for the prior clip and V1. It samples frames 100–178 every three frames at 10 fps. Its frame-130 image was inspected for framing and legibility. Painter-order triangle rendering has approximate occlusion and lighting; this is not GPU fidelity or developer motion approval. No human ratings or cleanup times have been recorded.

Local immutable evidence: `reports/sphere-region-release-v1`, `reports/sphere-region-release-v2`, their `-audit` siblings, `reports/sphere-region-release-diagnostic-v1`, `reports/sphere-region-release-preview-v1` and `reports/sphere-region-release-engine-v1`. Generated models, meshes and reports are excluded from Git. The historical V2 protocol's generic scope text says “quintic”; its explicit `profile: early-return`, retained source snapshot and independently verified weights record the actual calculation. Future writer wording is corrected without altering that evidence.

Next, examine the spatial release path and its temporal derivatives under the unchanged geometry/budget constraints. Longer duration alone is insufficient. Broader actions, objects, rigs, partners and real review remain required.

## Reproduction

Existing local fixtures and separately acquired licensed dependencies are required. Use fresh output directories; the public repository is a development source snapshot, not a bundled model distribution.

```powershell
.venv\Scripts\python.exe scripts/region_release_blend.py reports/sphere-region-floor-v1 reports/new-release --blend-frames 24 --profile early-return
.venv\Scripts\python.exe scripts/audit_region_grasp_track.py reports/sphere-region-track-v2 reports/new-release-audit --approach-patch reports/sphere-region-approach-v1 --floor-patch reports/sphere-region-floor-v1 --release-patch reports/new-release
```

Follow-up: [spatial arm return](sphere-region-spatial-v1.md) removes the speed regression but retains acceleration and endpoint continuity defects.
