# Torso-assisted pose fit and interpolated contact failures

This is a development fixture on one SOMA77 actor and an explicitly authored sphere proxy named “box”. It is not verified rectangular-box lifting, a new Kimodo inference result, or release approval. Original contact failures remain intact.

## Reach and authored pose fitting

The earlier Chest-centered outer bound included an immovable Chest-to-Shoulder link as freely orientable and excluded none of 124 desired wrist targets. A stronger diagnostic anchors at each Shoulder, whose position cannot change in the eight-arm-joint experiment. It verifies the actual Shoulder → Arm → ForeArm → Hand parent chain and absence of edited ancestors. The same exact rational outward-rounded chain test excludes **22/62 left and 58/62 right wrist targets**, including the original 0.5 mm wrist tolerance. This proves those derived wrist goals exceed the fixed-pivot chain’s outer reach; it does not exclude global human reach or every pose satisfying only 5 mm skin contacts. Independent replay covers 124 target inequalities and 372 link bounds; receipt SHA256: `84c84082d8f2965a9970c0974ae60f683cbfc938301190c7261445499c574fa3`.

The separate torso-assisted experiment retains the original eight arm-joint 45° source-relative rotation-norm caps and adds explicit **15° artist-chosen caps on Spine1, Spine2 and Chest**. All local translations, the original root/legs, finger rotations and other local rotations remain protected. These caps constrain edits; they are not validated anatomical limits. Object trajectories, ten skin-point correspondences, 5 mm contact positions, 0.5 mm wrist positions and 0.25° wrist rotations remain unchanged.

The existing bounded rotation-norm fitter first passes all three preselected diagnostic keys, then **all 62 native hold keys (60–121)**: both hand-point positions and both derived wrist goals pass at every key. Worst skin-point error is **1.06286 mm**. The full attempt is stopped by the original RAM-floor guard after saving 60 keys. A fresh, hash-bound resume reconstructs those 60 saved rotation-vector solutions, replays point/wrist errors and source caps, and solves only keys 120 and 121. The interrupted attempt and checkpoint are retained.

Independent replay checks 620 skin points, 682 per-joint caps, protected local rotations, exact outside-hold guide arrays and root tracks. Maximum original-foot coordinate difference is **7.42 nanometres**; maximum exported float32 point-error replay difference is **45.39 nanometres**. Pose-guide SHA256: `b88537f3aef1cec8de946608df589fc54d86af24bf1bb0cb1630c01d362049a2`; independent receipt: `605c3d838a7d5d7374a733126004413a11f3fe5b9584dd36828773d02f445bf9`. These are pose checks, not motion-quality checks.

## Original contact clock and surface assessment

A separate diagnostic GLB copies the source document and complete original binary prefix, then appends outputs for only the eleven edited rotation channels. It preserves original key times, LINEAR quaternion interpolation, all unedited channels, original mesh/skin/inverse-bind payloads and exact quaternion values outside keys 60–121. The hold boundaries still need transition work; this file is an authored pose-guide diagnostic, not a finished clip.

The point audit retains every original contact-clock sample: both exact endpoints, native keys and the predeclared 30/60/120 Hz populations at offsets 0/0.25/0.5/0.75 frames. Each contact has **1,033 unique samples**. Normals use all original incident faces for each of the ten selected vertices: **42 neighborhood vertices and 48 faces**, with all skin influences. This is a scoped point/neighborhood audit. No complete posed body, other triangles, whole-body collision, force balance, engine playback or continuous-motion claim is evaluated.

| Contact | Worst position (mm) | Worst relative speed (mm/s) | Worst normal opposition (°) | Minimum signed side (mm) |
| --- | ---: | ---: | ---: | ---: |
| Left center | 0.70315 | 5.54416 | 0.76548 | −0.67969 |
| Right center | 0.70611 | 4.81190 | 0.76034 | −0.68506 |
| Left four neighbors | 1.07722 | 5.72485 | 32.49932 | −0.56202 |
| Right four neighbors | 1.08279 | 5.01206 | 32.64414 | −0.58015 |

