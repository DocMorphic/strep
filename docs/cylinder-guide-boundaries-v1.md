# Cylinder boundary guidance and outer floor correction

The approach and outer-floor geometry defects are corrected at exported quarter-frame samples, and the passing grasp is unchanged. Eight release samples still fail the original clearance screen, and boundary motion becomes jerkier. The combined clip is rejected; no release capability is approved.

## Boundary-only guidance

The input is the [physical-continuity grasp](cylinder-guide-continuity-v1.md). Only approach frames 49–59 and release frames 122–132 are eligible. The complete grasp and release guard, frames 60–121, stay exact. All non-arm parameters, including finger edits and root, stay fixed to the input during this stage.

`cylinder_approach.py` computes a conservative radial escape of every vertex with any positive hand-subtree influence, including mixed hand/forearm skin. Each vertex inside the expanded cylinder height contributes a forbidden interval along the translation ray for the expanded radial disk. Merging intervals includes vertices that start safe but would enter while another moves out. The expanded disk/height product encloses the rounded cylinder offset, so this is safe rigid guidance, not an exact shortest translation. Actual articulated skin must still be measured.

The guidance target is **2.5 mm**, while acceptance retains **2 mm** and the existing 1 micrometre numerical allowance. Both wrists keep their input orientations. The original bounded arm fitter uses physical local-rotation continuity to the previous key. It changes **12 native frames**: 55–59 and 123–129. All 12 pass native full-skin object/floor checks and original edit bounds; **168 other frames are exact** relative to the moving-grasp input. The largest guide displacement is 25.434 mm at the left hand, frame 127. Total recorded boundary work takes 52.781 seconds.

## Outer floor lift

`correct_regional_outer_floor.py` changes only root Y and joint heights at frames **1–47**, minimizing lift and second differences subject to dense floor constraints and the original root-lift capacity. Frame zero and all frames 48 onward are locked. It reuses the input trajectory's dense samples only after proving that every native key supporting samples through frame 48 is unchanged by the boundary patch.

The guidance target is 2.002 mm for this prefix; locked later samples retain the original floor gate. The solver succeeds and adds at most **0.131882 mm**. All **133 locked frames**, rotations, root XZ, contact labels and event timing are exact relative to the boundary result. Exported prefix height reaches **2.001970 mm**. The minimum elsewhere in the unchanged tail is **2.000020 mm**, so the full clip should not be described as having a two-micrometre reserve everywhere.

## Combined exported measurements

All 717 integer/quarter-frame times are decoded from the actual exported GLB, using all 18,056 skin vertices. Original source-relative edit bounds pass at every sample. Grasp contact/geometry results remain identical to the retained passing track.

| Candidate measurement | Moving-grasp input | Boundary + floor |
| --- | ---: | ---: |
| Pre-approach floor failures | 125 | **0** |
| Approach geometry failures | 21 / 47 | **0 / 47** |
| Grasp geometry failures | 0 / 241 | **0 / 241** |
| Authored hand-contact failures | 0 / 482 | **0 / 482** |
| Extra release-guard contact failures | 0 / 8 | **0 / 8** |
| Release geometry failures | 26 / 47 | **8 / 47** |
| Full-clip geometry failures | 172 / 717 | **8 / 717** |
| Peak sampled joint speed | 1.587032 m/s | **1.878351 m/s** |
| Peak sampled joint acceleration | 43.071866 m/s² | **155.944946 m/s²** |

The remaining release failures occur at frames **126.5, 126.75, 127.25, 127.5, 127.75, 128.25, 128.5 and 128.75**. Minimum clearance is **1.545165 mm**, below the original 2 mm requirement. These are clearance deficits, not negative signed distances. Approach clearance reaches a minimum of 2.055424 mm. The source baseline's speed and acceleration remain 1.280603 m/s and 27.444606 m/s²; the new clip is not motion-quality approved.

## Diagnosis and next decision

The acceleration maximum is at the **right forearm, frame 129**. Additional large peaks occur at frames **59–60**, where the separately corrected approach joins the protected grasp. Per-key wrist guidance plus a preference to the previous joint pose does not ensure a smooth join to the next protected pose. Native clearance also does not guarantee interpolated clearance.

Keep the original, moving-grasp and boundary failures. Next solve the approach and release as multi-frame paths with endpoint pose/velocity conditions, physical joint smoothness and collision checks between keys. Preserve the passing grasp, fixed guides, source-relative edit limits and verified outer-floor correction. Simply increasing guidance reserve or declaring the approach finished because its geometry passes would miss the measured motion regression.

## Verification and reproduction

`regional_boundary_audit.py` independently reconstructs each changed native pose, verifies frozen parameters, recomputes radial interval guidance (maximum discrepancy 2.78e-17 m), and checks exact protected frames. It separately verifies root-only floor translations, unchanged interpolation support, capacities and dense linear floor constraints. `audit_regional_wrist_track.py` composes those checks with exported full-skin geometry, between-key edit limits and original-guide comparisons. **49 frames remain exactly equal to the original source** after the full chain; immediate-input protected counts above describe each individual patch.

**57 focused tests pass**, including cylinder-side/cap cases, initially safe obstructing vertices, rotated cylinders, floor interpolation/capacity cases and the existing pose/continuity checks. Godot verifies **180 actor-frames with all 77 bones**, preserving the skinned surface and non-looping playback. Maximum joint-position discrepancy is below 0.403 micrometres. Engine fidelity does not approve contact, cylinder dynamics, rendered skin or naturalness.

Evidence is retained under `reports/cylinder-guide-boundaries-v1`, `reports/cylinder-guide-floor-v1`, `reports/cylinder-guide-boundaries-review-v1` (including `diagnosis.json`), and `reports/cylinder-guide-boundaries-engine-v1`. With acquired assets and retained inputs, use fresh directories:

```powershell
.venv\Scripts\python.exe scripts/correct_regional_boundaries.py reports/cylinder-guide-track-v2 reports/<new-boundary>
.venv\Scripts\python.exe scripts/correct_regional_outer_floor.py reports/<new-boundary> reports/cylinder-guide-track-review-v2 reports/<new-floor>
.venv\Scripts\python.exe scripts/audit_regional_wrist_track.py reports/cylinder-guide-track-v2 reports/<new-review> --boundary-patch reports/<new-boundary> --floor-patch reports/<new-floor>
```

Public model-free CI is separate from local Torch/asset-dependent tests. No anatomy, self-collision, continuous surface collision, balance, forces, semantic correctness, animator rating or cleanup-time evidence is added. All fourteen release capabilities remain unapproved.
