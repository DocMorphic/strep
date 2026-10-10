# Explicit central hand-material contact study

The new authored hand references produce passing position, normal and contact-side witnesses at all 62 original native hold poses, but the exported interpolated motion still fails contact-side and sliding-speed limits. This is a separately declared development fixture, not the original failing contact selection passing, anatomical palm approval or a finished motion. The original targets, object trajectory, hold interval and tolerances remain unchanged. Generation, inter-key contact, whole-body collision, physical forces, game-engine playback and human review remain separate gates.

## Reference selection

Inspect the source rig's complete strictly hand-owned surfaces: a vertex qualifies only when every positive skin influence belongs to the corresponding Hand subtree. Both hands contain 2,734 vertices and 5,428 complete original faces. Preserve original references, winding, topology and all eight influence slots. Pose only those 5,468 vertices at the source default-node reference matrices; forbid complete posed-mesh evaluation. The inspection stores orthographic projections and wrist-coordinate geometry. Bone names and weights identify deformation ownership, not anatomy. No face has all three vertices at least 95% directly Hand-weighted, so that threshold cannot supply a complete contact patch for this asset.

Freeze the source-coordinate selection before motion fitting: signed wrist X in [25, 65] mm, absolute Z at most 15 mm, negative Y and available incident winding normal Y at most -0.85. Each hand has 36 candidates. Select five distinct vertices by minimum total squared X/Z assignment to a signed 40-mm center and the original four reference-space neighbor offsets. Preserve their center/neighbor ordering. Explicit flattened vertex IDs are:

| Hand | Center, followed by four neighbors |
| --- | --- |
| Left | 6875, 14681, 6938, 6936, 6939 |
| Right | 11340, 11339, 11403, 11401, 3627 |

The saved selection also contains the original `[mesh node, primitive, vertex]` references. Only four contact-row vertex-reference arrays change; restoring them yields the original scene exactly. Rebind the existing normal policy to the new scene hash without changing its thresholds. Independent scalar replay checks all 5,468 reference positions, complete hand ownership/faces, all candidate filters, selected incident neighborhoods and the one-to-one assignment optimum with a finite dynamic program. Selection receipt SHA256: `adf2302b5bae8617edfffc3f0f8d00f3ec3fdf011033edb99c6da480f134db48`.

## Preserve the least-squares failure

Fit each source five-point patch freely by a proper rigid transform at every original native hold key, 60 through 121 inclusive (62 per hand). Recompute winding normals using each selected vertex's complete original incident triangles, including all neighboring vertices and influences. This requires 25 vertices/30 faces on the left and 24 vertices/27 faces on the right, not a complete deformed character. Preserve every original 5-mm position, 15-degree opposition and 0.5-mm backface allowance.

| Hand | Position passes | Normal passes | Side passes | Worst position | Worst opposition |
| --- | --- | --- | --- | --- | --- |
| Left | 62/62 | 0/62 | 0/62 | 3.4243 mm | 18.3757 degrees |
| Right | 62/62 | 0/62 | 0/62 | 3.4924 mm | 18.2494 degrees |

Preserve these failed least-squares fits. A small positional residual does not establish contact. The worst pairwise actor/target normal-angle gaps are 26.8166 and 27.8998 degrees; the older frozen-patch exclusion at a 30-degree necessary limit does not exclude these new selections. This observation is not a global feasibility proof.

Independent replay reconstructs scalar skin blending, complete incident cross sums, target transforms, all 620 point correspondences, position/opposition/side arithmetic and 124 proper-fit squared-objective lower bounds. The source parser, animation sampler and object interpolation remain shared. Receipt: `596ca7c532de02fa18cfee690bc1e6dc3fe3b2bdd993ff08cad7936b19ef408f`.

## Constrained proper transforms

Perturb the initial proper rigid fit around its fitted patch centroid with at most 20 degrees of rotation-vector norm and 5 mm of translation norm. Constrain all five points, winding normals and signed contact sides together; the object and contact targets stay fixed. Use SLSQP with at most 200 iterations, minimizing mean squared normalized point error plus 0.001 times squared normalized perturbation. The solver has explicit interior margins: 10 micrometers position/side, 0.01 degrees opposition and 0.001 normalized cap norm. Actual acceptance uses the unchanged original limits with no acceptance slack. Tiny negative solver interior slacks remain recorded rather than being treated as exact arithmetic feasibility.

Both hands pass all conditions at predeclared frames 60, 90 and 121. Independently replay all six candidates/30 correspondences with separately implemented Rodrigues rotations, proper transform composition, scalar contact arithmetic and cap checks. Receipt: `05a7445c6c7ce9114a2482a42f6922f6b51d85c7344f5bd458f524bd5104892b`. These are freely placed patch witnesses, not reachable character poses.

The same unchanged protocol then evaluates all 62 original native keys: **124/124 free hand transforms pass**. Independent replay checks all 620 correspondences. The bound original source neighborhoods are unchanged; the nonlinear optimizer itself is outside independence.

## Three-pose character pilot

Construct wrist targets from the six independently replayed free witnesses. Fit eight explicit arm joints with their existing 45-degree source-relative rotation-vector norm caps plus Spine1, Spine2 and Chest with 15-degree caps. Preserve every local translation, finger and other local transform. Wrist matching tolerances are 5 micrometers and 0.001 degrees; maximum solver iterations stay 200. Recompute actual skin positions and complete incident normals after fitting, without replacing them by the guide's rigid points.

