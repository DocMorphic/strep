# Support-contact fitting experiment

2026-09-26. A separate clip-wide correction reduces contact gaps and sharp edits on some getting-up motions. It is **not a replacement for body-contact-v1**: all four experimental clips remain flagged, and three introduce new flags. The original 30-clip study remains unchanged (24 numerical passes, six flagged).

## Review in Studio

Open http://127.0.0.1:8768/studio and select **Support fitting · experimental**. Compare **Support candidate**, **Body baseline v1**, **Hands/feet baseline** and **Raw generation** at the same frame. Each version has its own files and measurements. Inspector → **Candidate support sequence** lists inferred low/slow intervals; clicking one jumps to its first frame. These intervals are geometric hypotheses, not annotated supports or gameplay events. Model foot-contact labels remain unchanged and are exported separately.

## Method and scope

The pass infers sustained low/slow patches from the unchanged hand/foot baseline across hands, feet, torso, head, knees and elbows. It retains runs of at least three intervals, fades weights with a two-frame Gaussian, and fits root height plus 20 body-joint rotation tracks over the entire clip using local CPU L-BFGS. It penalizes sampled surface penetration, moving support-target error, added joint acceleration, peak added velocity and support sliding. Targets follow the original moving patch: this does not claim to eliminate all existing skating or infer force-bearing supports. Every skin calculation retains eight weights.

The algorithm receives no action names. The experiment selects existing clips with body-support-gap or added-speed flags, which selects four get-ups here. The other 26 motions are deliberately not edited; their hashes are checked. This is regression preservation by leaving them alone, not evidence that the optimizer generalizes across actions.

The optimization uses a fixed near-floor vertex sample, then independently checks all 18,056 vertices at every keyframe and interpolated halfway pose. Root XZ/heading, skeleton bone lengths, timing, frame count and model foot-contact labels are preserved. Facial, finger and toe local rotations receive only numerical normalization. Exported root tracks contain actual corrected coordinates; stale network smooth-root features are omitted.

Root lift and rotation limits are **soft penalties**, not hard guarantees. Seed 55 lowers the root about 0.013 mm below its baseline and is explicitly flagged by an added hard post-check. Do not hide this by increasing tolerance. The next solver revision should enforce bounds in its parameterization. There are no anatomical joint limits, self-collision, force/balance constraints, object/partner interactions, or certified contact labels.

## Measurements

Peak added speed measures the correction's change to joint velocity, not the character's absolute running speed. Flag counts are diagnostic summaries, not a quality score; fewer flags can coexist with a new serious failure.

| Seed | Flags before → after | Peak added speed (m/s) | Key depth (mm) | Halfway depth (mm) | Outcome |
|---|---:|---:|---:|---:|---|
| 11 | 8 → 1 | 1.559 → 1.200 | 3.02 | 3.02 | Improved; still flagged |
| 22 | 4 → 2 | 1.568 → 1.000 | 0.00 | 0.00 | New regressions |
| 55 | 7 → 8 | 1.069 → 0.830 | 2.06 | 1.79 | New regressions |
| 77 | 6 → 4 | 0.932 → 0.700 | 8.15 | 7.65 | New regressions |

Seed 11's p95 fixed-patch gaps improved: torso 7.31 → 1.67 cm, head 7.13 → 1.96 cm, left knee 6.43 → 2.56 cm, left elbow 14.56 → 4.33 cm, right elbow 6.64 → 1.90 cm. Some nonzero gaps fall within the existing *relative* regression tolerances; this is not absolute contact certification. The left-hand gap flag remains. Its floor depth worsens from 0.62 to 3.02 mm, though it stays inside the unchanged 1 cm numerical penetration gate.

Seed 22 adds a left-hand gap flag. Seed 55 adds hand/foot gaps, foot/head sliding and the root-bound violation. Seed 77 adds right-hand sliding and has 8.15 mm maximum keyframe penetration. All candidates and failures are preserved. None is promoted to the default correction or labeled animation-ready.

## Verification and reproducibility

- 81 project tests pass; four upstream Torch JIT deprecation warnings remain.
- Four new candidate GLBs plus four copied limb-baseline GLBs validate with zero errors/warnings.
- Candidate GLB poses/surface depths are checked at every frame, all eight skin weights are verified, and BVH roundtrips pass.
- Independent artifact verification checks all hashes, ZIP content, exact copies of raw/limb/body-baseline versions, root tracks, rigid bones (maximum error below 0.00000033 m), rotations and unchanged contact channels.
- Seed 11 reproduces exactly against a separate run of the same final solver. Other seeds were not rerun for bitwise determinism.
- All four seeds were already seen. This is a development-set experiment, not held-out evaluation. No model training or new model generation took place.
- No independent animator ratings, cleanup-time trial, physics validation or game-engine import has been completed.

Commands from the project root (the runner refuses to overwrite its output folder):

```powershell
.venv\Scripts\python.exe scripts/run_support_contact.py
.venv\Scripts\python.exe scripts/verify_support_study.py
node scripts/validate_body_exports.mjs reports/support-contact-v1
.venv\Scripts\python.exe -m pytest tests -q
.venv\Scripts\python.exe scripts/build_desktop.py
```

Configuration and solver hashes were frozen before the four-clip batch in `benchmarks/support-contact-v1-freeze.json`. Exploratory seed-11 results remain in `reports/support-contact-prototype` and `reports/support-contact-prototype-v2`. The first prototype reduced gaps but introduced sliding; it is not the Studio candidate. Verification uses the second prototype for the exact-repeat check.

## Research basis and next decision

[Kovar, Schreiner and Gleicher](https://research.cs.wisc.edu/graphics/Gallery/kovar.vol/Cleanup/) identify contact-boundary discontinuities, near-straight-limb popping and root adjustment as linked editing problems. Their method uses explicit constraints and permits small limb-length changes; this experiment instead preserves rigid bones and optimizes soft geometric targets. It is not a reproduction of their method.

The current failure is conflicting or incorrect support hypotheses: forcing every low/slow region towards the floor can trade elbow/knee improvement for hand/foot failures. Next: expose editable support intervals and contact targets, enforce hard edit budgets, and compare annotated versus inferred contacts before further tuning. Keep the current evaluation thresholds and all previous versions. Broader object/partner authoring remains part of the product scope; this experiment does not solve it.
