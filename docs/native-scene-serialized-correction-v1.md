# Native correction across stored quaternion keys

The native scene fitter now offers three explicit experimental options for
bounded correction of supplied rig clips:

- `--vector-difference-scheme central` uses symmetric vector differences where
  both complete perturbations fit the control box. Near a box boundary it
  records a one-sided difference toward available room. All rows and exact
  nonzero derivatives remain present; native and contact clocks stay unchanged.
- `--rotation-storage-policy source-scale` applies the intended rotation by
  right-multiplying the original raw quaternion by its unit delta. It preserves
  the original quaternion length before Float32 storage. Decoding normalizes
  the quaternion as usual, so the intended orientation is unchanged.
- `--serialized-ray-probes 64` adds a finite budget of actual stored-key probes
  when a smooth proposal satisfies the protected source conditions and improves
  merit, while its decoded export fails those source conditions. This supports
  quaternion and mixed rotation/translation tracks that the older affine
  translation-cell calculation cannot handle.

The defaults remain forward differences, unit quaternion storage and zero
serialized-ray probes. Resume inherits its previous rotation storage policy
when no policy is specified; older requests infer `unit`. A policy change must
still reproduce the prior retained export byte for byte before optimization.
An incompatible nonzero checkpoint fails rather than rebaselining the actor
or its motion caps. Source-scale requires original rotation keys exactly
representable as Float32 and within four Float32 epsilons of unit length. More
substantial source normalization errors are rejected by this policy.

For a developer's configured Python environment and local completed fit:

```powershell
python scripts/native_scene_fit.py contacts.json permissions.json reports/serialized-fit --proposal-model storage-vector --iterations 2 --restoration-steps 3 --resume-from reports/prior-fit --vector-difference-scheme central --rotation-storage-policy source-scale --serialized-ray-probes 64 --geometry-policy geometry-policy.json
```

These are CLI research controls, not new animator-facing Studio sliders. The
command does not restart the live Studio server or alter its selected clip.
Underlying motion bounds, actor files, edit permissions, protected keys,
contact intent/timing/limits and an existing geometry policy remain preserved.
Final geometry and actual engine checks remain necessary. Source-scale changes
the representation of an edited quaternion, not its desired rotation or
the accepted source-rate tolerance.

## Why storage matters

An existing Float32 quaternion has a small representational length error.
Normalizing it before multiplication and rounding it back can move one or more
components by an ULP even when the intended rotation is infinitesimal. Direct
raw-quaternion multiplication preserves the source length and removes that
unnecessary jump. This does not remove all Float32 quantization or prove that
the intended motion is physically feasible.

The regression fixture demonstrates a sub-ULP edit whose source-scale GLB is
byte-identical to the unedited export, while the legacy normalization changes
its stored keys. Analytic orientation and quaternion-length checks cover a
nontrivial three-axis edit; resume inherits the policy and rejects a byte-
incompatible legacy replay. Larger source length errors and non-Float32 source
values are tested explicitly.

Serialized-ray search compares every key of every permitted track, including
frozen keys and tracks unchanged along the direction. Its bounded expansion
and bisection find tested matching/different key signatures and a matching
representative. Quaternion paths can curve or revisit states: the brackets
are not certified storage intervals, and the search is not exhaustive. Its
budget is per primary iteration. Every candidate is exported and redecoded;
all original source/edit/displacement/rate rows and individual contact
non-regression checks decide acceptance. A smooth proxy cannot approve a
stored candidate. Neither a passing ray probe nor a revised contact patch
confirms human animation quality, continuous collision safety or training
eligibility.

## Retained crawl evidence

The supplied development crawl retains the same first native source epoch,
54 explicit controls, 19 joints, 3,273 skin vertices, authored 19/19/33/33-vertex
contact patches, 20 mm position bounds and 0.005 m/s hold-speed bounds. The
source is a previously floor-restored rough clip, not its older raw mocap/rig
transfer epoch. Contact patches remain anatomically unreviewed.

The first symmetric-difference continuation attempts two iterations and accepts
no correction. It preserves the original rate arrays and exactly replays the
previous retained export. The unchanged forward path separately reproduces all
45,785 norm vectors/caps/scales and 6,375,321 sparse derivative entries exactly;
the conic direction function's AST is unchanged. Symmetric differences use 108
column proxy evaluations per iteration versus 54 for forward differences, so
this is not an equal-compute improvement claim.

Retained-probe diagnosis separates affine prediction, continuous motion, stored
proxy and actual GLB decoding. At a small forward or central backoff, the smooth
source prefix passes, while decoded angular-rate rows still fail. For the
central backoff, maximum normalized smooth source excess is -2.7281e-8 and
decoded excess is 4.9553e-6. All original constraints remain authoritative;
these observations motivate the representation and finite ray experiments.

The subsequent finite comparison uses two primary iterations per branch,
symmetric differences, three restoration steps and a 64-probe serialized-ray
budget per iteration. Unit storage retains 96 complete decoded exports;
source-scale retains 152. Both branches accept zero corrections, preserve the
original source-cap arrays exactly and retain the same final clip bytes.
The four revised holds still fail: maximum position errors are
37.84/79.10/91.81/88.20 mm and relative speeds are
0.19313/0.54886/0.25190/0.27585 m/s. Full sampled floor checks pass.

The source-scale representation removes the isolated normalization jump tested
above, but this finite crawl experiment demonstrates no accepted motion
improvement. Its final clip is byte-identical to the preceding completed CPU
Godot authoring/game/runtime study; that existing import record is reused, not
presented as a fresh engine run. Further work must address the measured decoded
source-rate failures before claiming usable crawl contact correction.

These are development corrections, not new model inference, held-out
validation, animator approval or release evidence. Local comparison records
remain in `reports/native-crawl-serialized-correction-v1/checks.json`; the
project-wide goal and frozen acceptance gates remain unchanged.
