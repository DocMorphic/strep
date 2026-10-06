# Verify depth-restoration phases before selection

The depth-restoration solver previously accepted later `Solved` or `AlmostSolved` phases based on their status and finite coordinates. A complete retained model exposes the defect: the first phase is native-feasible, the second violates the requested native tolerance, and the third also exceeds the depth-priority lock. The final exported direction must be checked after trust/authoring projection before it can replace an earlier verified point.

`scripts/native_partner_depth_restore.py` now records each attempted phase and checks its complete point, original trust/certificate bounds, all original affine native norms, nonnegative depth/surface epigraphs, complete surface population and applicable priority locks. The native check uses the unchanged solver feasibility tolerance of `1e-9`; normalized depth/surface locks remain `1e-9`. Original caps/scales, contact/reference/edit/geometry limits and strict decoded acceptance remain unchanged. This is a numerical proposal check, not an exact floating-point, nonlinear, physical or asset-quality certificate.

An invalid primary phase returns no direction and `UnverifiedDepthPhase`. An invalid later phase keeps the last verified projected direction. The third phase runs only after a verified surface phase; an unverified surface optimum cannot become a new priority lock. Receipts include `selected_phase`, `phase_checks`, measured residuals and specific rejection reasons. A solver status alone cannot grant selection or approval.

## Regression tests

**52 focused CPU tests pass in 33.35 seconds, zero skips**: 15 existing depth-restoration cases, 12 new phase-selection cases, 13 complete job cases and 12 static-reference cases. Controlled solver outputs exercise depth/surface lock violations, underreported epigraphs, native failures, invalid points, trust violations, feasible later phases and fallback. Real v1/v2 jobs retain original references and perform model, solver, export and complete geometry checks. CI adds the new suite; hosted CI success is not claimed.

The first run has 50 passes and two failures: old assertions require phase three even when the new check rejects phase two. Those tests and the implementation remain archived. The ordering test now requires a verified second phase before phase three; the explicit third-phase failure test uses a genuinely feasible second point. The old trust-projection fixture also had an unrelated native violation; its test cap now isolates trust projection. Production caps remain unchanged. An indentation mistake while adapting a fault-injection test causes a separate retained collection failure; it starts no study. The final repaired suite passes.

## Matched complete-model comparison

This study reuses the exact [complete sixty-control model and independent replay](native-stored-pair-export-replay-v1.md), with all 29870 native norms, 276789 surface rows, 119942 equivalent rows, 156847 rational implications, 2856 depth witnesses and original limits intact. No guidance, Jacobian, witness population or model is rebuilt. Only the phase-selector implementation changes; all three old phase points and both new points remain archived.

| Phase in the old implementation | Status | Measured native excess | Normalized depth deficit | Reported depth epigraph |
| --- | --- | ---: | ---: | ---: |
| Depth | Solved | -3.148609e-6 | 0 | 5.427724e-12 |
| Surface | Solved | 4.430188e-9 | 9.830133e-10 | 9.825188e-10 |
| Minimum norm | AlmostSolved | 7.644165e-9 | 1.585393e-7 | 1.722940e-10 |

The new selector keeps the depth phase and rejects the surface phase for its native violation. The minimum-norm phase is not run. The first two solver points reproduce the old points byte-for-byte. The selected projected direction has zero modeled depth deficit and native margin approximately 3.149e-6; its complete affine surface excess is 2.352139, compared with the old final 2.342484. The soft surface improvement cannot override verified native constraints or depth priority.

Every fraction still receives an actual exported-motion and complete geometry audit:

| Fraction | Old stored motion failures | New stored motion failures | New contact failures | New penetration, mm | New triangle records | New contained vertices | New failed geometry samples |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 27 | 5 | 0 | 5.000779 | 30438 | 10 | 1602 |
| 0.5 | 0 | 10 | 0 | 5.032308 | 30424 | 28 | 1602 |
| 0.25 | 0 | 2 | 0 | 5.048398 | 30424 | 36 | 1600 |
| 0.125 | 3 | 3 | 0 | 5.056444 | 30436 | 40 | 1600 |

