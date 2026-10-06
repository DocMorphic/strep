# Ninety-control wrist correction and stored-value repair

The [explicit wrist baseline](pair-hand-articulation-baseline-v1.md) now has a completed correction study and independent replay. The added controls do not resolve this scene's geometry. A bounded stored-value repair recovers motion feasibility, while every collision failure remains visible. Neither this local trial nor its failure proves that the complete permitted articulation range is infeasible.

## Complete model and phase decisions

The unchanged public v2 correction command starts from the pinned ninety-control baseline, retaining all original source/reference/rate/contact/edit/geometry contracts. The full model has **30450 native norms**, **276815 scalar surface rows** and **2873 depth witnesses**. Exact affine reduction retains **120212** rows with **156603** verified dominance implications; no original surface condition is dropped from the proof.

Depth and surface phases return `Solved`. The minimum-norm phase returns `MaxTime` and is rejected; the last accepted surface direction remains. Primary native margin is about **3.758345e-6**. The selected affine native excess **2.829683e-10** is within the unchanged 1e-9 numerical phase tolerance, but is positive. Full affine surface excess decreases **2.419333023283 → 2.331835417921** and predicted depth deficit is about 9.078557e-10 within its original lock. These are local numerical guidance results, not actual stored-motion or geometry approval.

Every requested raw export receives all **1707 native** and **1673 geometry** samples:

| Fraction | Stored failures | Centered failures | Contact failures | Penetration, mm | Triangle records | Contained vertices | Failed geometry samples |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1.0 | 7 | 4 | 0 | 5.008569 | 30519 | 2 | 1613 |
| 0.5 | 9 | 1 | 0 | 5.002267 | 30513 | 2 | 1608 |
| 0.25 | 3 | 0 | 0 | 5.000720 | 30437 | 4 | 1605 |
| 0.125 | 9 | 0 | 0 | 5.000616 | 30438 | 5 | 1603 |

All original-reference bounds pass. Every raw native and complete geometry result fails. The full step also fails centered nonlinear motion conditions; it cannot be fixed by storage choices alone. None of these raw fractions is selected or approved. The unchanged external penetration limit is five millimetres, and surface crossings remain failures.

The separate complete-model consumer imports no job/model/proxy/guard/reduction/solver/static-preparation implementation. It independently reconstructs stored-key offsets and continuous proposal worlds, exactly reproduces every original native norm and Jacobian entry, verifies every guard and rational surface implication, and checks all **ninety** scalar derivative columns with maximum difference **4.440892098500626e-13**. Original rates/static references, all raw payloads/worlds/native observations, centered failure counts and reference bounds match. Geometry archives, clocks, limits and scores are verified as transport; collision predicates are not independently reimplemented.

## Fixed-control storage repair

The public repair command chooses the eighth step by its lowest complete geometry score among centered-native/reference-passing fractions. Controls stay fixed. Ten finite absolute-neighbor probes plus the retained start progress through native failure counts **9 → 7 → 6 → 6 → 6 → 3 → 3 → 2 → 3 → 3 → 0**. Five additional absolute choices increase the stored correction list from 26 to 31. Every contact condition and original rate/edit/reference bound remains unchanged.

The final stored candidate passes all native/contact/reference conditions. Original-reference joint displacement is **3.329541 mm** for A and **3.346496 mm** for B. Node6 changes are about 0.456058/0.461684 degrees, node7 0.271945/0.271705 degrees, and node8 0.021651 degrees per actor, within the original five-degree bounds. This is one small local step, not a search of that entire range.

Complete final geometry is identical to the raw eighth-step score: **5.000616339347013 mm** penetration, **30438** triangle records, **5** contained vertices and **1603** failed samples. Native storage repair has not solved collision or nonlinear guidance error. Two appended index7 diagnostic clips retain all seven original source animations, binary prefixes and static scene metadata. The selected production asset is unchanged.

A second consumer imports no repair/search/storage/job/model/proxy/static-preparation implementation. Manual absolute choices reproduce all eleven probe payloads, controls, decoded worlds and native residuals. Original rates, Float64 static references and every native-time reference bound match; both appended libraries and complete native worlds are exact. Geometry transport is verified, without independently recomputing predicates.

A fresh ninety-control request changes only anchor controls/files/corrections to this independently replayed diagnostic. It passes actual native and original-reference preflight; all source/reference/static/rate/contact/edit/geometry/settings fields are retained. The original model, source, failed probes and prior candidates remain immutable. No fresh model is rebuilt or geometry rerun merely to pin this anchor.

The repair command also rejects nested output destinations before directory creation. Four focused v1/v2 tests pass in **16.52 seconds**, zero skips, covering complete source-study inventory/hash preservation on rejection and successful separate-output repair/library preservation. This guard is outside the unchanged correction-model implementation. Hosted CI success is not claimed.

The producer, complete-model replay, repair, repaired-key replay and anchor preflight all exit zero. Numerical pipeline completion does not approve animation quality. Next revisit local guidance and separation reachability from the retained motion-feasible anchor, preserving every original limit and failed result, and continue broader action/rig/object/partner evaluation. These generated cube-skin fixtures supply no production humanoid realism, engine/physics, new motion-model inference/training, human ratings or cleanup-time evidence. All fourteen release evidence arrays remain empty; the single full-project goal stays active.

Immutable ignored local receipt SHA256 identities:

- Full correction: `6c25a09f2a9045461406fd7812b2a2cdd501cbd55380b6393eeba09b624fbde4`.
- Complete model/export replay: `ac9acaf0c948b1598ff03d7a0eec4163384a7636e63bf7306dc6a77a9a2de161`.
- Fixed-control repair: `3ddb9915e4a82a5212372fcf8b9dec2674c58e2d4a4338e60556104c17eea196`.
- Every-probe/library replay: `31cb24eb249041e3d4c9558ed57b20f97c92b386f0cd710eaee5fb9e87960864`.
- Next-anchor preflight: `d2e133d862f4e3c6a7caf2d2ce73bb4e51742feeaca2855db795a1b27365e520`.
- Next request: `2a9c5fc35dc85e18d17399a828084efc4f5fd46bf3ac2ed2bd04ee3b04f01da0`.
