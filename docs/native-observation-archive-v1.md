# Streamed numeric observation archives

The expanded humanoid actor stage now completes at all 2,201 original/key-union
times. Pose, original Node3D object transforms, contacts, complete imported skin
and declared sampled geometry pass. The maximum source-relative vertex error
remains 0.0950103 mm against the original 0.1 mm limit; all 4,402 actor/object
geometry observations pass. This is the actor producer, not the final combined
comparison with actual saved/reloaded object resources. That combined stage
remains in progress. No world plane or partner is declared in this case, and
no human, GPU, runtime or physics approval follows.

The worker was observed reserving 8.10 GB of private process memory. For this
2,201-time, two-object, 36,108-face population, lower/upper depth bounds and three
witness coordinates alone represent 6,358,472,640 logical bytes of Float64 data.
Reducing sample times, faces or precision would change the measurement contract.
`native_observation_archive.py` instead writes complete arrays incrementally to
an ordinary compressed NPZ without retaining earlier array values.

```python
from native_observation_archive import ObservationArchive, verify

with ObservationArchive(output / 'observations.npz') as observations:
    observations['times_s'] = complete_times
    for name, complete_array in complete_observations:
        observations[name] = complete_array

transport_check = verify(output / 'observations.npz')
```

This is a storage component, not a geometry evaluator. The running study and
existing scene evaluators remain unchanged. Integration must wait for the
current combined study and its terminal replay; the component does not claim
that the live worker's peak memory is already reduced. No complete-population
memory benchmark has been performed.

Each assignment snapshots one whole array, preserving dtype, shape, logical
bytes and ordering. It neither downcasts nor filters nonfinite diagnostic
values. Plain numeric arrays are supported, including complex and endian-specific
data; objects, strings and dtype metadata reject explicitly. The original array's
values, shape and dtype are rechecked around writing. Previous arrays are retained
only as small receipts, not as values. The default per-array budget is 256 MiB;
oversized arrays reject as a whole rather than returning a truncated population.
The working lifetime is one complete array plus hashing/compression buffers,
not all frames. This is an allocation/lifetime property, not a measured total
process-memory ceiling.

Output starts in a fresh `.partial` archive. Completion checks the exact entry
population and publishes through a fresh filesystem hard link; existing or
racing targets are never replaced. A filesystem that cannot perform that link
retains a failed partial instead of falling back to overwrite. The complete
receipt is written exclusively. Failed writes preserve completed array receipts
and the actual partial bytes; failed finish/caller operations remain failed.
Existing archives/receipts are never reused automatically.

Verification checks raw archive and receipt hashes, exact ordered entries,
safe flat names and NPY headers before array allocation. It enforces its own
per-array budget, complete payload sizes and plain numeric dtype restrictions.
Then it reads one array at a time to verify every shape, dtype and logical byte
hash. It refuses changed values even with an updated container hash, duplicate
entries, oversized/malformed headers, missing observations and promoted scope
flags. Original archive/receipt hashes are rechecked after reading. A receipt
with a retained failure cannot be promoted to complete transport verification.

## Validation and actual transport sample

All 38 focused tests pass. They include scalar, empty, strided, Fortran-layout,
endian-specific, complex, boolean, nonfinite and explicit NaN-payload values;
original-byte preservation; released previous array lifetimes; per-array rejection;
partial failures; source value/shape/dtype mutation; competing targets/receipts;
changed data despite updated hashes; and header rejection before allocation.
These are transport tests, not model, engine or collision measurements.

A separate actual-data round trip uses the completed expanded actor producer's
entire 2,201-time vector and all triangle arrays at frames 0, 1,100 and 2,200 for
both objects. All 19 supplied arrays retain their exact dtype, shape and logical
bytes: 8,683,528 logical bytes. Original source archives/reports and implementation
hashes remain unchanged. This explicitly selected transport sample is not a
full geometry replay or a new query. The other time arrays are not claimed
validated by this round trip; the writer API does not select or discard them.

Ignored evidence lives in `reports/native-observation-archive-development-v1`.
The preceding single-job commit passes all four Windows/Linux hosted checks.
All release capability gates, formal held-out trials and human cleanup/review
requirements remain open. Next: finish and replay the current combined producer,
then integrate streamed archives into the complete scene workflow while retaining
the original query population and exact numeric values.
