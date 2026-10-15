# Displacement witnesses on the native interval clock

`KeyIntervalModel.displacement_diagnostics(value, worlds)` reports every joint
displacement failure with its original norm-row number, joint/node, exact clock
index/time, measured displacement and unchanged limit. The caller supplies
complete finite world matrices on the model's clock. Omitting `worlds` uses the
existing quantized preview; that is not independent native export validation.

The existing displacement block is **joint-major, then time**. In the original
NumPy expression, the advanced joint index and the separated final scalar index
put the joint dimension before time. Reading the flattened block as time-major
can therefore label a correct numerical failure with the wrong joint and time.
The new diagnostic independently reconstructs that whole block with explicit
scalar joint indexing, then requires exact equality with every original vector
and displacement cap before producing labels. Its maximum witness uses the
first original row on ties. Failure uses the same strict bound as the existing
positive-scale norm residual; no extra tolerance or rounding is added.

The numerical row order, source caps, solver, exported animation and acceptance
are unchanged. This addition attributes failures; it does not make a failed
clip pass. Rotation, point-contact, motion-rate, floor, complete scene geometry,
engine and human-quality checks remain separate. Caller-supplied matrices do
not themselves prove that a native export or engine produced those matrices.

## Verified local behavior

All **41** affected checks pass in **212.58 seconds**, covering the interval
model, affine native seeds and selected-track restoration. Five new cases check
unequal joint/time populations, analytic failures at distinct joints and times,
unchanged source/norm arrays, narrow pass scope and malformed/nonfinite worlds.
The existing actual-GLB fixture also checks the diagnostic against explicitly
indexed decoded positions. The 512 MiB CPU guard completes in **228.984 seconds**,
peak **156,905,472 bytes**; all **225** resource observations replay. No test
module is added: the declared inventory remains 518 Python modules / 45 Node
suites, with 82 Python modules / five Node suites in the contact/rig subset.

A fresh process decodes both actual high-five candidate GLBs on the complete
original interval clock. Every saved source vector, candidate vector, cap,
scale, residual and original rate-cap array matches exactly. Every reported
failure is then checked against its explicitly indexed source/candidate joint
position. The only changed production module adds this diagnostic method;
removing that method gives the exact prior parsed Python syntax tree.

| Actor | Failed displacement rows | Actual failure interval (s) | Maximum joint displacement | Actual peak time (s) |
| --- | ---: | --- | ---: | ---: |
| A | 15 | 1.143750–1.170833 | 50.145154 mm | 1.1666666269302368 |
| B | 192 | 1.175000–1.258333 | 53.348320 mm | 1.2000000476837158 |

Both maxima belong to node 57, named `RightHandMiddleEnd`, under the unchanged
50 mm bound. The earlier time-major interpretation incorrectly attributed the
largest rows to other fingers at about 2.9 s. That report remains preserved;
its time/joint labels must not guide another edit. The numerical failures and
their counts were correct, and remain failures.

The candidate world matrices are exactly unchanged outside the intervals
influenced by modified native keys: A 0.6333333253860474–2.200000047683716 s,
B 0.6333333253860474–1.6666666269302368 s. Root and endpoint matrices remain
exactly unchanged. Thus this observation was a reporting error, not evidence
of unexpected edits at 2.9 s. The static pose's displacement bound still does
not guarantee the interpolated curve stays within that bound.

The fresh replay's 512 MiB CPU guard completes in **94.390 seconds**, peak
**278,216,704 bytes**; all **95** resource observations replay. Records remain
under ignored `reports/high-five-native-displacement-replay-v1`; earlier raw
results and incorrectly attributed reports remain intact. This replay does not
requery floor/scene geometry or reexecute the engine. All prior collision,
floor, motion-rate and release failures remain unresolved; no clip is adopted.

The [focused hosted workflow](https://github.com/DocMorphic/strep/actions/runs/38699445093)
at `d1a1110628150849a738de4f7020782c33a3b265` passes all **14 interval-model
checks per OS**: Ubuntu 4.43 seconds and Windows 113.72 seconds. That selected
module includes the five new cases and nine earlier checks; it is not a hosted
rerun of all 41 locally affected checks or the full source inventory.
