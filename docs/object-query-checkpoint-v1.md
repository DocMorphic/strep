# Complete object playback queries with recomputed activations

The original six-second, two-hand lift study stops after about 440 seconds because available system memory reaches 453,505,024 bytes, below its existing 600 MiB guard. Its own peak process-tree RSS is about 1.48 GB and remains below the 7 GiB tree cap; the one-hour time cap is also unexpired. The supervisor exits with code 15 and records terminal failure. No completed candidate exists. The raw inputs, partial setup, method snapshots, logs and failure stay immutable. A stale inner `processing` marker is not evidence of a live worker or a result.

V17 retains V16's original 180 native keys, all 537 quarter-key poses, declared two-hand region population, object trajectories, point/normal constraints, rotation/root bounds, six solver stages and independent acceptance. It uses the previously verified sparse skin evaluation. Intermediate object queries run in chunks of 32 poses with non-reentrant activation checkpointing: temporary skin/distance tensors are recomputed during backward rather than retained throughout the forward graph. Outputs concatenate in their original frame order before the unchanged augmented-Lagrangian reduction. Nothing is dropped, subsampled or granted a looser threshold.

Each recomputation closure binds its own frozen object-pose/buffer slices. Reusing a later loop variable would silently change backward geometry, so tests explicitly use different moving trajectories and buffers across chunks. Bind coefficients and query tensors must remain constant during forward/backward; trainable object tracks are rejected. This is a correction-memory strategy, not a different motion checkpoint, scene-aware neural model or dynamics simulation.

## Verification

All 166 focused Python tests pass. They cover original contact compilation/evaluation and solver controls; recomputed values and weighted affine gradients for moving boxes, spheres and cylinders; maximum and per-vertex reductions; chunks of one, four and 32 poses; unchanged inputs and complete populations; invalid/mutable queries and unsupported configuration. A separate environment without Torch passes 45 overlapping metadata tests. Hosted inventory remains 394 model-free Python modules and 37 Node scripts per operating system. Validation of this publication is pending.

A same-input comparison in two isolated CPU processes retains **all 537 quarter-key poses and both complete hand regions (5,694 vertices)**. It uses the original skin's eight influences and the saved moving-box query trajectories/buffer policy. Residuals, scalar loss and rotation/position gradients match exactly in this comparison.

| Kernel mode | Sampled peak process RSS | Forward/backward time |
| --- | ---: | ---: |
| Dense intermediate-query activations | 1,162.1 MiB | 0.542 s |
| Recomputed in 32-pose chunks | 744.7 MiB | 0.653 s |

The measured isolated-kernel RSS reduction is 35.9%. These are single local runs, not complete solver memory, general throughput or portability claims. The kernel covers complete hands, not full-body collision approval or pose-controller gradients. Earlier sparse verification retains all 180 native and 537 intermediate poses with all 18,056 vertices/eight influences; affine values/gradients agree within floating precision. The first kernel command passes integer indices with the wrong Torch dtype and fails before evaluation; that failed harness is retained, and a fresh corrected harness explicitly uses long indices.

Local evidence is retained under `reports/box-lift-contact-playback-v1`, `reports/box-lift-sparse-backend-preflight-v1`, `reports/object-query-checkpoint-kernel-v1`/`v2` and the corresponding test folders. The first directory's supervisor and terminal audit are authoritative for the stopped study. A fresh guarded study must use a new output directory and unchanged original input hashes; observation timeouts alone never justify restarting a live worker.

## Reproduce and remaining work

Use separately acquired pinned dependencies, vendor assets and saved authored/guided inputs. For this lift, the source preview collection is supplied explicitly:

```powershell
.venv\Scripts\python.exe scripts/run_scene_fit.py <authored-lift-scene.json> --output reports/<fresh-correction> --solver-version 17 --preview-base reports/<original-preview-collection>
node scripts/validate_scene_exports.mjs reports/<fresh-correction>
.venv\Scripts\python.exe scripts/run_godot_scene_import.py reports/<fresh-correction> reports/<new-key-audit>
```

The private launcher additionally applies the existing one-hour/7 GiB-tree/600 MiB-available guards and preserves its exact source. Native-key engine import must be followed by dense exported playback measurements of both hands, full-skin box/floor geometry, orientation and release/boundary behavior. The longer lift outcome is unproven at publication. World/partner high-five requires its own path because this experimental object mode requires declared geometry. No dummy object, shortened clip, removed contact, relaxed metric, learned-model training, physical attachment or human quality claim is introduced. All fourteen release evidence lists remain empty; the full project goal stays active.
