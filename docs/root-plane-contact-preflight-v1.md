# Vertical root correction must preserve declared contacts

`native_root_plane_preflight.py` checks necessary per-pose vertical root intervals before a correction is attempted. It intersects every triangle-referenced floor vertex with every affected declared point contact, including incoming partner targets and centroid reductions. Existing limits remain intact. Empty intersections reject this restricted translation hypothesis; nonempty intersections do not establish a feasible clip.

```powershell
python scripts/native_root_plane_preflight.py contacts.json geometry.json fresh-output --actor character --root 21 --plane ground --maximum-shift 0.22
```

The plane must be explicitly upward and horizontal. Inputs bind a supplied rig, animation, placement, scene geometry and contact intent. The native/frame-population floor clock is expanded with every affected contact time. Other actors and objects stay fixed for this diagnostic. Source files and selection remain unchanged; no clip is exported.

The scalar helper computes each vertex's root-subtree translation coefficient from all normalized skin influences and their actual inverse-bind homogeneous coordinates. Static/unaffected vertices remain included. Each floor inequality supplies a lower or upper root bound; each Euclidean point contact supplies an interval after preserving horizontal error. Zero-response floor/contact failures cannot disappear. Incoming contacts negate the target actor's coefficient. Object contacts use world differences so moving object orientation cannot change the position norm.

These are ordinary Float64 calculations, not certified interval arithmetic. The diagnostic omits key interpolation, original source-rate limits, contact slip, other planes, actor/object/partner collisions, balance and anatomical interpretation. It leaves clip feasibility, quality, training and release approval false.

## Complete-clock development evidence

The four unchanged Kenney scenes retain the original Y=0 / 5-mm floor and 22-cm root ceiling. No contacts are added to these baseline cases.

| Action | Sample times | Empty per-pose intervals | Maximum necessary upward shift (mm) |
| --- | ---: | ---: | ---: |
| Crawl | 2,017 | 447 | 258.015 |
| Kick | 2,017 | 0 | 44.728 |
| Get up | 3,033 | 1,070 | 657.259 |
| Run, roll and stand | 3,541 | 236 | 989.774 |

The kick's nonempty floor-only intervals are not support or motion approval. A separate authored development case pins one right-foot-dominated vertex to its original position at 0.733333349 seconds with 5-mm position tolerance. Clearing the other foot requires 44.728 mm of lift, while this pin permits only 5 mm; their intersection is empty. The pinned point is at Y=1.586907 m. It is a deliberate position-preservation example, **not** detected planted-foot support, original model intent or anatomical approval. Original baseline contact lists remain unchanged.

This rules out a simple lift for the declared pin and motivates articulated correction or a reviewed contact-aware retransfer. Earlier reference-proportion and torso-mapping studies already exist: the [reference diagnostic](kenney-reference-diagnostics-v1.md) found large pelvis-relative head/hand differences, and the [torso mapping alternative](kenney-torso-mapping-comparison-v1.md) worsened overall failures. Those studies are retained rather than repeated or promoted.

All 53 related tests pass, including sixteen new cases for incoming/outgoing contacts, static and negative coefficients, complete vertex populations, homogeneous skin response and rejection/approval scope. Validation takes 5.031 seconds/23 resource observations. The five-case study takes 41.500 seconds/59 observations. Fresh replay reproduces all 12,625 per-pose intersections and observation arrays exactly. Separate scalar influence arithmetic matches every coefficient; direct subtree translation matches its predicted skin displacement at each case peak. Replay takes 42.454 seconds/60 observations. All resource-policy traces replay with matching bindings.

Private records remain under ignored `reports/root-plane-contact-validation-v1`, `reports/kenney-root-plane-preflight-v1` and `reports/kenney-root-plane-replay-v1`. Shared readers/samplers remain; this is not independent physics or human evaluation. No model generation, new weights, reserved release cases or human cleanup ratings are used.

## Hosted checks

At `cf4f3d6`, both lineage jobs pass after the prior fixture correction. Both Windows contact/rig shards reach the 15-minute job deadline; their logs report 523/469 Python passes and 10/23 subtest passes immediately before cancellation. Ubuntu contact/rig and both game-package jobs pass. The focused CI allowance is now 90 minutes, matching the main source-check allowance, so the complete declared suite can finish. No tests or numerical gates are removed, and the local 900-second worker execution limit and memory admission remain unchanged. The new hosted outcome is pending.

The full-project goal remains active. Root-only rejection is a useful authoring diagnostic, not a replacement for robust retargeting, articulated support correction, transitions, styles, held-out evaluation or animator review. All fourteen capability approvals and release gates remain unchanged.
