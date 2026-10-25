# Reusable surface clip context

`scripts/surface_clip.py` removes the get-up experiment's fixed asset paths,
joint-role names and animation-zero assumption from window preparation and
decoded validation. Callers supply a decoded rig, the selected animation,
editable skin-node IDs and angular limits, explicit material-vertex contact
phases, acceptance limits, fitting reserves and a bounded sampling policy.
Studio invokes this component through the explicit
[Ground-contact cleanup](studio-surface-clip-v1.md) workflow.

The context validates the original geometry, untouched animation channels and
shared native LINEAR clock using the same layout validator as the key exporter.
It supports consecutive windows of two to eight keys, freezes the incoming key by default,
and evaluates every native key, interval eighth and declared dense-grid time.
An oversized clock is rejected before allocation, rather than subsampled.
Contact phases use explicit static world positions and closed time intervals;
overlapping phases for the same material vertex are rejected. Empty contacts
permit floor-only checks. The floor is the world Y=0 plane.

Acceptance uses the supplied original limits. Smaller internal fitting limits
reserve room for serialization and interpolation errors without widening those
acceptance limits. Step checks bound changes in correction parameters, not the
character's physical speed. Exported candidates are decoded again and checked
for source identity before their complete requested sample population is tested.
Nonfinite or incomplete mesh/control arrays cannot pass the numerical checks.

Thirty new tests cover a separately named fixture rig, selected animation one,
unchanged other animations and geometry, contact activation, input copies,
nonuniform Float32 clocks, complete sample populations, native window solving
and export, and malformed contracts. Together with thirteen existing key-export
and twenty feasibility tests, 63 tests pass. Both CI source-test inventories
include the new module (651 full and 200 focused Python test files).

The full KayKit get-up comparison in `reports/surface-clip-replay-v1` reproduces
the frozen experiment's reports exactly for both clips, at all 7,129 sample times
per clip. The original transfer fails at all 7,129 times; the corrected candidate
has zero failed samples and passes the correction-step checks. Three windows
at keys 0-2, 89-91 and 177-179 also have identical decoded controls, bounds,
initial sample populations and complete dense results. The comparison performs
no new solve and does not broaden the earlier get-up quality claim.

Source hashes and recorded resource decisions verify for both the 63-test run
and the clip comparison: 266 observations in total, maximum sampled worker-tree
memory 150,626,304 bytes. The comparison finishes in 232.281 execution seconds.
The local publication verifier also checks the saved sample counts, failure
decisions and CI inventories. Historical experiment files remain unchanged;
their relocated paths are resolved in memory using the storage-consolidation
map. The earlier ordinary-import endpoint clock failure remains unresolved.

This component does not run a rolling coordinator, select contacts from a text
prompt, support moving targets, check triangle/self/partner collisions, verify
physics or approve motion quality. Source pinning, resource admission and
checkpoint publication remain job-wrapper responsibilities. The broader Studio
scene checker remains a separate part of acceptance.
No model weights, training data or character payloads are included here.

## Job and Studio integration contract

The [rolling job](surface-clip-job-v1.md) binds the source, initial candidate, selected animation,
contact phases and implementation hashes to an immutable request. It must
validate the incoming pose before freezing it, save every rejected candidate,
and advance a checkpoint only after decoding and auditing the exported window.
Continuation must verify the preserved prefix and source bindings; a stopped
job must retain its last accepted clip. A complete final audit is required even
when every individual window passed.

Studio exposes that job through its existing resource-guarded request,
status and continuation lifecycle. Its full scene collision and engine checks
remain separate from the flat-floor surface solver. A numerical candidate must
remain explicitly unreviewed until the requested human and cleanup evidence
arrives. Passing the development get-up comparison does not validate a new
action, rig, object or partner interaction.
