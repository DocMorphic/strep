# Rig-mapped native foot support intervals

The experimental CLI now accepts explicit foot-support intervals on a supplied
rigged GLB. Joint names can differ from SOMA names. It preserves original keys,
root/other branches and the source motion outside authored edit windows, including
airborne phases. It proposes both upward and downward ankle corrections within
signed displacement bounds. No new motion was accepted on the first real-clip
test: support screens pass, source-relative rate screens fail, and the output
retains the original bytes. Studio integration remains unfinished.

## Author a source-bound draft

Inspect the actual skin-joint identities, parents and original rotation clocks:

```powershell
.venv/Scripts/python.exe scripts/native_support_job.py character.glb --describe reports/my-support-metadata.json
```

Choose a fresh metadata filename. This read-only route does not infer anatomy or
assign roles. Map the root and each requested direct thigh/knee/foot chain using
unique joint names or node indices from that metadata. The draft binds the exact
source GLB SHA-256, animation index and duration. The current implementation
requires one chosen animation with LINEAR rotation tracks, one skinned primitive,
rigid transforms and a nonempty fully foot-bound skin region. Intermediate helper
bones and unmatched clocks within a chain are explicitly rejected.
The ankle must remain below the thigh origin along the plane normal throughout
the edit window; folded or above-hip poses need a broader solver.

Save a JSON draft following this shape, replacing the hash, root, mapping and
key indices with values for the supplied source:

```json
{
  "schema": "strep-native-support-v1",
  "glb_sha256": "replace-with-source-sha256",
  "animation_index": 0,
  "duration_s": 3.6666667461395264,
  "root_node": 1,
  "mapping": {
    "LeftLeg": "LeftLeg",
    "LeftShin": "LeftShin",
    "LeftFoot": "LeftFoot"
  },
  "supports": [
    {
      "id": "left-stance",
      "foot": "LeftFoot",
      "stance_s": [1.5, 2.5],
      "edit_keys": [10, 65],
      "plane": {"normal_xyz": [0, 1, 0], "offset_m": 0},
      "clearance_m": 0.00025,
      "maximum_gap_m": 0.005,
      "maximum_displacement_m": 0.03,
      "maximum_angle_degrees": 45
    }
  ]
}
```

`stance_s` specifies exact seconds, including fractional boundaries. `edit_keys`
selects the first and last existing common chain keys; those boundary keys stay
frozen and at least three interior keys are required. The edit window provides
room to blend into/out of stance. A stance must contain at least two native keys.
The keys bracketing fractional stance boundaries also receive height constraints.
If a frozen boundary cannot meet them, the proposal is rejected; it never expands
the edit window or snaps the requested stance time.

The static plane is in the GLB's world coordinates: signed height is
`normal_xyz · point - offset_m`, in metres. Scene placement and moving objects are
not applied by this standalone tool. The lowest fully foot-bound surface point,
not the entire sole, is constrained. Maximum gap is at most 5 mm, displacement at
most 30 mm and source-relative local rotation at most 45 degrees; authors can
choose tighter values. The native-key upper height has a 0.25 mm inward reserve.
Support chains must occupy separate branches, and same-foot edit windows cannot
overlap. Disjoint stance/edit intervals are supported; the gap between them
retains the original motion.

## Fit, audit and retain failures

```powershell
.venv/Scripts/python.exe scripts/native_support_job.py character.glb reports/my-support-draft.json reports/my-support-fit
```

Use a fresh immediate `reports/` output folder. The worker binds source/draft
bytes, archives implementations, retains the input and every produced trial,
and checks that the input and methods did not change. Description and fitting
also detect source changes during preparation. It performs no model inference
or training.

Signed height ranges are intersected with each key's exact two-bone reach range.
The original per-key bone lengths/translations are retained. Knee bend is smoothed
on the physical native clock toward the closest allowed source bend, with frozen
window endpoints. Four fixed parameter pairs are tried. The serialized GLB is
reloaded before any decision.

