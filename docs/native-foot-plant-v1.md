# Explicit fixed-patch foot planting

`native_foot_plant.py` adds an offline deterministic correction and independent
contact acceptance checks. It moves a foot's fixed source patch toward its
authored stance-start position through the existing two-bone leg rig. A lower
contact error cannot override support, displacement, angle or motion-rate
failures. All three real development trials retain their exact input.

## Target and geometry

A policy binds the original source, current input clip and support draft by
SHA-256. Every support has an explicit maximum planar patch anchor error and
maximum tangential patch speed. Mapping, native clocks, edit windows, stance
times, plane and displacement/angular bounds come from the existing native
support draft. No semantic stance or human contact label is inferred.

The patch uses fixed source vertices within 3 mm of the foot-region minimum
at stance start. All positive vertex influences must belong to the foot
subtree; every mesh primitive and up to eight skin influences are retained.
The patch centroid's source-start tangent position is the target. Proposed
ankle translations lie in the authored plane tangent. Exact two-bone IK
retains foot-world orientation and rigid bone lengths at native keys.
Quintic weights blend the correction outside stance and are zero at edit
boundaries. Long windows can still exceed displacement bounds; proposals
are rejected rather than accepted by widening the limits. Unreachable exact
IK targets are rejected without clamping.

Independent decoding verifies native channel clocks and interpolation,
unchanged translations and other tracks, exact boundary/outside keys,
mesh attributes/topology, binds and embedded image payloads. Contact checks
sample at 120 Hz plus exact stance boundaries and compare each fixed vertex
to its source-start tangent position. Measuring drift from the candidate's
own start cannot hide a constant target offset. Source-relative four-bin
rate caps, support heights and cumulative ankle/angular bounds are checked
separately through the existing serialized audit. Those development caps
are not independent animation-quality or realism benchmarks.

The selected output is the proposal only when every configured gate passes
and the input was not already satisfactory. Otherwise it is a byte-for-byte
copy of the supplied input; rejected exports and explanations stay available.
This generic GLB step does not claim editable native NPZ conversion or a
Studio integration. Its report explicitly keeps native conversion unverified.

## Development evidence

The prior accepted wave still has 4.879948 mm fixed-patch drift. A source-bound
diagnostic compares ideal point translations only: centering the patch could
reduce drift to 0.525718
mm, whereas fixing the ankle alone leaves
0.942076 mm.
The required centroid shift is at most 4.697269
mm. These ideal translations are a diagnostic, not an exported IK result.

Actual wave, kick and crawl trials use their historical numerical support
drafts and authored limits of 1 mm patch anchor error and 5 mm/s patch speed.
These are explicit development choices, not validated universal thresholds.

| Clip | Proposed anchor error | Proposed patch speed | Failed rate rows | Result |
| --- | --- | --- | --- | --- |
| Wave | 0.525723 mm | 5.045768 mm/s | 26 / 5 / 22 / 13 | Retained input |
| Kick | 18.028257 mm | 202.116302 mm/s | 359 / 4 / 85 / 17 | Retained input |
| Crawl | No exported proposal | Not measured | Not measured | Exact leg reach rejected |

Rate groups are positional speed/acceleration and angular speed/acceleration.
The wave improves geometric anchor error but exceeds its speed limit by
0.045768 mm/s and fails 66 rate rows.
Its sampled support height/edit bounds pass: maximum ankle change is
6.393939 mm and local angle change is 4.006758 degrees. The kick's 68.527419
mm ankle change exceeds its 30 mm displacement budget; support gap, patch
limits and rate gates also fail. The crawl rejection is exact reachability,
not evidence that a different pose or parameterization cannot work.

The selected inputs remain exact, including the wave's previously accepted
height correction. Godot imports three selected inputs and two rejected
proposals: 5 clips/600 native
frames with 77 bones, one skin and non-looping playback. Maximum joint
position difference is 8.944e-07 m and
basis-element difference is 9.795e-07.
Headless CPU import fidelity does not establish browser/GPU appearance,
continuous clearance, balance, force-consistent contact or realistic motion.

## Running and testing

Use a source-matched support draft and a separate policy:

```json
{
  "schema": "strep-native-foot-plant-v1",
  "source_sha256": "<SHA-256 of original.glb>",
  "base_sha256": "<SHA-256 of current.glb>",
  "draft_sha256": "<SHA-256 of support-draft.json>",
  "supports": [{
    "id": "<existing support id>",
    "maximum_patch_anchor_error_m": 0.001,
    "maximum_patch_speed_m_s": 0.005
  }]
}
```

```powershell
.venv\Scripts\python.exe scripts/native_foot_plant.py original.glb current.glb support-draft.json plant-policy.json fresh-output
```

Seventeen new fixture cases plus native support/diagnostic regressions pass
58 checks. They cover unchanged tracks, tilted planes, reach rejection,
misbound/invalid policies, changed triangle payload, zero-drift but shifted
patches, immutable inputs, retained failures and already satisfactory inputs.
A separately constructed oscillating toy rig actually passes every geometric
and rate gate without mocked acceptance; its source anchor error is over
16 mm and corrected error is below 0.0001 mm. That is software validation,
not a Kimodo motion, real training target or human realism endorsement.

Preceding commit 0408e50 passes hosted workflow 37056081081, including the
full source-check selection. The new module is checked with the focused
58-test selection; the unchanged full suite is not rerun for this isolated
addition. The new tests are added to hosted CI.

Local evidence stays in `reports/native-plant-diagnostic-v1` and
`reports/native-plant-canary-v1`; a source/evidence receipt is saved in
`reports/native-plant-validation-v1/verification.json`. Model, character and
generated payloads, credentials and detailed local studies remain excluded
from public Git.

No new generation, real model update, human submission, reviewed licensed
target admission or formal held-out run occurs. All 14 capabilities remain
unapproved, the formal 72-by-five population stays untouched and the full
goal remains active. Joint optimization of planted geometry and motion rates
is still needed; height correction and deterministic centering alone do not
solve general contacts. Broader actions/styles, object/partner/finger targets,
rig transfer, reviewed learning and human release evaluation remain required.