All position populations pass the unchanged **5 mm** limit. Three of four contacts fail the **5 mm/s** relative-speed limit; only the right center passes both position and speed. All four surface conditions fail the unchanged **15°** opposition / **0.5 mm** backface allowance. All 10,330 normal observations are available, so missing normals do not explain the failures. The center normals face appropriately, but their signed sides exceed the allowed backface depth. Neighbor normals additionally disagree with the target surface.

Independent replay verifies source/export preservation, all original clocks, object transforms, point errors, **16,960 velocity point pairs**, complete incident topology, cross sums, normal reliability, opposition, sides and pass decisions. Shared glTF parsing, asset/skin loading, native FK/interpolation and original pose solving remain outside independence. Receipt SHA256: `7d12119286899718211a8de6d3c06a40070c6cd5bd3fcbd6d9d42a572c278b7d`; diagnostic GLB: `4f9cff621eff67245e41aeb2c833a255517d513a4dee891d7a21f897ae4bcb5c`.

## Frozen normal-shape diagnostic

A proper rigid rotation preserves every pairwise normal angle. If two corresponding normal errors must each be at most 15°, spherical triangle inequality requires the actor/target pair-angle difference to be at most **30°**. Across all ten pairs of the five points on each hand, the worst pair-angle gap at every sample is at least **52.92210° left / 52.89707° right**. Thus a common rotation of these frozen sampled normals cannot satisfy all five target normals at any of the 1,033 times on either hand. Scalar replay covers **20,660 pair comparisons** (receipt `453dbf3391d36281384160fd225bd5976cb7c1db0cb6f6cbb08e41dfd2a6cbd2`); this is a floating numerical diagnostic with a 1e−7° exclusion margin, not an exact rational proof or an exclusion of articulated skin deformation.

Actual source weights show every selected point is predominantly influenced by the corresponding **Pinky1** joint (approximately 80.95–97.69%), with smaller Hand/Ring1 and occasional Index1/Middle1 influences. Calling these points a palm would be unsupported. Additional finger articulation or a separately declared material-contact selection can alter the patch; this diagnostic does not prove those approaches impossible. Any new selection must preserve this failed version, record its source topology and point ordering, and be evaluated as a new authored fixture rather than counted as an original failure passing.

## Resource scope and remaining work

The scoped joint/ten-point/incident-neighborhood producer and audit use the existing **1,024 MiB + 600 MiB reserve** policy. They complete in 8.594 s and 1.125 s, with 137.61 MB and 93.58 MB recorded process-tree peaks. Their 26 and seven resource observations independently replay. The scalar normal-shape replay uses 512 MiB + the same reserve; 28 observations replay. Full skin/body geometry remains subject to **2,048 MiB + 600 MiB reserve**, regardless of these smaller measured peaks.

The next experiment must address declared contact material/finger shape, backface offsets and temporal drift, then assess full-body geometry and original physical conditions. No wrist-guided generation is admitted from the present guide. No model training is justified solely by these authored-contact failures. Anatomical plausibility, grip strength, transitions, held-out objects/rigs, actual game-engine playback and genuine developer/animator ratings and timed cleanup remain unverified. All quality, training and release approval flags remain false.

Local immutable evidence is under `reports/equatorial-fixed-pivot-reach-v1`, `reports/equatorial-torso-guide-v1`, `reports/equatorial-torso-hold-v1`, `reports/equatorial-torso-hold-resume-v1`, `reports/equatorial-torso-contact-clock-v1` and `reports/equatorial-torso-normal-shape-v1`; each retains worker/method snapshots and resource records. Generated payloads are intentionally excluded from the public repository.

Later continuation: the [direct articulated patch study and portable point-attribution command](contact-point-attribution-v1.md) test actual incident-surface constraints with eight finger-base joints. Both predeclared three-key formulations still fail; independently replayed candidates and retained guides stay unapproved. New authored selections can now inspect actual bone weights before choosing material contacts.
