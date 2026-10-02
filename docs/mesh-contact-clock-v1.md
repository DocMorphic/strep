# Explicit contact timing and serialized playback constraints

Mesh-contact fitting now distinguishes authored-key contact from a contact held
through the full frame interval. Playback fitting evaluates float32 mesh contact
values, and independent export inspection rejects failures on the selected
clock. This closes two measured gaps in the previous
[playback guard experiment](crawl-body-contact-playback-guards-v1.md): the
previously passing shin exceeded 20 mm during its full frame interval, and two
retained proposals exceeded that cap after serialization.

## Authored meaning

`--contact-clock authored-keys` is the default: check every active authored
frame's float32 timestamp. `--contact-clock frame-hold` explicitly requests
sampling from the start-frame timestamp up to, but excluding, the end-frame
timestamp. The hold includes the tail after the last active key. It intersects
the available animation duration; the final frame is not extrapolated past the
clip. Native keys, channel midpoints and 120 Hz samples are included. Finite
sampling is not proof that contact holds at every instant.

The draft's patches, target positions, intervals and numerical limits stay
unchanged. The chosen clock is an additional request condition, recorded in the
request and trial metadata. A key contact and a held contact are different
conditions; switching clocks is not a like-for-like performance comparison.
Neither clock establishes anatomy, intended support or action correctness.

## Fitting and export

Every `--playback-guards` fit now adds quantized contact constraints, including
in the default authored-key mode. A patch centroid is computed from the full
weighted skin's aggregated bind-space contributions. Continuous central finite
differences through both neighboring baked TRS endpoints provide derivatives
for quantized values. Actual exported GLB decoding independently checks those
values. They can differ slightly; the adapter is not a substitute for the
independent acceptance screen.

An input interval is protected only when all its original key and selected
playback contact samples pass. The protected row mask remains frozen across
floor restoration, contact pursuit and final measurement. Trial retention
requires those values to pass the exact cap without the previous normalized
negative allowance. A passing raw key cannot override a failed quantized sample.
Protection at sampled values is not a general continuous or serialized
certificate; independently decoded retained proposals still need evaluation.

The existing bounded root-lift restoration, edit/step limits, floor screen,
inner optimization margin, proposal archives and input-retention behavior remain.
Default non-playback fitting math stays unchanged. All mesh-trajectory export
modes now save `playback-contact-inspection.json` and add
`decoded_contact_clock_screen_failed` when the selected contact clock fails.
The independent full-surface playback floor gate remains mandatory.

The mode is now available as an experimental finite-clip
[Studio submission option](studio-mesh-playback-v1.md), with saved choices,
failure visibility and explicit periodic-clip rejection. For an explicit CLI
held-contact study:

```powershell
.venv/Scripts/python.exe scripts/rig_mesh_trajectory.py --source character.glb --spec draft.json --output reports/new-hold-study --feasibility --guarded-trials --playback-guards --contact-clock frame-hold
```

Use a fresh output directory. The draft must be bound to that source and contain
reviewable patches and contact targets. Output selection remains separate from
quality approval, and failed candidates remain available alongside the input.

## Validation and current study

All 1,564 model-free Python tests and 14 JavaScript suites pass. Eighteen new
cases cover exact half-open boundaries, overlapping clocks, multi-patch exported
full-mesh parity, independently evaluated continuous derivatives, derivative
cache invalidation, final-frame clipping, source mutation and invalid modes.
A synthetic serialized contact crosses the 20 mm cap while its raw key passes;
the proposal is rejected before retention. Another actual GLB passes its
authored key, floor and controlled solver fixture but is rejected solely by the
full-frame contact export check. These fixtures establish software behavior,
not human-motion realism.

A fresh exploratory study uses the same original Cesium crawl, unchanged draft,
13 by 45 controls and declared 30/60 floor/contact budgets, with the explicitly
added frame-hold condition. The [completed study](crawl-body-contact-frame-hold-v1.md)
preserves its sampled floor and protected hold through all 55 independently
encoded/decoded retained proposals, but still fails the other three contacts
and retains the original. Its immutable request, implementation and outputs are
local under `reports/crawl-body-contact-frame-hold-v1/`. The authored-key
comparison stays unchanged. Matching iteration budgets does not imply equal
computation, and the changed hold condition is not an equivalent request.

No inference, training, new seed, formal held-out use, browser/GPU rendering,
submitted human review or cleanup timing occurred in this implementation batch.
All 14 release capabilities remain unapproved. Reviewed contact anatomy/timing,
broader arbitrary action,
scene/partner, edit/style, rig, loop/transition and import validation remain in
the project-wide goal.
