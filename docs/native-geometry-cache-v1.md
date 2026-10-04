# Complete geometry evidence with exact input reuse

`scripts/native_geometry_cache.py` captures every declared sampled scene condition and its numeric observations together with the complete inputs needed to reuse a sample. It provides a standalone offline command and Python API. The historical geometry kernel and existing study archives stay unchanged.

```powershell
# Capture a fresh complete cache while no other local action job is running.
python scripts/native_geometry_cache.py contacts.json geometry-policy.json reports/geometry-cache-v1

# Audit a separately saved candidate using that cache.
python scripts/native_geometry_cache.py candidate-contacts.json candidate-policy.json reports/candidate-cache-v1 --donor reports/geometry-cache-v1
```

The command acquires the existing single-worker lock and uses one numerical thread. An existing output folder rejects; failures retain their partial evidence and never produce an approvable completed cache. The lower-level `evaluate_to_cache()` API requires its caller to own the worker lock.

Reuse requires exact agreement of every placed actor vertex, triangle index, object shape and pose, declared plane and numeric geometry limit at the same exact clock. Actor, object and plane population order must also match. No joint-name rule, descendant guess, changed-vertex subset, small-difference cutoff or pose-clock thinning is used. Even a one-ULP vertex change triggers fresh measurement. Both actors of a partner condition are included.

Every changed or newly declared time receives a complete whole-scene query through the unchanged kernel. When querying a fresh subset, the kernel also requires both exact clip endpoints; those endpoints are queried again rather than relaxing its validation. All unchanged times remain in the final report with their full donor decisions, depth brackets and witness arrays. Stored failures remain failures. Per-sample provenance distinguishes fresh queries from exact full-input reuse, and numeric array names are remapped to the complete current clock.

The donor binds original input files, complete report, numeric archive, transport receipt, geometry dependencies and runtime versions. Complete archive transport is verified one array at a time. Changed files, changed loaded metadata, changed kernel/runtime, incomplete clocks or tampered provenance reject. The fresh kernel's actual vertex inputs must also match the equality-pass snapshots, so a mutation between comparison and query cannot silently create inconsistent evidence.

Additional complete vertex snapshots consume storage. The defaults allow 256 MiB per numeric array and 16 GiB total logical numeric bytes. The total budget may be explicitly set from 1 KiB to 1 TiB; overflow rejects the complete cache instead of dropping late samples. Logical-byte limits are not compressed-size guarantees, process memory caps or elapsed-time limits. Both limits can be supplied through the command's `--maximum-array-bytes` and `--maximum-logical-bytes` flags.

Only caches produced by this API can be used as donors. Older geometry archives do not contain these complete query-input snapshots and cannot be silently adopted. This implementation therefore does not retrofit or accelerate the already running 2,552-time candidate study.

All 31 new focused cases and 91 selected cache/geometry/transport tests pass from an isolated source copy without vendor code, models or downloaded characters. Source verification covers identical inputs with zero new queries, localized native edits, both actors of partner scenes, moving objects, new clocks, shapes, placements, winding/topology, planes, limits, condition ordering, one-ULP vertex changes, donor tamper, mid-query input mutation, worker locking and partial/total storage failure. Each successful fixture compares the entire report and every original numeric geometry observation against an independent fresh invocation of the unchanged whole-scene kernel. The first fixture run found an incorrect accessor-reader import; later ordering regressions demonstrated that equal dictionaries alone do not preserve object/plane population order. Both failures and their source snapshots remain local, and the repaired implementation has the final isolated source checks. These are synthetic source fixtures; production-character cache parity and timings remain unmeasured.

This is a geometry workflow improvement, not a motion/contact acceptance gate or quality certificate. Full point/surface contacts and motion rates still require separate measurements. The original geometry scope remains sampled declared actor/object, actor/actor and plane conditions; object/object, self-collision, continuous collision, exact arithmetic, engine playback and human realism are not certified. The API retains original selection and never grants release approval. No universal performance claim or full-character cache speedup is measured yet.

Local evidence: `reports/native-geometry-cache-clean-source-v3`, `reports/native-geometry-cache-repair-v1`, `reports/native-geometry-cache-order-regression-v1.log` and `reports/native-geometry-cache-source-publication-v1`. The current candidate study and its pending full independent replay remain separate. The full project goal and all release gates remain open.
