# Explicit static-joint rotation variants

The offline editor previously required an existing animation channel. A skin joint with a static rotation could not be articulated through a permission change alone. `scripts/native_static_rotation_variant.py` now prepares a separate clip with explicitly requested constant rotation curves. Every original animation, the original binary prefix, static asset metadata, and existing selected-channel clocks, values and interpolation remain unchanged.

## Prepare a separate clip

```powershell
python scripts/native_static_rotation_variant.py --request path/to/preparation.json --output reports/new-static-variant
```

The output directory must be fresh. The strict `strep-native-static-rotation-variant-v1` request supplies:

- `source`: file `path`, exact `sha256`, and integer `animation_index`.
- `nodes`: 1–16 distinct existing skin joints without a rotation channel in that clip. Matrix nodes are rejected.
- `clock_from`: an existing channel's `node` and `path`. Its clock must include zero and the exact clip end.
- `sample_times_s`: explicit sorted unique samples, including both endpoints.
- `limits`: `matrix_error_max` and `vertex_error_max_m`, each between 1e-12 and 1e-5.
- `label`: a nonempty variant name, and `acknowledge_float32_pose_drift: true`.

The command normalizes each original static quaternion and stores its nearest Float32 value at every template key in a LINEAR curve. It appends a new animation, preserving originals. It measures actual sampled world-matrix and skinned-vertex differences against the original selected clip. The complete fidelity clock includes supplied samples, every existing native key and interval midpoint, and uniform 120 Hz samples. More than 20000 combined samples rejects preparation instead of returning a successful subset.

Static node transforms can carry precision greater than Float32. Adding a rotation channel therefore does not imply identical poses. A completed preparation can fail its declared fidelity limits; its report remains unapproved and originals remain selected. Reports archive requests, source bytes, implementation identities and observations. Invalid preflight requests create no output, and processing failures retain diagnostics.

## Retain original references in correction jobs

`scripts/native_stored_pair_job.py` continues accepting its v1 contract. A new `strep-native-stored-pair-job-v2` request additionally requires a pinned `static_reference_tracks` file:

```json
{
  "schema": "strep-native-static-reference-tracks-v1",
  "source_scene_sha256": "<derived-source-scene SHA256>",
  "reference_scene_sha256": "<original-reference-scene SHA256>",
  "actors": {
    "A": [{"node": 7, "path": "rotation", "clock_from": {"node": 6, "path": "rotation"}}]
  },
  "acknowledge_original_static_baselines": true
}
```

Each declaration must identify a permitted rotation track absent from the original reference animation. Its derived source curve must exactly contain the normalized nearest Float32 original static quaternion. Its clock must match an existing template in both source and original reference, including exact clip endpoints. Duplicate, unedited, missing, implicit or incorrectly pinned tracks reject the job. Existing animated references cannot be replaced by static declarations.

Track-change checks compare added curves with the original static quaternion at its original precision. Joint displacement still compares actual motion with the original reference worlds. Every original motion-rate array is exactly recomputed from the original reference; contacts and geometry retain their declared conditions. The v2 result and input snapshots identify this explicit binding, and per-track reference results label it `original-static-transform`.

This is a separate declared authoring experiment. It does not enlarge old submitted permissions, replace reference assets, reset cumulative limits or automatically select a candidate.

## Validation and retained fixture

Sixty-six focused CPU tests pass in 67.02 seconds, zero skips: 15 preparation tests, 12 static-binding job tests, and 39 existing job/model/crossing tests. They include high-precision pose drift, exact original payload preservation, every sampled observation, declared fidelity failure, invalid requests, original reference/cap retention and a complete six-control v2 model/solver/export/geometry audit. The existing v1 complete job also passes. CI includes both new suites; hosted CI success is not claimed.

A preparation on the retained generated development fixture adds node7 rotation using node6's 290-key clock. The two original actor files have identical bytes and selected indices; one prepared payload serves as the numerical preparation evidence. All five original animations remain, and the new variant has index5. Across all 1707 fidelity samples, maximum matrix-element drift is **5.528258822939947e-10**, and maximum skin displacement is **1.3834041657582919e-10 metres**. Both satisfy the explicitly declared 1e-7 limits; neither world nor skin observations are byte-identical.

A separate consumer imports no new preparation/job/model code. It verifies the complete old library and binary prefix, static metadata, every old channel, the added seed and clock, every saved sampled world/skin error and unchanged original reference/rate-cap hashes. It uses the existing rig loader and native sampler; those implementations are not independently reimplemented.

No enlarged correction study or geometry reassessment ran on this retained fixture. Its prior 5.100709 mm penetration and 30432 triangle records remain unresolved. Numerical generated-fixture evidence does not approve humanoid realism, interactions, physics, engine playback or human cleanup performance. All fourteen release evidence arrays remain empty, and the full-project goal remains active. Next bind the separate articulation experiment to the original reference and limits, validate its actual baseline, then measure whether the additional joint freedom helps correction.

Large local assets and observations remain ignored. Receipt SHA256 identities:

- Preparation: `4dfc387993b8be39d1378b4bc871bbc227d00800f15039249f637b3d5a6ad76d`.
- Consumer replay: `dfca53bdce599e400e50200393b037c793a5e2610244ce4b559607b42033a41d`.
