# Native engine skin validation

The saved native Godot resources preserve this pair's imported skin in sampled
GPU views, including hand close-ups. Imported weight quantization produces small
3D differences, so the preceding original-skin contact measurements cannot be
treated as measurements of the imported mesh. A separate imported-data CPU
reconstruction still passes the authored contact and 53 declared mesh samples.
The strict near-end engine-clock failure and animation-quality failures remain.

## Bound inputs and scope

The input is the completed `reports/checkpoint-native-tracks-v3` audit from
[native engine validation](native-engine-contact-v1.md). Both original GLBs and
saved/reloaded `actor-0-animation.res` / `actor-1-animation.res` are reused by
hash. No clips, controls, scene placements, contacts or native key times change.
The GPU audit uses actual Godot runtime imports and the existing graphics probe
in a hidden-startup local process. No browser is involved.

Both imports have 18,056 vertices, eight influences per vertex and 77 bind
transforms. Imported positions and bind matrices match the original values
exactly. Joint correspondence uses names; rest-position and effective-weight
correspondence supports reordered vertices and coincident vertices with distinct
influences. It does not assume vertex indices remain unchanged.

Maximum effective per-joint weight error is 1.525506377e-5 and maximum raw
weight-sum error is 7.631443441e-5. The predeclared per-joint allowance is one
16-bit normalized step plus 1e-7, with 1e-6 m rest-position and 1e-5 bind-matrix
tolerances. No weight normalization is applied in the imported reconstruction.
Godot's compatibility skeleton shader accumulates the eight weighted matrices
without normalizing their sum.
[Godot shader source](https://github.com/godotengine/godot/blob/4.7-stable/drivers/gles3/shaders/skeleton.glsl).

## GPU comparisons and controls

Each actor is sampled at zero, 1.1897090673446655 seconds (a prior worst-error
native key), the edit-window start, event minus 0.05 seconds, the event, event plus
0.05 seconds and full duration. Each pose is rendered from three views with
whole-body and 30 cm hand framing. The reference triangles are independently
posed from the original full-weight GLB CPU skin and authored stage placement.
Images are 512 by 512, solid white, unshaded and double-sided on black.

All **84 positive comparisons pass**: at least 500 foreground pixels,
intersection-over-union at least 0.995, and silhouette distance at most 1.5 pixels.
Whole-body framing must not touch the image border; hand framing intentionally
crops the body and can meet the border. Observed minimum IoU is
**0.9994297957632098**, maximum distance **1 pixel**, and minimum foreground
population **13,791 pixels**.

Six event hand controls deliberately shift the forearm inverse bind by 5 cm,
with original reference triangles retained. Every control fails: IoU ranges
0.8836839384â€“0.9728577642 and boundary distances 12.0830â€“23.1948 pixels.
The harness therefore detects this known skin deformation error. This is not a
proof that every smaller, occluded or unsampled defect would be detected.

All 180 GPU/reference images and imported data are saved locally. These tests
validate finite-resolution sampled silhouettes on the recorded backend; they
do not certify every 3D vertex, materials, lighting, physics, contact or realistic
motion. The skin API reports bind indices/names and inverse transforms used by
the audit.
[Godot Skin API](https://docs.godotengine.org/en/stable/classes/class_skin.html).

## Imported-data contact and geometry

`ImportedSkin` reconstructs positions using the actual imported rest vertices,
raw quantized weights and bind matrices, driven by the bound native-resource
engine joint observations. It remaps coincident/reordered vertices to the
original vertex population by effective weights. The reconstruction retains
the original source triangle topology; it does not use GPU position readback.
Computations use float64 and the documented linear-weight formula rather than
reproducing every GPU precision operation.

| Measurement over declared geometry samples | Result |
| --- | --- |
| Maximum Euclidean vertex error vs original full-weight skin | 0.155127216 mm |
| Anchor error at authored event, A / B | 0.088297460 / 0.088517480 mm |
| Palm gap | 1.049369401 mm |
| Normal error, A / B | 1.034811Â° / 0.444115Â° |
| Authored region-contact target | PASS |
| Sampled crossing/containment checks | 53 / 53 PASS, zero measured depth |
| Maximum sampled floor penetration | 6.003400102 mm |

Crossing counts, degenerate-face counts and containment depth are independently
checked for both directions at every original geometry-guard time, including
the exact event. Passing these discrete CPU checks on original topology does
not establish continuous collision clearance or engine physics. The authored
palm-region condition remains separate from the original fixed-point benchmark.

## Reproduction and remaining work

```powershell
.venv/Scripts/python.exe scripts/audit_native_gpu_skin.py reports/checkpoint-native-tracks-v3 reports/checkpoint-native-gpu-skin-new
.venv/Scripts/python.exe scripts/diagnose_imported_native_contact.py reports/checkpoint-native-gpu-skin-new reports/checkpoint-imported-skin-contact-new
```

Fresh output folders are required. Both tools bind their inputs and archive
methods; they rehash evidence and current methods before recording completed
results. Import/GPU process failures are distinct from completed comparisons
with failed numerical checks. The first GPU attempt hit a GDScript type-inference
error; the second freed a reference between framings and was stopped after its
reported error. Their partial output remains in v1/v2. The repaired v3 GPU audit
and imported reconstruction are terminal. No expensive completed study was
rerun for documentation or commit.

All 1,118 model-free Python source tests pass. Targeted tests cover reordered bind/vertex layouts, distinct weights at coincident
positions, duplicate influence accumulation, allowed quantization, missing or
deformed data, matrix column layout and preservation of raw weight sums. Render
inspection confirms the expected body/hand silhouettes and visibly displaced
negative-control wrist. This is neither browser testing nor human animation
review.

Next resolve endpoint seek semantics and connect explicit native candidates and
their failure reports to Studio review. Original speed/acceleration failures,
sampled floor penetration, continuous-clearance uncertainty and human review
remain. No model training, held-out use or Studio selection occurred; all 14
release capabilities remain unapproved.

| Record | Result SHA-256 |
| --- | --- |
| GPU and imported skin v3 | `1463f1a00bb7f3da89e9f90897457e80af3ba201b80245a1c0f3bfc5b0d65ac9` |
| Imported-data contact/geometry | `699930df75daee11a390a3a116368ce285b94ab9462303d992fea73b8051442c` |
