# Selective body-pose guides

The request adapter now accepts `type: "joint-set"` with 1–30 distinct SOMA30
`joint_names`. This exposes knees, head, pelvis, torso and other represented
joints without also conditioning every other joint's pose. Action descriptions
remain arbitrary; joint names describe the checkpoint skeleton, not an action
whitelist or names on the supplied character rig.

Studio's pose-guide composer adds **Selected body parts** and a multiple-selection
control. It derives targets from the captured source pose, whose NPZ, SHA-256 and
source-frame indices remain bound. Selecting different joints does not solve a
new pose. The existing hand/foot offset authoring tool remains separate.

```json
{
  "type": "joint-set",
  "motion": "reports/my-authored-pose/motion.npz",
  "sha256": "<exact source SHA-256>",
  "source_frames": [0, 60, 119],
  "frame_indices": [0, 60, 119],
  "joint_names": ["Head", "LeftShin", "RightShin"]
}
```

`LeftShin` and `RightShin` identify the SOMA knee-origin joints. The source must
be a validated native SOMA77 motion, including consistent local rotations,
global rotations and joint positions. The actual checkpoint conditions are
SOMA30 global joint positions and rotations at the chosen frames, plus the
upstream implicit root XZ path, hip height and heading. Other joints have no
direct pose mask; generation can still change them. Existing overlap and origin
rules remain enforced. Fingers beyond the reduced skeleton are not exposed as
independent articulation controls.

Unlike the existing `end-effector` guide, `joint-set` does **not** expand a hand
or foot selection into its upstream endpoint group. Authors must select every
desired represented joint explicitly. The adapter initializes upstream common
root handling, replaces the selected channel indices, preserves crop/move and
serialization, and sends the existing condition format to unchanged weights.
It rejects skeleton/order mismatches instead of applying indices to another rig.
The pinned NVIDIA checkout and downloaded checkpoint remain unchanged.

Guide audits retain selected position/rotation channel names and report their
actual errors. The provisional 30-mm / 15-degree numerical screen remains a
development diagnostic. Selecting body joints does not enforce mesh collision,
surface support, balanced forces, contact timing or plausible animation.
Independent target-rig transfer and full mesh checks remain necessary.

The [four-clip protocol](../benchmarks/selected-joint-guides-v1.json) freezes two
ground-action requests with seeds 77 and 79. It is a functional integration
probe, separate from the [complete five-seed geometry comparison](ground-proposals-v1.md).
Its reference poses are previously measured development failures, not clean
corrective targets or training examples. Original raw clips and all outputs
remain retained. The goal and release criteria remain unchanged.

The unchanged checkpoint completes all four raw clips with the new guide class,
100 denoising steps and no postprocessing. Two original descriptions reuse exact
current-method cached text features; no new text encoding or training occurs.
The worker finishes in 53.922 seconds at 1,620,905,984-byte peak process-tree RSS.
All 71 recorded resource observations replay.

**0/4 clips passes the provisional guide screen.** Errors at the three authored
frames are retained, including maxima across every selected joint:

| Request | Seed | Root-path error (mm) | Joint-position error (mm) | Hip-height error (mm) | Selected-rotation error (degrees) |
|---|---:|---:|---:|---:|---:|
| Crawl: head and knees | 77 | 56.09 | 94.52 | 9.79 | 5.96 |
| Crawl: head and knees | 79 | 39.16 | 139.05 | 36.11 | 28.49 |
| Get-up: pelvis, chest and head | 77 | 59.84 | 162.42 | 15.25 | 35.28 |
| Get-up: pelvis, chest and head | 79 | 152.02 | 171.12 | 22.98 | 30.63 |

Generation/condition delivery therefore works, but precise target satisfaction
does not. Neither action receives a clearance, semantic or quality approval.
The probe performs no new target-rig, complete-mesh or engine assessment and
does not substitute these four clips for the existing five-seed baseline.

Core checks pass 143 Python tests and three Node checks. Actual pinned SOMA
CPU/CUDA condition assembly verifies exact selected position/rotation masks,
unselected channels, crop/move, serialization and an orientation-only target
miss. Earlier hand/foot/root/full-body and scene-planning behavior remains
covered. All 48 source-check resource observations replay. Live Studio rendering
remains unverified; the existing server has not been restarted.

Local evidence lives under `reports/selected-joint-guides-source-checks-v1`,
`reports/selected-joint-guides-probe-v1` and their guarded job/resource records.
The next corrective stage needs explicitly authored, feasible whole-body/support
targets and bounded enforcement or a separately evaluated scene-conditioned
editor. These failed source poses are excluded from clean-human training targets.

The Studio module route and current model-free admission checks additionally
pass 20 tests in the isolated CI dependency environment. Its 20 resource
observations replay. Both new model-free Python/Node modules enter the explicit
source inventory, now 452 Python modules and 42 Node suites. These local checks
do not claim a completed hosted run or rendered Studio session.