All original reference bounds pass. All new exports fail actual motion and complete geometry. The full step's depth improves slightly and its motion failures decrease, while the previously native-passing half/quarter steps no longer pass. This is a corrected selector and a retained failed motion comparison. The preceding native-passing diagnostic anchor stays intact; no new candidate replaces it or receives approval.

A separate consumer imports no changed phase selector, producer job/model, storage wrapper or curve proxy. It computes every attempted phase's native/depth/surface residual directly from the saved complete matrices, reproduces rejection reasons and the exact selected direction, and checks the first two points against the pre-change capture. Actual exports reuse the tested public export-observation API and existing native conditions, recomputing original rate arrays and all-native reference bounds. Every control, stored payload, decoded actor world and native observation matches. Geometry transport is checked, predicates are not independently recomputed. All workers exit zero after the retained test failures are corrected.

## Centered screen and bounded full-step repair

A read-only screen checks every fraction with the unchanged stored-curve proxy and original native conditions. All four centered nonlinear proposals pass, including contacts; their actual Float32 exports retain the motion failures above. No geometry, Jacobian or model is rebuilt by this screen.

The existing finite one-neighbor search therefore checks the full step at fixed continuous controls under the original one-step/64-component envelope and eight-stage/32-probe budget. It tests eight neighbors across nine retained actual probes: native failure counts are **5 → 5 → 3 → 2 → 1 → 1 → 1 → 3 → 0**. Six additional component choices bring the list from twenty to twenty-six. Every original motion/contact/reference condition passes at the final stored probe; failed probes remain. Maximum original-reference displacement is approximately 3.398857 mm for A and 3.427320 mm for B, with maximum edited rotation below 0.453 degrees, against unchanged thirty-millimetre/five-degree bounds.

Complete final geometry exactly matches the raw full-step score: **5.00077899156606 mm** penetration, **30438** triangle records, **10** contained vertices and **1602** failed samples. The candidate still fails the five-millimetre depth and crossing conditions. Compared with the preceding native-passing half-step anchor, depth and containment improve while crossing and failed-sample counts worsen. This is an unapproved diagnostic result, not a motion-quality success.

Two separate appended index6 clips preserve all six source animations and the original binary prefixes. Their native worlds match the final stored probe. A separate consumer imports no search/storage/job/proxy APIs and manually verifies all nine probe payloads and native observations, original rate/reference limits and both complete appended-library worlds. All retained probes and 29870 native conditions are replayed at all 1707 times; geometry transport is verified without reimplementing predicates. Both workers exit zero.

A separately pinned next diagnostic anchor and request change only controls, stored files and the twenty-six component choices. The original sources, static references, rate arrays, contacts, geometry/edit limits and settings remain. Its constructor repeats complete native/reference checks. All preceding anchors remain intact; no animation is automatically selected or approved. Next rebuild fresh guidance at this verified native-feasible stored anchor and measure the remaining depth/crossing failures. Do not infer real motion quality from the improved affine priority checks. These are generated cube-skin development fixtures, not production humanoid or broad partner-action evidence. No new inference/training, rendering/GPU, engine, physics, animator rating or cleanup-time evidence is claimed. All fourteen release evidence arrays remain empty and the full-project goal stays active.

Raw studies, assets, observations, drivers and failures remain ignored. Receipt SHA256 identities:

- Pre-change phase capture: `ff1c69b49d4e33b3f6f069681844bb87e28c08ea70bc20b6868bfc91a2233bbe`.
- Matched changed-selector study: `2a846da94fed86b275d702b5fe9c681ff8ebb787415d955a1e6643649e698b75`.
- Independent phase and complete export replay: `ca98951b95d593b48768cdb668464f6676dab584a392ee4cb8140b8eda6d5c44`.
- Centered nonlinear failure screen: `835ae135487ce09e554c7c38be5e2c6010f9a28eb28011222522951250afba58`.
- Finite full-step stored repair: `c8e9d65f86c1b36725cb6cb317600f2d0ef66c0f991b404be0f16ae836be7e75`.
- Complete saved-key/native/reference/library replay: `16a24914acfcdf6dc8ec3182cbb90d8c4515b9c2a9cc3e78f90cd4095563c1de`.
- Next diagnostic anchor with unchanged original limits: `3178dd9dafc71020b3f8c86a7320e96faa0a0d6e58d8d503572fd5a2a47dae84`.