The audit includes full-clip 120 Hz samples, all native keys and midpoints,
stance/edit boundaries and exact duration. It checks channel identity, native
clocks, unedited values, root/other branches, free phases, serialized angle/lift
bounds and stance-region heights. Per-support files record every sampled height
and identify worst times. Root motion is saved at the audit times without changing
the native root tracks. Authored support markers are bound to the final output
hash and explicitly distinguish verified sampled support from unverified intent
on a retained failed input.

Source-relative positional/angular speed and acceleration caps use the selected
input's full uniform 120 Hz motion, four equal time bins and the existing 1e-5
rate tolerance. The fractional final tail is reported and excluded only from
these uniform derivatives. These comparative caps do not replace an independent
benchmark reference or establish plausible dynamics. A separate absolute peak
comparison remains diagnostic. A proposal must pass every support and comparative
rate screen to be chosen. An already satisfactory input stays byte-identical;
that outcome is not described as improved motion.

## First development test

The input is actor A of the checkpoint-selected pair. Both feet have authored
stance from 1.5 to 2.5 seconds, edit boundary keys 10 and 65, and the unchanged
world floor. All four v4 proposals preserve clocks, unedited transforms and free
phases exactly, and pass both foot-height screens at 161 times per support.
There are 589 full-clip audit times. Minimum stance height is at least 0.318532 mm
and maximum lowest-foot height is at most 4.750000 mm across these proposals.
All comparative rate screens fail:

| Trial | Position speed | Position acceleration | Angular speed | Angular acceleration |
| --- | ---: | ---: | ---: | ---: |
| 0 | 492 | 33 | 80 | 24 |
| 1 | 437 | 32 | 66 | 26 |
| 2 | 502 | 33 | 88 | 25 |
| 3 | 431 | 29 | 79 | 24 |

Counts refer to this tool's selected-input comparative caps, not the earlier
pair study's original baseline caps. No changed output is accepted. Input stance
depths remain 2.551739 and 3.033551 mm, so retained-input support is not approved.
The retained output hash is
`14834fe9d8c4cc3653b8436459681ce3507773d465b2d8a1976c8fc962ae74d4`;
v4 result is `cfe48ab5fa5a5c88d94c2855fe52d111c1cfcbf7822bc0b042efb66b8c9674cf`.

The first attempt stopped on an exact preservation assertion: ordinary sampling
introduced a matrix difference up to 1.110223e-16 at a frozen key when its next key changed.
Exact-key handling initially changed the shared sampler, which correctly caused
an older prepared-request hash check to fail. That shared edit was reverted.
`NativeSupportSampler` now isolates exact-key handling to this new path; fractional
times remain interpolated without a tolerance snap. The next attempt exposed
penetration at fractional stance boundaries. Bracketing-key constraints repaired
the sampled height screen. All attempts and their archived methods remain local
and immutable.

## Scope and next work

Synthetic tests cover arbitrary joint names, signed lowering, unchanged airborne
phases and sibling branches, exact/fractional clocks, disjoint windows, hash and
source-mutation rejection, failed-trial retention and already satisfactory inputs.
The older prepared-pair test passes again with its original shared sampler hash.
All 1,208 model-free Python tests pass; 131 bound local evidence files rehash
without mismatch. The preceding public knee-smoothing commit passed hosted
checks on Windows and Linux.

This is a CLI authoring prototype. It does not establish engine/GPU equivalence
for new proposals, self/partner collision freedom, whole-sole planting, balance,
contact forces, static-object finite geometry or continuous clearance/rates. No
Studio route, default selection, human approval or release capability was added.
Next connect source-bound native drafts and diagnostic previews to Studio, then
solve rate/contact constraints together and broaden rig/scene support. Arbitrary
actions remain the product scope; these foot phases are not an action whitelist.
No held-out prompts or cleanup reviews were used. All 14 release capabilities
remain unapproved and the full-project goal remains active.
