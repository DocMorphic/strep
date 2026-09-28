# General target-rig loop authoring

2026-09-26. Development progress under the existing full-project goal; no release or independent animator approval.

Studio Characters now offers **Make a loop** for saved imported, generated, corrected and edited humanoid clips. The recipe selects a start, cycle length, return-blend length, explicit turn per cycle and root mode. Traveling mode accumulates the source's horizontal cycle displacement; in-place mode removes net horizontal travel. Both retain periodic height and the specified turn. The API is `/api/rig-loops`; inputs are hashed, original assets/motions and recipe history are retained.

The source must contain continuation frames after the selected cycle: `start + period + blend <= source frames`, `period > blend >= 4`. A cycle is at most 30 seconds. Its first blended samples come from the ending continuation transformed back by the inverse cycle transform. The first two samples retain that continuation exactly; subsequent smoothstep weights return to the earlier motion. Output contains `period + 1` samples, including phase zero at the next cycle placement. A separate three-cycle GLB accumulates the rigid cycle transform, including turning, rather than resetting the root at each wrap.

Studio displays both variants with their own frame counts, reports, root tracks, contacts, event markers and source-clock links. The three-cycle variant is for review; editing controls require the one-cycle version. Switching variants retains phase. Source-authored targets are transformed into their appropriate cycle placement and retained with source contribution weights. Missing support remains unknown. Source events remain in the input package for explicit periodic review; exported boundary events identify cycle boundaries only.

## Executed cases and honest quality scope

| Job | Source and settings | Result |
| --- | --- | --- |
| `20260926-212331-ed0fa635` | Quaternius female corrected wave, start 10, period 60, blend 8, travel mode, zero turn | 61 / 181 samples. Floor about 3.01 mm; authored-support patch speed p95 **52.8 mm/s** when all positive-weight source contributions are included. |
| `20260926-212541-f05dcc66` | Same source/range/blend, travel mode, +15° turn | Correct cycle placement, but authored-support patch speed p95 **410.7 mm/s**, peak **677.5 mm/s**. This is severe sliding, not a valid turning motion. |
| `20260926-212922-5f10b11e` | Cesium imported animation after prior contact editing, start 0, period 30, blend 8, travel mode | 31 / 91 samples. Floor 50.44 mm at samples, 50.65 mm at half-frames. Failed quality case. Only a short authored heel interval exists, so its small patch speed does not establish whole-clip support. |
| `20260926-213335-362828ae` | Same wave as first row, only root mode changed to in-place | 61 / 181 samples, identity cycle transform. Floor still about 3.01 mm. All-positive-weight authored-support patch speed p95 **0.484 mm/s**, peak **1.446 mm/s**. |

The stationary wave's full-weight-only patch speeds looked low even before the fix; that excluded the actual return blend. The verifier therefore reports both full-weight metrics and a union of every positive-weight authored interval. The latter exposed the sliding and measured the in-place improvement. This is a controlled development comparison on the same source, not independent contact ground truth or held-out success.

In-place motion still has a maximum local rotation step of 22.9° within the cycle (6.48° around the repeated seam). The arm/body return can therefore need phase selection or refinement despite good foot metrics and exact closure. No motion here has independent naturalness/semantic approval. No model generation or training occurred.

## Export issue found and fixed

Initial imported locomotion job `20260926-212453-18b639f0` had the animation name `Imported locomotion cycle`. Godot wrapped its terminal sample to frame zero because of its name-based loop inference. The first audit is retained as **failed** in `reports/godot-rig-loops-v1`, including per-frame localization: only terminal frame 30 differed, by the approximately 5 mm cycle displacement.

[Godot's official name-suffix documentation](https://docs.godotengine.org/en/latest/tutorials/assets_pipeline/importing_3d_scenes/node_type_customization.html) describes the `loop`/`cycle` inference. `gltf_tools.authored_animation` now wraps user labels with an explicit stable prefix/suffix and preserves the original label in animation extras. It is used by loop, transition, clip-edit and prepared-import exports. Godot's audit records the imported loop mode. The locomotion job was regenerated with unchanged motion; all v2 files import with mode zero and preserve their terminal samples. Neither pose tolerances nor expected samples were changed to obtain a pass.

These GLBs are finite assets with explicit cycle metadata. Runtime engine looping/root extraction must deliberately consume the cycle transform; an unchecked engine loop flag can reset world displacement. The three-cycle baked export proves repeated pose/placement encoding, not runtime root extraction or gameplay-event behavior.

## Verification

`verify_rig_loops.py` reconstructs the loop independently from decoded source GLBs using per-node SciPy Slerp, checks each repeated cycle placement and the original seam samples, measures authored patch velocities and target error, samples floor depth at half frames, and verifies served-file hashes plus every ZIP entry. Input/contact/history artifacts remain immutable.

Evidence: `reports/rig-loops-v1`, `rig-loops-v2`, `rig-loops-in-place-v1`, and corresponding `godot-` directories. V2 reuses the unchanged two wave artifacts and the regenerated locomotion artifact. Its six GLBs contain 606 total frames at 19/65 bones, all skin surfaces survive Godot import, and maximum joint-position error is 4.48e-7 m. The in-place comparison separately verifies four GLBs/484 frames. All these GLBs have zero validator errors; the original six Quaternius or one Cesium warnings per file remain. Wave archives have 61 entries; locomotion archives have 59.

Last full regression run after the shared export-name fix: 287 tests passed, four upstream Torch deprecation warnings. The subsequent in-place addition passes all eight focused loop tests, including source continuation, zero/turning cycle transforms, three repetitions, terminal contacts/events, bounds and hashes. UI checks verify repeated playback ending at frame 180 / 6 seconds, terminal phase display, matching repeated sidecar links, and disabled editing on the repeated review variant.

## Remaining work

Support-aware cycle selection/refinement, wrap-aware contact correction that preserves the seam, periodic source-event mapping, runtime engine root extraction, meaningful turning motion, broader independently selected actions/rigs and blind animator cleanup-time evidence remain open. This implementation supplies a reusable authoring path and reproducible failures; it does not certify every selected range as loopable or realistic.
