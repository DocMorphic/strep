# Contact correction across loop boundaries — 2026-09-26

Studio contact edits now recognize a saved periodic timeline. They fit one ring of phases, keep the original cycle placement, and derive the terminal pose from phase zero. The output includes a corrected single cycle, three-cycle preview, root/contact/event tracks and Godot runtime files. This establishes a periodic editing path; it does not make the tested motions release-ready.

## Solver and limits

`rig_periodic_contact.py` extends the existing target-mesh fitter. Each phase has bounded pelvis translation and local joint rotation corrections. Alternating forward/backward sweeps consider both neighboring corrections. At the seam, root shifts are transformed by the cycle yaw; local rotation corrections remain in their joint frames. Neighbor root-vector and rotation-vector distances have explicit Euclidean limits. A feasible line-segment safeguard retains these bounds, and independent decoded-GLB checks measure actual rotation geodesics and pelvis changes.

Bounded least squares handles ordinary phase proposals. SLSQP is used only when a neighbor limit clips the proposal substantially, allowing motion along the constraint boundary. The existing `max_nfev` value bounds least-squares evaluations and the fallback's iterations; actual evaluations and fallback usage are recorded. There are at most six sweeps. Small parameter change is a stopping rule, not a proof of stationarity, global optimality or feasibility of all requested contacts.

The terminal sample is constructed by applying the original cycle transform to corrected phase zero. Original arm/torso and other unedited local transforms remain unchanged. The implementation currently requires a single period plus terminal sample, rigid yaw/horizontal cycle placement and fully skinned geometry under the mapped pelvis. Contact targets at the terminal sample are transformed back into phase-zero constraints. Contradictory endpoint targets produce an explicit lower-bound diagnostic and rejection flag.

The final exporter records actual compiled phase constraints at every wrap, including endpoint-only targets. Original input intervals remain separately available. A synthetic constant-pose regression exercises terminal-only constraints through fitting, GLB export, repeated targets and runtime metadata. The real v3 studies below preceded this final sidecar refinement; their immutable source snapshots remain unchanged.

## Retained experiments and quality results

`run_periodic_contact_study.py` submits real Studio jobs on two previously failed loop candidates. It uses inherited authored targets only where source weight is one. Partial blend targets stay in the preserved input review and are independently measured; they are not silently declared solved.

The first projected-direction solver is retained in `reports/periodic-contact-v1`. It reduced imported locomotion floor depth to 7.03 mm but stalled at a neighbor rotation limit. The v2 experiment used SLSQP on every phase. After observing the live worker's cost and progress, it was deliberately stopped at the first sweep; its partial state and logs are retained. It is not a completed quality result. The final hybrid study is `reports/periodic-contact-v3`:

| Measurement | Turning wave, before → after | Imported locomotion, before → after |
| --- | --- | --- |
| Maximum sampled floor depth | 3.01 → 2.88 mm | 15.32 → 6.34 mm |
| Maximum half-frame floor depth | 3.01 → 2.73 mm | 14.09 → 6.11 mm |
| All positive source-target sliding, p95 | 518 → 529 mm/s | 10.91 → 0.563 mm/s |
| All positive source-target error, maximum | 86.76 → 89.41 mm | 4.20 → 2.12 mm |
| Explicit fitted target error, maximum | 0.741 mm | 2.12 mm |

Turning job: `20260926-224821-4b3059cc`, 61 single/181 repeated samples. Its explicit fitting screens pass, but sliding through the return blend gets worse. It is **not an approved motion**. Locomotion job: `20260926-225025-7cb4f8f4`, 21/61 samples. Two sampled frames still fail the unchanged 5 mm floor limit, so Studio labels it **rejected**. Its sliding figure covers only four annotated velocity steps, not the whole support sequence. Neither trial establishes general animation quality.

The independent ambiguity diagnostic finds 30 turning-wave patch/frame cases with competing positive-weight source targets whose separation makes simultaneous 20 mm hard-target accuracy impossible. Blend weights describe source contributions, not two physically confirmed supports. These intervals need reviewed contact intent or transition regeneration, rather than larger solver weights or a relaxed acceptance threshold.

## Verification and integration

`verify_periodic_contacts.py` decodes the actual single/repeated GLBs, independently verifies accumulated placement and terminal closure, unedited local transforms, root/joint edit limits including the seam, original positive-weight source targets, integer/half-frame floor, root/events, all archive entries and HTTP hashes. Largest repeated transform discrepancy is below 8e-8; unedited local discrepancy below 1.2e-8. The root correction step stays below 1.79 mm for turning and 12.31 mm for locomotion, versus the unchanged 15 mm bound. Joint correction steps stay within the 5 degree bound, including across the seam.

`reports/godot-periodic-contact-v3` passes actual Godot 4.7.2 playback: 12 runs, 998 transform samples, skeleton/extracted modes, half-frame/coarse/multi-period updates, nonzero actor placement, dispatch and silent-seek checks. Maximum transform discrepancy is 1.10e-5, CPU-skinned position discrepancy 9.67e-6 metres and root discrepancy 1.11e-5, under the existing 1e-4 numerical tolerance. Both packaged demo projects start and reach the first cycle boundary. All six input/corrected/repeated GLBs have zero validator errors and the original six Quaternius/one Cesium warnings. This is headless engine evidence, not GPU rendering, physics or animator approval.

Studio shows periodic endpoint guidance, corrected repeated previews, matching sidecar links and variant-specific runtime downloads. Result links now select the corresponding rig without requiring a separate character query parameter. Browser review confirmed cross-rig navigation, the three-cycle endpoint and visible grey character.

Marker edits of corrected loops preserve both single/repeated GLBs and the prior rejection status/audit. The first chain study exposed a missing quality-status carryover and is retained. Fixed API job `20260926-225646-18000447` is verified in `reports/periodic-contact-event-chain-v2`; it remains rejected after adding a timing cue. A regression test covers this behavior.

315 full tests passed with four upstream Torch warnings after the hybrid solver. Subsequent focused checks passed: five periodic tests (including final endpoint-sidecar export) and ten marker tests (including inherited rejection). JavaScript syntax checks passed. No model inference or training ran. The project-wide goal remains active and release approvals remain open.

Next: reviewed contact intent and model-assisted regeneration/editing of failed motion sections, extending semantic rough-clip editing across diverse actions. Retain these failures as regression cases; do not spend the project solely tuning this wave and locomotion sample. Scene/partner reliability, style diversity, offline installation and independent held-out/animator cleanup studies remain required.
