# Bounded rotation and translation key repair

The public native surface fitter now accepts an explicit
`strep-native-component-storage-repair-v1` policy. This extends precision repair
to authored translation tracks, addressing the uncovered root component in the
[replayed crawl candidate](studio-ground-continuation-v1.md). The earlier
rotation-only policy and continuation formats retain their behavior.

The policy binds the exact boundary-authoring digest and explicitly lists
`allowed_paths` as rotation, translation or both. It requires one adjacent
Float32 value per corrected component, at most 64 corrections and acknowledgment
of stored-key adjustment. Every correction names actor, node, path, native key
index, component and signed step. Translation has three components; rotation
has four. Scale and unselected tracks are unsupported. Correction identities
include the path, so a rotation and translation on the same node cannot silently
replace each other's adjustments.

The correction must lie in an existing authored key set. Clip edges require
explicit boundary permission; protected interpolation support remains excluded.
Original control boxes, strict track bounds, near-unit quaternion constraints,
clocks, static payloads and all unselected clips/tracks remain checked. Mutated
loaded policies, corrections or authoring contracts reject. Discrete changes
do not alter the intended continuous curve or replace the original source caps.

The typed planner considers translation of a joint or its ancestors only for
positional speed/acceleration failures. Angular failures use rotation tracks.
Own-joint rotation cannot move its joint origin. Direct positional failures on
an authored translation track receive planning priority, so a failing root is
not hidden behind descendant arm options. Original LINEAR interpolation support
and permitted native keys determine the finite choices. A choice can restore
the nearest value, replace a signed neighbor, or add a component; steps never
accumulate beyond the one-neighbor envelope.

Every exported probe receives fresh strict payload/authoring audits and complete
native decoding. Original row population, caps and scales remain bound. Authored
serialized rotation-speed limits are freshly checked when supplied. Intended
motion failures do not enter precision search. A failed search returns its
original proposal and retains every failed neighbor; a partially improved
candidate never becomes a passing repair. Successful exact-control reuse still
re-exports and freshly checks native conditions and bytes. Geometry is assessed
separately on the returned output and is never inferred from repair success.

`strep-native-component-storage-continuation-v1` saves typed corrections,
controls, original source hashes, authoring/policy digests and exact corrected
actor files. Loading it does not reset the source epoch or grant motion approval.
The public fitter selects the component implementation from the explicit policy,
archives its four additional method files and writes the typed final state.
Its existing `--storage-repair-policy` and `--storage-continuation` arguments
remain the entry points. Legacy rotation policies do not implicitly enable
translation. Studio's current v3 clearance request still uses the legacy
rotation policy; mixed precision repair and boundary choices need explicit UI
contracts in subsequent integration.

## Checks

All **213 related local checks** pass in one complete run, including 49 new
component/fitting cases and the existing rotation repair/search, continuation,
fit, authored-speed integration and Studio storage suites. Tests export actual
GLB neighbor changes and preserve other values; retain continuous curves, source
worlds/caps and byte-identical continuation; reject malformed policies,
unpermitted keys/paths, changed payloads, contract mutation and strict bound
violations; distinguish positional/rotational interpolation support; repair a
root-rate defect, recheck reuse, and run the public fitter/continuation both with
and without speed limits. A constant-root fixture isolates the effect of a
stored-key neighbor under zero original motion caps. This is software evidence,
not animation-quality or humanoid performance certification.

All **293 resource observations** independently replay under the unchanged
admission/memory/time policy. The earlier run retains its 203 passes and ten
failures: six from a fixture that borrowed acceleration allowance from another
source bin, and four from bypassing the legacy dynamic search hook. The constant
fixture and restored hook resolve those failures; all 298 earlier resource
observations also replay. Raw checks remain local under
`reports/component-storage-checks-v1` and `reports/component-storage-checks-v2`.
Inventory is now 472 Python test modules / 42 Node suites. Hosted checks for the
new implementation are separate from this local result.

The previous [full source run at `7f50b21`](https://github.com/DocMorphic/strep/actions/runs/38191029137)
now completes successfully in all twelve jobs. Its declared inventory is
469 Python modules / 42 Node suites. Each OS's four core shards pass 9,132
checks with seven skips and 50 subtests; adapter/material jobs also pass, but
their overlapping cases are not added to that core total. That revision predates
Studio storage integration and this component implementation. Current complete
hosted coverage must not be inferred from the older result.

## Actual crawl trial and replay

The fixed-candidate trial starts from the earlier best failed rotation-only
neighbor (four corrections, 46 failed native rows). The exact 63 controls,
original asset, cap arrays and rate clock stay unchanged. An explicit mixed
policy permits rotation/translation corrections, with 8 stages / 16 probes per
stage. Every proposal uses all 107,895 native conditions and all intended
conditions pass. This is reused development data, not held-out evidence.

The search retains 53 fresh native exports and completes at **350.891 s
execution**; all 363 resource observations replay. Its best greedy-merit anchor
has 44 failures and twelve typed corrections. One correction is translation
of root node 21, native key 54, component 2, by one negative adjacent value.
The previously failing root acceleration at row-frame 215 now passes, and all
other original root acceleration rows pass too. This removes the measured
rotation-only coverage limitation for this fixed candidate.

Some searched neighbors have as few as 38 failed rows, but the greedy merit
score optimizes normalized excess rather than failure count alone. No candidate
passes every native condition. The partial anchor remains rejected; the
returned file retains the initial four corrections and 46 failures. Its full
floor audit still fails every one of 2,017 times at **257.398701 mm** peak.
Geometry of the rejected best anchor is not approved or claimed as measured.

A separate replay reconstructs returned and best files byte-for-byte, all
native worlds/residuals, original control/cap/clock data, and byte-identical
typed continuation for each. It confirms root row-frame 215 fails in the returned
seed and no root acceleration row fails in the best anchor. Every returned
floor sample is freshly recomputed and identical. All 53 probe arrays/assets
receive hash validation; other neighbors are not numerically replayed.
The replay completes at **37.672 s execution** and all 55 resource observations
replay. It shares repository decoding/constraint/geometry arithmetic and is
not an independent mathematical implementation.

Evidence remains under `reports/crawl-component-repair-v1` and
`reports/crawl-component-replay-v1`. No new model generation, training admission,
held-out reservation, engine, renderer, live browser or human approval follows.
The next repair study must preserve this root correction and original epoch
while investigating the remaining conditions; more search steps are not proof
of feasibility. Complete clearance, scene/partner interactions and human
animation quality remain separate requirements.
