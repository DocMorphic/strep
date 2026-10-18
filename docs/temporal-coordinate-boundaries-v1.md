# Temporal-coordinate conversion and storage boundaries

Development correction, 2026-10-18. This hardens the
[frame-local timing mapper](frame-temporal-controls-v1.md); it changes no
animation, rig, model checkpoint, physical threshold or selected asset.

The pre-fix probe reproduces two accepted-input defects. Float32 temporal
weights `[0.1, 0.2, 0.7]` sum to one in Float32, but their owned Float64 sum is
0.9999999925494194. Embedding a source control therefore changes its frame
values. Similarly, Float32 `[0.8, 0.6, 0]` has a computed Float32 norm of one,
but its owned Float64 norm is 1.000000023841858. The old input check accepts a
control that exceeds the bound in the coordinates actually used.

The constructor now validates the owned Float64 partition too, and control
conversion checks the owned Float64 ball. Neither path normalizes or clips the
input. Exactly representable Float32 partitions and controls remain supported.
These are temporal-coordinate checks, not changes to character skin weights.

The lift's 64 MiB complete-model allowance also assumed eight-byte input
elements. Platforms with wider `longdouble` inputs could need more live storage
than that estimate. Admission now counts actual input bytes and promoted
product/validation storage, retaining the previous conservative allowance for
narrower inputs. Finite/range validation runs in bounded row chunks before the
full output is allocated. Oversized models and invalid tail rows reject without
output allocation or missing rows. The 64 MiB limit is unchanged.

All **358 focused cases pass locally**, including the previous 349 and nine
new boundary cases. Tests cover both reproduced conversion defects, accepted
exact Float32 inputs, input/output storage admission with platform double and
long-double types, and invalid values in the final validation chunk. Allocation
spies ensure rejection occurs before output creation. The wider-dtype case is
platform-dependent; the local Windows long-double type occupies eight bytes.
Hosted operating-system results are recorded separately when complete.

Historical evidence stays tied to its actual implementation. The pre-fix
source and test are recovered byte-for-byte from public commit
`fc66877414b9faf695f0cb7e771cf598c53da3da` into a fresh source-epoch archive.
Old reports and their hashes are not rewritten to refer to the new source.

A fresh compatibility reader computes the original 6,968 frame-local rows and
all 216 expanded columns with both implementations, then compares both results
against the saved model. **Every geometric Jacobian byte matches**, as do
embedded controls and all 120 frame-control evaluations. The original complete
Float64 budget is 16,260,352 bytes: both versions admit exactly that allowance
and reject one byte below it. Thus the tested historical Float64 computations
and their admission boundary remain unchanged. The 16 global derivative rows
are outside this mapper and are not rerun or reclassified.

Local evidence: `reports/temporal-coordinate-boundary-probe-v1`,
`reports/temporal-coordinate-boundary-tests-v1`,
`reports/temporal-coordinate-historical-sources-v1` and
`reports/temporal-coordinate-compatibility-v1`. Numerical checks retain a
512 MiB process-tree cap and tensor tests 2 GiB, both with the unchanged
600 MiB free-memory reserve. Earlier body/normal failures, held-out evaluation,
engine/runtime limitations and genuine human review remain open. The
whole-project goal stays active; this is not motion or release approval.
