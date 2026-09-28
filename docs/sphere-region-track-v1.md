# Region contacts through a moving grasp

The new region-contact condition now passes all 62 grasp/release-guard keys and all 245 exported quarter-frame samples over that interval. The complete clip is still rejected: its approach blend intersects the sphere, some motion peaks increase, and the unchanged outer clip retains small floor-clearance failures. No release capability is approved.

## Trajectory construction

The [bounded two-hand pose](sphere-region-pose-v1.md) supplies the hand shape, contact regions and initial arm configuration. Its skinned anchor, region normal and knuckle tangent are expressed in the sphere's local coordinates and transported with the original object trajectory. At each key, the shoulder, arm, forearm and wrist are fitted under their original 40-degree rotation-norm budgets, relative to the original animation. The previous solution initializes the next solve. Other rotation edits and root lift remain equal to the reference pose during the grasp. The underlying reference animation continues to move; this is not a held world-space body pose.

The reference finger shape fits all original finger budgets across the grasp interval because the original finger local rotations are constant there. No finger-budget increase or model change was needed. The source grip interval is frames 60–120; frame 121 is the existing release endpoint guard. Twelve-frame quintic blends in physical edit coordinates connect the interval to the original clip. Blended rotation vectors remain in their original norm balls, but that alone does not guarantee a collision-free path. Ninety-six native frames remain exactly unchanged across every saved array.

`region_grasp_track.py` implements object-local targets, the bounded arm fit and quintic blending. `study_region_grasp_track.py` saves all frame solutions, including failures and solver termination details, plus implementation snapshots and input hashes. The source clip, object tracks, original scene targets and acceptance thresholds remain unchanged. The new surface/normal definitions retain their explicit authored-condition provenance; the original fixed-point condition is not claimed as solved.

## Export reveals the missing clearance margin

The first trajectory, `sphere-region-track-v1`, passes all 62 native grasp keys. Exported interpolation passes only 177 of 245 quarter-frame samples. Its minimum sphere clearance is 1.969938 mm, slightly below the unchanged 2 mm requirement; some left-hand contact triangles also fail their lower gap bound. The isolated pose had only about 5 micrometres of surplus clearance.

The follow-up, `sphere-region-track-v2`, adds a declared 0.1 mm outward reserve to each fitting target. Authored world-space grip targets, 5 mm anchor/centroid limits, 10-degree normal limits, 2–3 mm distributed-contact gap, spacing/area requirements and original joint budgets are unchanged. This selects a different pose inside the same region-contact acceptance set. The first trajectory and every failure remain retained.

| Measure over grasp and release guard | Original V13, measured with new regions | Region track v1 | Region track v2 |
| --- | ---: | ---: | ---: |
| Exported samples passing region/geometry checks | 0 / 245 | 177 / 245 | 245 / 245 |
| Minimum full-skin sphere clearance | -4.287311 mm | 1.969938 mm | 2.069914 mm |
| Minimum full-skin floor height | 1.948417 mm | 6.054139 mm | 6.054139 mm |
| Maximum left anchor error | 35.017784 mm | 2.119282 mm | 2.219287 mm |
| Maximum right anchor error | 30.350516 mm | 2.148859 mm | 2.246837 mm |
| Maximum left object-relative slip speed | 0.170413 m/s | 0.003760 m/s | 0.003759 m/s |
| Maximum right object-relative slip speed | 0.136125 m/s | 0.010181 m/s | 0.010195 m/s |

The v2 dense audit also verifies edit limits between keys: zero failures across all 717 full-clip samples. Its largest rotation edit is 38.502996 degrees; the smaller individual finger budgets are checked separately. Maximum active region-normal errors remain below 9.502 degrees. These are discrete vertex and pose measurements, not continuous collision detection or physical grip certification.

The two studies used about 157.987 and 174.000 seconds of recorded projection time. Both retain evaluation-limit termination at frames 119 and 121. Those keys nevertheless meet independently measured pose/target criteria; solver success flags do not decide acceptance. The first directional derivative check has maximum scaled-residual error 1.08e-7.

## Remaining failures

The v2 approach still has 17 failing quarter-frame samples, with up to 3.760326 mm sphere penetration at frame 58. The earlier v1 diagnostic locates the overlap at left palm vertex 7071, while the original approach's nearest vertex is the pinky tip. This identifies a new geometric path regression introduced by blending toward the improved grasp. The release blend has no measured object/floor failure, but that does not establish good timing or naturalness.

Whole-clip joint speed rises from 1.409751 to 1.742135 m/s, and peak sampled joint acceleration rises from 38.516182 to 46.718854 m/s². Hand speed near grasp/release boundaries improves, but that cannot erase the whole-body regressions. Existing outer-clip floor height still reaches 1.879032 mm, below the 2 mm clearance requirement; those untouched-frame failures remain visible. No animator ratings, cleanup times, self-collision, anatomical or balance evidence has been added.

Next, replace the unsafe approach blend with a path that explicitly checks hand/body clearance while reaching the same contact timing. Preserve the successful grasp interval and original limits, then recheck the full motion and dynamics. A smooth scalar envelope is not sufficient. Broader objects, rigs, actions and partner interactions remain required by the project goal.

## Independent verification and engine playback

`audit_region_grasp_track.py` independently replays native parameter tracks and quintic weights, checks the frozen parameters and original limits, and verifies all untouched frames exactly. It exports both baseline and candidate through the normal SOMA GLB exporter, decodes their actual animation channels, and measures every skin vertex against all authored objects and the floor at 717 integer/quarter-frame times. Scalar contact-triangle enumeration checks distributed contact independently of the optimizer. The newer audit additionally evaluates reference-relative joint/root limits at subframes.

The first audit's implementation was captured after completion only after reconstructing its bytes and matching its recorded SHA-256; the second audit saves its source before dense sampling. Raw results were not rewritten. Both native study implementations were snapshotted before fitting.

Godot imports the baseline and both candidate GLBs and verifies all 540 actor-frames with all 77 bones. The maximum joint-position discrepancy is 0.445 micrometres; all imports retain a skinned surface and non-looping playback. This checks playback fidelity only. It does not establish GPU skin rendering, event/physics integration or motion quality. Fourteen focused tests pass, including rigid object-local transport, blend endpoint behavior, region selection and binding isolation.

Local evidence is retained under `reports/sphere-region-track-v1`, `reports/sphere-region-track-v2`, their `-audit` siblings, `reports/sphere-region-approach-diagnostic-v1`, and `reports/sphere-region-track-engine-v1`. Generated motion, GLBs and reports remain excluded from Git.

## Reproduction

These commands require the earlier local pose/scene fixtures and separately acquired licensed skin dependencies. Use fresh output directories.

```powershell
.venv\Scripts\python.exe scripts/study_region_grasp_track.py reports/sphere-region-pose-v1 reports/new-region-track --outward-reserve-m .0001
.venv\Scripts\python.exe scripts/audit_region_grasp_track.py reports/new-region-track reports/new-region-track-audit
```

The retained engine manifest can be verified with `scripts/run_godot_rig_import.py --study reports/sphere-region-track-engine-input-v1 --output reports/new-region-engine-audit`. No Studio default, held-out test, model checkpoint or release gate was promoted.
