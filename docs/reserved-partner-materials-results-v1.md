# Reserved neutral hand-material inventory results

The complete source-bound hand inventories are built and replayed for all three reserved directed pairs, both actors and both hands. The unchanged neutral fixture scenes still contain no contacts or animations. This prepares material surfaces for subsequent explicit palm/grip authoring; it does not select those surfaces or validate an interaction.

## Complete population

| Reserved rig | Eligible triangles per hand | Eligible vertices per hand | Instances of each hand |
|---|---:|---:|---:|
| rig-held-01 | 1,351 | 893 | 2 |
| rig-held-02 | 1,544 | 1,004 | 2 |
| rig-held-03 | 1,351 | 893 | 2 |

Across twelve instances the inventories contain 16,984 triangle and 11,160 vertex references, with zero degenerate owned triangles under the unchanged `1e-12 m²` twice-area threshold. Instance totals include repeated source rigs. Both hands use their explicitly mapped bone and actual descendants, with minimum deformation ownership one. They are complete hand-subtree surfaces, including fingers; anatomical palms and usable grip regions remain unreviewed. Every whole-hand inventory exceeds the native contact limit of 256 vertices, so explicit smaller patches are required rather than applying the whole hand or downsampling it.

All original attachments, neutral observations, rig profiles and directed placements remain byte-identical. The source rigs continue to share one known topology and two original meshes with synthetic proportion changes. These results add no independently authored rig generalization, new engine measurement or held-out animation trial.

## Replay and source checks

The build performs a complete reconstruction of each candidate and its reduction. A separate copied bundle also reproduces all twelve hands while Python reads from the original bundle, construction folder and original asset bindings are denied. The corrected harness explicitly guards `Path.open`, `builtins.open` and `io.open`, self-tests all three denial paths, observes all 84 required bundle reads among 105 distinct read paths, and records zero attempted original reads during verification. Original and copied bytes remain unchanged. Matching source methods and shared rig/skin kernels remain required; this is Python read-access testing rather than OS sandbox isolation.

The first harness guarded only `builtins.open` and `io.open`. Python 3.10's `Path.open` uses a cached accessor and bypassed those hooks, so its result is preserved but rejected as evidence for original-path denial. The corrected `v2` receipt binds that rejection and does not credit the earlier harness. Both harnesses used the same complete material bundle.

An isolated source snapshot passes **149 checks**, including **82 new checks** for the material API and portable inventory. Tiny fixtures verify material references against actual animated partner-contact sampling; the complete neutral fixtures verify relocation, source immutability, no invented hands when no hand-owned geometry exists, complete directed population and rejection of changed counts, identities, methods, settings, approval claims and candidate payloads even when their hashes are rebound. Windows/Linux CI includes the new source tests; the latest revision's CI outcome must be checked separately.

Local receipts, kept outside Git:

| Receipt | SHA256 |
|---|---|
| `reports/partner-material-source-check-v1/result.json` | `7c5c8e45b31d0ed94088a15c66a72d5a4157e16a3ce119657a96f39ea429a7dd` |
| `reports/release-partner-materials-v1/result.json` | `9139c0237f0bca25f5950afb106690c394e0eafbff0ccb27b2ce09ab45649f9b` |
| `reports/release-partner-material-portability-v2/result.json` | `f2d14ff6e2d90624c1debda4014a1ae79f94da8169bb186bf24a52d6b15b96dc` |

The [material authoring API](rig-material-patches-v1.md) supplies original triangle and skin-point references, preserves winding, measures posed triangles and rejects incompatible source versions. Anatomical review, explicit point correspondence, timing, motion generation/editing, contact/collision corrections and animated engine validation remain necessary for usable object and partner actions. Selected patches, approved contact targets, human ratings and cleanup records remain zero. All fourteen project release-evidence arrays remain empty.
