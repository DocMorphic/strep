# Native conversion decisions and separate foot-drift diagnostics

Studio now reports the actual native selection when conversion rejects a
fitter's passing GLB. The retained clip, preview link and authored support
markers follow the converted result. The fitter output remains available
under an explicit “before native conversion” label. This fixes a demonstrated
reporting error; it does not change any motion limit or approve animation.

## A passing fitter can fail native serialization

The [small coordinate follow-up](native-wave-coordinate-v1.md) left all four
wave proposals rejected. A source-bound diagnostic screened 420 single/pair
choices at a 2e-7-radian radius and decoded three proposals: none satisfied
the full constraint vector. A larger scale-grid process disappeared before
terminal evidence; its absent handle, OS process check and released worker
lock are recorded separately. Its provisional numerical zero is not a result.
The interrupted output and source archives remain untouched.

A fresh scale probe stores progress and stops before paired screening when
its single-control screens already find zero excess. Of 60 screens, six are
independently decoded; one passes. The successful change is a -1e-5-radian
bend adjustment. Coupling is unnecessary for this known closest proposal.
Larger steps can fix its target row while introducing other failures.

The existing fitter then runs all four matched warm starts, each with one
coordinate iteration and a .0002-radian initial radius. That is an existing
permitted repair radius, within the unchanged original control boxes. The
source, authored stance, plane, displacement/angular limits, native key
clocks and four-bin 120 Hz caps with 1e-5 tolerance remain unchanged. No
production optimizer or selection gate is altered for this comparison.

| Proposal | Before failed rows | After failed rows | Initial worst excess | Final worst excess |
| --- | --- | --- | --- | --- |
| 1 | 8 / 4 / 1 / 2 | 8 / 4 / 1 / 2 | 0.0037830542 | 0.0037830542 |
| 2 | 1 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 3.22636415e-05 | 0 |
| 3 | 23 / 4 / 4 / 4 | 23 / 4 / 5 / 4 | 0.00700423531 | 0.00688001379 |
| 4 | 14 / 4 / 0 / 8 | 14 / 4 / 0 / 8 | 0.00203978617 | 0.00203675181 |

Groups are positional speed/acceleration and angular speed/acceleration.
Proposal 2 passes every fitter gate; the other three remain rejected.
Proposal 3 gains an angular-speed failure. A lower maximum normalized
excess therefore does not establish overall improvement.

Converting proposal 2's quaternion keys through editable float32 rotation
matrices and preview serialization produces **two positional-speed and one
angular-speed violation**. Sampled support height and edit bounds still
pass. Native conversion retains the exact input. Its root/rotation arrays
remain byte-for-byte equal to the selected input window, and unknown contact
labels remain unknown. An independent rerun with the new diagnostics
reproduces the same rejection and locates these three rows:

| Joint | Rate group | Interval (s) | Excess beyond cap plus tolerance |
| --- | --- | --- | --- |
| LeftShin | position_speed | 1.633333333–1.641666667 | 1.07339753e-08 |
| LeftToeBase | position_speed | 3.925000000–3.933333333 | 1.0908087e-07 |
| LeftShin | angular_speed | 0.233333333–0.241666667 | 1.58747585e-07 |

Position excess is in m/s and angular excess in rad/s. Small magnitude does
not make a failure a pass. These observations identify a representation
boundary for future correction; they do not authorize tolerance relaxation.
The next numerical repair must evaluate the actual native round trip rather
than assuming a passing pre-conversion GLB remains valid.

Godot 4.7.2 imports four fitter proposals, selected native input and rejected
native proposal: six clips/720 native frames, 77 bones, one skinned surface
and non-looping playback each. Joint sample differences are at most
5.437e-07 m and 9.795e-07
basis elements. CPU import fidelity does not establish GPU appearance or
animation quality.

## Drift is measured independently of support height

`native_contact_diagnostics.py` validates source/draft binding, matching native
clocks and identical mesh, skin weights, binds and node identities. It uses
all fully foot-bound region vertices to measure height, then freezes the
source vertex identities within 3 mm of the region minimum at stance start.
This is a defined lower-foot patch, not an inferred sole, measured pressure
patch or human contact annotation. It samples at 120 Hz plus exact authored
stance boundaries. Height never substitutes for tangential displacement.

The diagnostic projects displacement from each fixed vertex's starting
position and finite-difference velocity onto the plane tangent. It reports
maximum tangential drift/speed, minimum height, maximum lowest-vertex gap and
sampled penetration. Switching whichever vertex is currently lowest cannot
hide motion of the original patch. No additional acceptance gate is created.

On the development wave's authored 1.6–2.4 s left-foot stance, the fixed patch
has 14 vertices within a 1195-vertex foot region:

| Measurement | Input | Converted proposal |
| --- | --- | --- |
| Maximum fixed-patch drift | 4.879932 mm | 4.879948 mm |
| Maximum tangential speed | 28.614383 mm/s | 28.618025 mm/s |
| Sampled penetration | 2.034175 mm | 0.000000 mm |

The candidate clears sampled penetration while retaining roughly 4.88 mm
of drift. It does not establish planted feet. Native support reports now
include selected/proposed measurements; the viewer labels each explicitly.
Older saved reports show measurements unavailable instead of an invented zero.
The support-event file binds the actual selected preview hash and records
unverified status when that retained selection fails the authored screens.
These authored markers remain distinct from reviewed training contact labels.

Use the standalone diagnostic on provisioned local assets with:

```powershell
.venv\Scripts\python.exe scripts/native_contact_diagnostics.py source.glb candidate.glb support-draft.json fresh-contact-diagnostics.json
```

Eleven analytical/native geometry tests check sliding at zero floor height,
tilted-plane normal motion, source preservation, fixed identities, invalid
populations and changed payloads. A synthetic false fitter pass verifies that
Studio instead follows native rejection, selects the retained preview and
serves markers bound to that clip; changed marker evidence is rejected.
Offline text tests cover millimetre units, selected/proposed distinction,
missing/nonfinite values and safe text rendering. These are software checks,
not actual animator submissions or browser/GPU verification.

The full geometry/Studio selection completes 1,672 Python tests and 16
JavaScript suites. The separate CPU adapter/native-pipeline selection
completes 213 tests. After the final native audit-link update, 48 focused
geometry/bridge/Studio tests and the drift/audit-link JavaScript suite pass.
The earlier complete selections are not rerun for that isolated URL change.
Prior commit `88a0a9a` passes hosted workflow `37045109424`; new hosted
results are reported after publication rather than inferred in advance.

Local evidence remains excluded from the public source snapshot:

- `reports/native-wave-coupled-probe-v1`: completed small pair diagnostic.
- `reports/native-wave-coupled-scale-v2/interruption-observed.json`: preserved
  interruption record; no terminal success is inferred.
- `reports/native-wave-coupled-first-v3`: fresh terminal scale-grid evidence.
- `reports/native-wave-scale-canary-v1`: four normal fitter trials, native
  rejection and six-clip Godot evidence.
- `reports/native-wave-contact-bridge-v1`: current bridge, exact native
  retention, contact diagnostics and three localized conversion failures.
- `reports/native-contact-diagnostics-validation-v1/verification.json`:
  current public source and archived terminal evidence receipt.

All motions are historical development samples with numerical stance times
and earlier small root/forearm edits. There is no new model generation,
learned update, reviewed licensed corpus, human cleanup result or formal
held-out evaluation. Broad action/style, scene/object/partner/finger, rig,
physics/geometry and human release requirements remain unfinished. All 14
capabilities stay unapproved, the formal 72-by-five population stays untouched,
and the single full-project goal remains active.
