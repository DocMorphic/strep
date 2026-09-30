# Moving cylinder grasp with fixed alternative guides

All 62 native grasp/release-guard keys pass, but exported interpolation and the surrounding clip still fail. The trajectory is retained as a failed development result; no clip or release capability is approved.

## Construction

The [calibrated pose](cylinder-guide-calibration-v1.md) supplies fixed guides 7148 / 11538, the original region faces and the passing hand configurations. Targets are expressed in the cylinder's local coordinates and transported through the existing object track. A declared **0.1 mm outward fitting reserve** selects poses inside the same authored contact windows; no clearance, gap, normal, guide or edit limit changes.

The original source finger rotations vary slightly during frames 60–121. The driver holds the calibrated **editable finger local rotations**, deriving their source-relative edits separately at each frame and checking every original norm budget before fitting. Uneditable end joints retain their source motion; all ten have zero skin influence in this asset. Assets where an uneditable hand joint influences skin are rejected by this diagnostic instead of falsely claiming a fixed hand shape.

Only the two shoulder/arm/forearm/wrist chains are fitted at each key. Other body edits and root lift remain equal to the reference-pose edits during the grasp; the underlying source motion continues. Numerical stopping requires wrist position residual below 1 micrometre and rotation-matrix residual below 1e-5 in Frobenius norm. This stopping condition does not approve the pose: serialized skin, source-relative bounds and every original numeric contact condition are measured afterward.

The authored grasp is frames **60–120**. Frame **121** is an explicitly separate release guard, not an extension of the authored contact interval. Twelve-frame quintic blends in physical edit coordinates join the grasp to the original source. Frames 49–132 change; **96 frames remain byte-exact across all saved motion arrays**. Guides do not vary by frame.

The bounded native run takes **73.172 seconds**, with peak observed RSS **583,557,120 bytes**. All **62/62** keys meet target and pose screens. Native full-skin cylinder clearance is about 2.135 mm. This is not sufficient for animation acceptance.

## Exported motion measurements

Both source and candidate are exported through the standard SOMA GLB path and decoded at **717 quarter-frame times**. The 241 authored-grasp times yield 482 individual hand-contact measurements; four additional samples check the release guard separately.

| Candidate phase | Samples | Geometry failures | Minimum cylinder clearance |
| --- | ---: | ---: | ---: |
| Unchanged before blend | 193 | 125, inherited floor failures | 62.413 mm |
| Approach blend | 47 | 29 | −21.451 mm |
| Authored grasp | 241 | 11 | 1.579537 mm |
| Release guard | 4 | 0 | 2.119669 mm |
| Release blend | 47 | 26 | −18.476 mm |
| Unchanged after blend | 185 | 0 | 94.323 mm |

During the grasp, **17/482 individual hand contacts fail**. The union of contact and geometry failures covers **20/241 times**. All eight additional release-guard hand measurements pass. The original guide condition remains failed at all 482 authored-grasp guide checks. Native and all 717 decoded source-relative edit-bound samples pass; root XZ and stored foot labels are preserved.

The candidate has 191 full-clip geometry failures versus 434 for the source, but that reduction is not acceptance. The source has 482/482 alternative-region contact failures. Candidate joint speed rises from **1.280603 to 1.451594 m/s**, and maximum quarter-frame finite-difference joint acceleration rises from **27.444606 to 197.226161 m/s²**. These sampled metrics are diagnostics, not force or physical-dynamics validation.

## Diagnosis and next decision

The largest acceleration occurs at the **right forearm, frame 115**. Native consecutive-key rotation changes reach **13.002255° at the right shoulder from frames 84 to 85**, despite small wrist target residuals. Several other arm/wrist jumps exceed 9°. This is consistent with the underdetermined per-frame arm fit switching internal joint configurations while preserving wrist targets. Warm starts and a tiny raw-parameter regularizer did not provide adequate temporal control.

The next change should constrain or regularize **physical joint motion across frames** while preserving source-relative edit bounds and the frozen contact definition, then repeat the same native/exported checks. Increasing the outward reserve alone would not address these arm jumps. After the grasp survives interpolation, the approach/release paths and inherited floor failures still require correction under the original gates. Keep this trajectory and its failed frames as the comparison.

## Independent verification and engine fidelity

`audit_regional_wrist_track.py` replays all 84 edited native frames, exact untouched arrays, fixed physical finger rotations, blend weights and original bounds. It invokes the existing full-skin exported-region auditor, then adds decoded between-key edit limits, original-guide comparisons and separate release-guard contacts. Input/method/output hashes and native FK/export fidelity are checked. The diagnostic peaks are independently recomputed from exported transforms.

Godot imports both clips and verifies **360 actor-frames with all 77 bones**. Maximum joint-position discrepancy is below **0.402 micrometres**; both preserve a skinned surface and non-looping playback. This establishes actor playback fidelity only, not cylinder physics, GPU skin appearance or motion quality. **39 focused tests pass**, including frame-local parity with fresh native contexts, bounded fixed finger shapes and explicit target stopping without pose approval. Public model-free CI remains separate from these local asset-dependent checks.

Evidence: `reports/cylinder-guide-track-v1`, `reports/cylinder-guide-track-review-v1` (including `diagnosis.json`), and `reports/cylinder-guide-track-engine-v1`. With separately acquired assets and retained study inputs, reproduce into fresh directories:

```powershell
.venv\Scripts\python.exe scripts/study_regional_wrist_track.py reports/cylinder-guide-projection-v1 reports/<new-track>
.venv\Scripts\python.exe scripts/audit_regional_wrist_track.py reports/<new-track> reports/<new-review>
```

There is no new anatomical, self-collision, continuous surface-collision, balance, interaction-force, semantic, animator-rating or cleanup-time evidence. No model checkpoint or Studio default changes. All fourteen release capabilities remain unapproved.
