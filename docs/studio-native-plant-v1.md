# Explicit planted-contact correction in Studio

Native foot-support editing now offers **Plant feet against sliding**. An author
chooses stance times, native edit keys, a plane and cumulative edit bounds, then
sets maximum patch anchor error and patch speed. The selected source is preserved;
every failed alternative remains available. Contact precision cannot override
support, motion-rate or editable-native conversion failures.

## Authoring and selection

The option is available in both character and native correction-review support
panels. Anchor error is entered in millimetres and speed in millimetres/second;
the request stores metres and metres/second. Defaults are 1 mm and 5 mm/s. These
are editable development choices, not validated realism standards. The same
limits apply to each explicitly authored support interval. A new source load
resets the option and its limits; the original support draft schema stays intact.

Planting is an explicit alternative to between-key refinement and the older
knee-plane/orientation search. It requires an already rigid input; tiny-scale
preparation must be performed separately. Client requests cannot supply model
paths, warm seeds, iteration counts, trust radii or tolerance overrides. Precision
is bounded to 0–30 mm anchor error and 0–100 mm/s patch speed. These ranges bound
the configurable requirement; changing a limit creates a different requirement.
The solver never silently widens it.

The server snapshots the original GLB, draft, planting policy and method versions.
The policy binds source, input and draft by hash and names every support. It fixes
the original foot-patch vertex identities and each point's source stance-start
tangent anchor, following [joint native planting](native-joint-plant-v1.md).
Native root/other translations, unrelated tracks, boundary/outside keys,
mesh/skin payloads and key clocks remain protected.

An exact IK centering proposal seeds at most eight joint minimax/L1 iterations at
.001 radian trust. If centering rejects an unreachable ankle target, the original
input seeds direct rotation search instead; no reach clamp is introduced. If the
joint proposal still fails, a separate phase uses at most eight bounded coordinate
iterations at 2e-6 radian trust. Both inspect raw GLB and shadow editable FP32-matrix
representations. An already satisfactory input bypasses the coordinate phase.
Per-phase controls, rejected exports and independent decoded audits remain saved.

For native review clips, the actual NPZ and preview conversion independently
rechecks fixed-patch anchor/speed, authored clearance, support gap, cumulative
movement/angle bounds and original selected-source motion caps. Failure selects
the exact prior native pose tracks and preserves the failed native proposal.
The final Studio decision, selected preview, planting audit and event markers
follow that actual conversion. A raw fitter pass cannot substitute for it.
These additions are opt-in; older support-only requests keep their existing
selection behavior and report planting as unavailable.

Preview text separately displays drift diagnostics, explicit source-anchor/speed
limits and full configured acceptance. Invalid measurements remain unavailable;
rounded text cannot turn an over-limit measurement into a pass. Proposal rows
link to planting audits and saved controls. Event markers reference the selected
clip's hash and mark unmet configured requirements as unverified. They are authored
stance intervals, not measured contact forces or human contact annotations.

## Development evidence

A bounded follow-up to the prior CLI wave completes 216 coordinate screens at
2e-6 radian trust and accepts one step. Both raw and shadow constraint populations
reach zero positive deficit. The separate actual editable-native conversion then
passes all configured contact/support/rate gates: maximum fixed-patch source-anchor
error is 0.513110 mm, speed is 4.999737958 mm/s and rate failures are 0 / 0 / 0 / 0.
Only the left thigh, shin and foot change in this leg operation. Roots retain the
selected input's earlier edits; this does not imply the original model output was
untouched. Three exported versions cover 360 headless Godot native frames with
77 bones, one skin and non-looping playback; maximum position error is 5.437e-7 m
and basis-element error 9.795e-7.

That result remains one historical development wave with numerical stance
choices. The original kick and crawl failures remain rejected and immutable.
A successful source-relative screen is not an independent animation benchmark,
a universal planting result, human realism review or held-out release approval.

The separate actual Studio canary starts from the previously accepted height
correction. Its source anchors and rate caps therefore reference that selected
clip rather than the earlier uncorrected source. Eight joint iterations leave
three failing rate rows; five coordinate iterations then satisfy raw and shadow
populations. Actual native conversion independently passes every configured
gate. The selected preview has 0.509833 mm source-anchor error, 4.999993940 mm/s
patch speed and zero rate failures. Sampled support height ranges from 0.253335
to 1.936237 mm; the largest ankle change is 6.586550 mm and local angle change
1.017737 degrees. The failed joint alternative stays available.

The Studio manifest, actual selected NPZ/GLB and source-bound stance markers
agree. Five exported versions cover 600 native Godot frames with 77 bones, one
skin and non-looping playback; maximum position/basis errors remain 5.437e-7 m
and 9.795e-7. This establishes the offline backend path and import fidelity;
rendered browser/GPU appearance and engine-interpolated contact precision are
separate, unverified questions.

84 focused model-free Studio/support tests and 215 CPU adapter/native pipeline
tests pass, together with four desktop bundle checks and offline editor/formatter
fixtures. Coverage includes explicit precision, mode isolation, actual retained
failures, satisfactory inputs, source/policy/method tamper rejection, pose/event
binding, exact unit conversion and actual contact measurements overriding a
support-only fixture stub. The latter isolates a branch and is not physical
animation evidence. Source CI includes the new planted-support tests. Previous
commit 9ae5954 passes all four hosted jobs in workflow 37064099803.

The CLI follow-up is retained at
`reports/native-joint-plant-coordinate-followup-v1`; Studio development evidence
is retained in `reports/studio-native-plant-canary-v1`. A source/evidence receipt
is kept in `reports/studio-native-plant-validation-v1/verification.json`.
Live browser/GPU appearance is not verified by these
offline tests or CPU imports. Models, characters, credentials and generated
studies stay excluded from public Git. No real model update, human submission
or training admission occurs. All 14 release capabilities remain unapproved,
formal 72-by-five evaluation is untouched and the full project goal stays active.
Broader action/style, object/partner/finger and rig behavior, continuous geometry,
force/balance plausibility and human cleanup/release evidence still require work.

The final full source selection passes 1730 Python tests and 16 JavaScript suites. The project-owned idle Studio process is refreshed after terminal workers and checks; only its process identity and loopback listener are observed, with no live HTTP/browser or GPU claim.