All **three candidates** pass the original actual contact conditions and all eleven caps. Independent replay checks three candidate poses, 33 caps and 30 correspondences through separate Rodrigues rotations, recursive FK, scalar skin blending and incident cross sums. Protected locals/translations remain exact; foot world matrices differ by at most 4.45e-16. The source parser, native interpolation, skin preparation, object interpolation and original nonlinear solver remain shared or outside independence. This is sampled numerical contact evidence; artist caps do not establish anatomy or human quality.

The pilot receipt is `9266f747e759c0e00af4213743da39a5e13d93bfb3b67bedd84bbe321a6aa0c9`. The identical source-relative body protocol then covers **62/62 original native hold keys**, all passing the actual position/normal/side conditions and eleven joint caps. Independent replay checks **62 poses, 682 caps and 620 contact correspondences**; protected translations/local transforms remain exact and the maximum foot world-matrix difference is 5.56e-16. Receipt: `7fdc170007dabd2b2afbb396da82c23016d5a9a48b7d0c3a6ab073f35a9695d1`. This is a new authored fixture, not the old patch passing or complete motion approval.

## Exported interpolation exposes temporal failure

Export only the eleven edited rotation channels at keys 60–121 into a fresh diagnostic GLB. Append new output accessors, preserve the entire original binary prefix, prior accessors/samplers, mesh/skin data, every other channel and all outside-key quaternion values. The unchanged LINEAR quaternion interpolation is actually sampled after export. Keep the original contact interval, 5-mm position and 5-mm/s relative-speed limits, 15-degree opposition and 0.5-mm backface allowance.

Evaluate all **1,033 distinct original clock times per contact**: native and object keys, endpoints and twelve combinations of 30/60/120 Hz with 0/0.25/0.5/0.75 frame phase. All ten winding normals are available at all times. The complete 49-vertex/57-face incident neighborhood is evaluated, without whole-body collision queries.

| Contact | Worst position | Worst relative speed | Worst opposition | Minimum signed side | Surface samples passing |
| --- | --- | --- | --- | --- | --- |
| Left center | 2.1503 mm | 7.7149 mm/s | 8.2534 degrees | +0.2723 mm | 1033/1033 |
| Right center | 3.0177 mm | 21.0855 mm/s | 8.8656 degrees | +0.1979 mm | 1033/1033 |
| Left neighbors | 3.3833 mm | 7.8443 mm/s | 14.9963 degrees | -0.5195 mm | 981/1033 |
| Right neighbors | 3.5665 mm | 21.2041 mm/s | 14.9927 degrees | -0.5057 mm | 964/1033 |

Every row passes position, and every sampled opposition stays within 15 degrees. Both neighbor rows fail signed side between native poses; **all four contact rows fail relative speed**. The complete motion remains rejected. Independently replay all original clocks, **10,330 normal correspondences and 16,960 point velocity pairs**, topology/incident cross sums, reliability, contact pass arithmetic and source-preserving export. Native FK/interpolation, asset/accessor parsing and original pose solving remain shared/outside independence. Receipt: `5b310fa8c80bd2f2dbe6ef402527b6ab22aeb06603a0de7a264c10acd55ed723`.

Diagnostic GLB hash: `e20e32451701ace7f11fdc08ca4ba2498a367011bb89407ca6020d5964cb8d27`. It is a failed exported development clip, not admitted model guidance or an engine-tested asset. Preserve all outputs. Next address temporal coupling and an explicitly declared solver interior margin while retaining original acceptance limits; only then assess complete geometry and actual force consistency before the model-control comparison. No training admission follows from these local contact studies.

## Local evidence and resource scope

Ignored studies: `reports/hand-material-inspection-v1`, `central-hand-material-v1`, `central-hand-free-fit-v1`, `central-hand-constrained-fit-v1`, `central-hand-constrained-fit-v2`, `central-hand-torso-pilot-v1`, `central-hand-torso-hold-v1` and `central-hand-contact-clock-v1`. They retain source/input/method hashes, original references, raw observations, failed fits, independent replay receipts and owned resource traces. Generated GLBs, images and numerical archives are excluded from the public repo.

Scoped selected-surface/pose workers retain the existing 1,024 MiB plus 600 MiB reserve policy. Complete posed-body geometry retains 2,048 MiB plus 600 MiB. Resource replay establishes recorded admission/lifecycle policy only. All quality, release and training flags remain false; the single full-project goal stays active across broad actions, scenes/partners, rigs, edits/styles, transitions, engines and genuine human ratings/cleanup.


The complete hold producer/audit finish in **139.891 / 4.469 seconds** with **136 / 10** independently replayed resource observations. Export/clock producer/audit finish in **22.453 / 11.797 seconds** with **27 / 17** observations, all independently replayed. These resource receipts add no motion approval. Source inventory remains 436 Python modules / 41 Node suites; this continuation changes methodology/result documentation and runs ignored studies, not production source or its passing software-test scope.


Later continuation: [previous-pose fitting and interval selection](pose-continuation-v1.md) independently isolate interpolation drift and test the complete 62-key continuation curve. That curve still fails actual sliding/side conditions; the reusable source helper is numerical infrastructure, not a motion approval. The next nine-key insertion pilot and complete 135-key proposal are frozen but not executed.
