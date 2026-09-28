# Stance correction and character transfer — 2026-09-24

The session goal is complete. The same stance-correction search improves all five reviewed run loops while preserving the existing loop and regression screens. The best result is transferred to the licensed CesiumMan character and exported as an animated, skinned GLB with before/after clips. Raw generation files and the previous reviewed study are unchanged.

- Character review: [local viewer](http://127.0.0.1:8767/reports/stance-character-v3/comparison.html), or `reports/stance-character-v3/comparison.html` through a project-root HTTP server.
- All five source comparisons: [local viewer](http://127.0.0.1:8767/reports/stance-correction-v1/comparison.html).
- Source NPZ/BVH, every candidate, and metrics: `reports/stance-correction-v1/`.
- Character GLB, measurements, contact sidecar, and attribution: `reports/stance-character-v3/`.

These results establish technical progress on this five-seed study. They do not establish independent foot-contact correctness, animator-approved realism, held-out generalization, or game-engine acceptance.

## Results on the source skeleton

“Before” here is the frozen deterministic loop correction, not raw model output. Speeds use the exact same inherited contact labels before and after; no contacts are removed or relabeled. All values are measured over repeated cycles with root displacement accumulated.

| Seed | Contact speed p95 before → after, cm/s | Corrected loop prediction RMS, cm | Largest joint change, cm | Largest local rotation change | Outcome |
| --- | ---: | ---: | ---: | ---: | --- |
| 11 | 32.30 → 2.14 | 1.65 | 1.26 | 3.48° | Passes loop + regression + distortion screens |
| 22 | 9.15 → 3.82 | 1.24 | 0.36 | 1.17° | Passes |
| 33 | 35.05 → 6.21 | 1.72 | 3.37 | 9.63° | Passes |
| 44 | 29.78 → 3.76 | 1.96 | 1.23 | 2.45° | Passes |
| 55 | 18.35 → 5.16 | 1.36 | 0.66 | 0.85° | Passes |

The prior study had two of five combined passes; this study has five of five under the same original numerical gates, plus new distortion limits. The broader realism rubric still requires independent stance measurements. In particular, predicted-contact p95 for seeds 33 and 55 remains above 5 cm/s; a proxy improvement is not a pass of an independently annotated stance gate.

## Method and fixed constraints

`correct_stance.py` solves a periodic quadratic objective for horizontal offsets of each foot. It penalizes movement between consecutive predicted-contact samples, offset magnitude, and cyclic second differences. The wrap interval explicitly includes forward root travel. A two-bone IK solve applies these offsets while conserving thigh/shin lengths, preserving ankle world orientation, and keeping the knee on its original bend side. Horizontal root motion and all contact labels remain exactly unchanged.

The same 27 configurations run on every seed. `benchmarks/stance-correction-v1.json` fixes the search and additional distortion budgets: at most 6 cm joint displacement, 20° local rotation change, 1 mm extra constant ground lift, and at least 1% contact-speed improvement. The original acceptance thresholds and original three-reference sliding-regression limits are reused unchanged. All candidates are saved, including rejected candidates; the winner minimizes predicted sliding among feasible results.

Seed 33 has a maximum unreachable target clamp of 4.90 mm, reflecting a nearly extended leg. That residual is reported rather than stretching a bone. Maximum extra constant floor lift is below 0.0002 mm across the five seeds. Joint-floor depth does not worsen; this source-stage measure does not inspect a mesh.

## Character transfer and remaining defects

Seed 11 was selected because it has the lowest accepted source contact-speed p95. The explicit 19-joint mapping recovers bind transforms from the original inverse-bind matrices, aligns bone directions to SOMA's neutral pose, and transfers global orientations into the target hierarchy. Root travel is scaled by the mean left/right leg-length ratio, **0.633**. Fingers, toe ends, and some spine/shoulder detail have no direct counterparts. The source mesh, weights, materials, textures, and license are retained; only the derived copy receives new animation.

The animated GLB contains two named four-cycle clips, before and after stance correction, with 97 keys including the terminal sample. Each cycle travels **1.473 m**, for **5.891 m** over four cycles. Playback stops after the fourth cycle; a manual restart resets the world position. Contact predictions are in `contacts.json`, not standard glTF animation channels.

On the character, the ankle/toe-base contact-speed proxy improves from **16.68 to 5.12 cm/s**. Its joint coverage differs from the six-point source metric. The common constant vertical alignment for both clips is **7.87 cm**. This corrects the gross height mismatch but does not solve target-rig contacts:

- Lowest foot vertices rise as much as **1.68 cm** during predicted support. The medians are approximately 0.65 cm left and 0.50 cm right.
- Keyframe vertices clear the floor within numerical tolerance, but half-frame interpolation reveals up to **2.03 mm penetration** after correction, compared with 1.77 mm before.
- The target 19-joint loop prediction RMS is 1.43 cm after transfer, versus 1.40 cm before. This is a separate diagnostic with different joint coverage from the 77-joint source screen.

These findings motivate target-rig foot placement rather than another source-model training run. No mesh self-collision, independent support annotation, animator rating, or engine import is claimed. The viewer was inspected from side/front/three-quarter views at support and cycle-boundary frames; restart and end-of-playback behavior were checked. This is a developer review, not a blind human evaluation.

## Verification

- **24 tests pass**: the existing pipeline tests plus cyclic contact correction, absent-contact behavior, IK reach/bone-length preservation, rotation antipodes, source preservation, GLB accessor layout, and inverse-bind skinning. Four warnings are upstream TorchScript deprecations.
- A complete second stance run exactly reproduces corrected arrays, every candidate metric, and all winners on this machine. Source labels, horizontal root paths, original raw hashes, and the frozen baseline summary were checked.
- All five BVH exports pass full-joint round-trip checks; maximum error is below 0.0000045 m, and accepted loop screens survive export.
- Both character clips were read back from the GLB and CPU-skinned at every exported key. Maximum vertex round-trip error is below 0.0000014 m. Root travel error is below 0.00000021 m; target bone lengths remain fixed.
- A second character transfer produces a byte-identical GLB and exactly equal skin-validation arrays.
- The Khronos glTF validator reports **0 errors, 1 warning**. The same non-root skinned-mesh warning occurs in the original CesiumMan asset. The 76 informational messages concern retained unused original data. The actual exported GLB also loads and animates in the locally bundled Three.js viewer.
- Mesh-floor clearance was sampled at every key and midpoint using quaternion interpolation. This is a sampled check, not continuous-time collision proof.

The transfer implements the [Khronos glTF transform and skinning conventions](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html). Three.js 0.186.1 and glTF validator 2.0.0-dev.3.10 are pinned under `assets/viewer/`; rendering and validation need no remote resources after setup.

## Reproduce

From `C:\wassup\strep`, use fresh output directories:

```powershell
.venv\Scripts\python.exe scripts\correct_stance.py --output reports\stance-new
.venv\Scripts\python.exe scripts\correct_stance.py --output reports\stance-repeat
.venv\Scripts\python.exe scripts\verify_stance_study.py reports\stance-new reports\stance-repeat
.venv\Scripts\python.exe scripts\retarget_cesium.py --study reports\stance-new --output reports\character-new
.venv\Scripts\python.exe scripts\measure_character.py reports\character-new
node scripts\validate_character.mjs reports\character-new\cesium-run-comparison.glb
.venv\Scripts\python.exe scripts\build_stance_previews.py --study reports\stance-new --character reports\character-new
.venv\Scripts\python.exe -m pytest tests -q
```

To serve locally if the existing server is stopped:

```powershell
.venv\Scripts\python.exe -m http.server 8767 --bind 127.0.0.1
```

Open the new comparison path under that server. No model inference, training, downloads, or credentials are needed by the correction/transfer stages. The original motion still carries the experimental streamed-encoder qualification from the baseline study.

Failed transfer attempts `stance-character-v1` and `v2`, and their logs, are retained. They failed before successful export validation due to a source-joint name mismatch and an array-axis bug; `v3` contains the corrected, tested implementation's successful output.

## Next milestone

Apply stance-aware placement on the target rig, addressing both support height and interpolation penetration while preserving the source improvements. Then obtain independent support annotations and animator review, and choose a game engine for import validation. The broader run-to-roll, box, partner, held-out rig, and clip-editing goals remain separate work.
