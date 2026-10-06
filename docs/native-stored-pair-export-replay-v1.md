# Reusable stored-pair export replay

`scripts/native_stored_pair_export_replay.py` checks every actual export from a completed v1/v2 stored-pair correction study. It uses existing boundary edits, native samplers and motion/contact conditions, while manually reconstructing the absolute Float32 neighbor choices. It does not import the producer job, correction model, storage wrapper or stored-curve proxy.

```powershell
python scripts/native_stored_pair_export_replay.py --study reports/my-study/result.json --output reports/new-export-replay
```

The output directory must be fresh and outside the immutable study directory. Original input files, source assets and the producer's archived/current implementation must remain available with matching hashes. The study must retain its complete artifact population, request, snapshots and every requested fraction. Changed bindings, escaped or omitted artifacts, and altered fraction populations are rejected. This is a local reproducibility command; the producer's snapshots are not a self-contained asset bundle.

The replay recomputes the original rate arrays, restores original reference worlds for edited actors, and keeps actual source playback for frozen actors. For the anchor and every fraction it checks exact controls, permitted stored channel payloads, authoring audits, decoded actor worlds and native residuals. Every original contact and native failure count remains visible. Cumulative displacement uses every native sample, including times outside the uniform rate clock. Animated and explicitly bound static-reference tracks keep original clocks, transforms and limits.

Saved geometry clocks, limits, scores and observation-archive transport are checked. Geometry predicates, derivatives, affine reductions and solver optima are not independently recomputed by this command. A computationally complete replay can faithfully reproduce rejected motion; it grants no asset selection, engine, physical realism, semantic, animator or release approval. Processing failures retain an implementation archive and failure record; prior outputs are never overwritten.

## Validation

The initial focused suite passes **21 CPU tests in 90.63 seconds, zero skips**. An additional rate-cap regression passes **one test in 5.50 seconds**. Together these cover 22 distinct cases. Integration cases use actual complete v1/v2 model, solver, export and geometry studies on generated development fixtures, including frozen partners and static-reference binding. Rejections cover changed provenance, omitted artifacts, path escapes, altered observations and worlds, falsified reference bounds, boolean failure counts, fraction changes, geometry scores and omitted exports. A fully rehashed and rebound weakened caps file still fails recomputation from the original reference. Sources, original clips and producer observations stay unchanged. Hosted CI success is not claimed.

After adding explicit rejection of altered original-selection or approval flags, the final suite passes **24 CPU tests in 99.32 seconds, zero skips**. The earlier runs remain retained. CI includes this suite alongside the existing correction and repair suites.

The command also replays the complete retained sixty-control correction study below. All exported payloads, worlds and 29870 native conditions match exactly at all 1707 native times; every original reference bound matches. All four complete geometry transports retain 1673 samples and their failed status. This export replay supplements the separate complete model/derivative consumer; it does not replace it.

## Fresh correction from the stored anchor

The preceding [stored-value repair](native-stored-pair-repair-jobs-v1.md) provides a native/contact/reference-passing diagnostic anchor with twenty component corrections. The new request changes only anchor controls, actor files and corrections, preserving original source/static references, nine rate arrays, all edit/contact/geometry limits, participants and settings. The unchanged producer completes a fresh sixty-control model with 29870 native norms, 276789 scalar surface rows, 119942 equivalent encoded rows and 2856 partner depth witnesses.

The primary and surface phases report `Solved`; minimum norm reports `AlmostSolved`. The primary normalized depth optimum is approximately 5.42772e-12, but the final projected deficit is approximately 1.58539e-7, exceeding the requested 1e-9 lock. Predicted native excess is approximately 7.64416e-9. These statuses and numerical locks do not establish exact feasibility or nonlinear acceptance.

| Fraction | Stored motion failures | Centered motion failures | Contact failures | Penetration, mm | Triangle records | Contained vertices | Failed geometry samples |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 27 | 29 | 0 | 5.001120 | 30427 | 6 | 1602 |
| 0.5 | 0 | 0 | 0 | 5.032366 | 30418 | 28 | 1600 |
| 0.25 | 0 | 0 | 0 | 5.048412 | 30440 | 36 | 1600 |
| 0.125 | 3 | 0 | 0 | 5.056461 | 30439 | 40 | 1600 |

Every fraction passes cumulative original-reference bounds; every complete geometry audit still fails. The half step passes actual motion/contact checks and reduces depth from 5.064515 mm to 5.032366 mm, triangle records from 30437 to 30418 and contained vertices from 42 to 28. Failed geometry samples stay at 1600. The full step gets closest to the five-millimetre depth threshold but fails 27 actual motion rows and increases failed geometry samples to 1602. Neither is an approved animation.

A separate complete model consumer imports no producer job/model/proxy/guard/reduction/solver APIs. It recomputes the original rate arrays and every native Jacobian entry, proves all 2856 affine guard coordinates remain nonnegative throughout the proof box, verifies all 156847 exact rational surface implications, and replays all sixty scalar derivative columns within **3.3306690738754696e-13**. Every raw payload, decoded world and native observation matches; cumulative reference displacement uses all native times. Geometry transport is checked, predicates are not independently recomputed. The consumer confirms the final phase exceeds the requested depth-priority lock. That solver-phase selection requires correction; the lock is not a nonlinear certificate.

The current bounded-memory repair command chooses the half step from this pinned study and completed model replay. It retains one actual probe, tests zero additional neighbors and keeps all twenty existing absolute component choices. The final probe is decoded again and compared exactly with its archived observations. Complete native/contact and original-reference checks pass; complete geometry still fails at exactly the raw half-step score. Maximum original-reference displacement is approximately 2.820906 mm for A and 2.849188 mm for B; maximum edited rotation is below 0.390 degrees, within the original thirty-millimetre/five-degree bounds.

Both actors receive separate appended index6 variants preserving all six source clips and the original binary prefix. A separate saved-key consumer imports no repair-job/search/storage/proxy API and verifies the complete native observations, manual component choices, original rate/reference bounds and appended-library worlds. No extra storage repair or automatic asset selection is needed or granted. The native-passing, geometry-failed half step remains a diagnostic anchor only. Next validate solver phases against their actual depth-priority locks before continuing correction; preserve original external acceptance and every rejected output.

No new model inference/training, production humanoid action, GPU/rendering, engine, physical validation, developer rating or cleanup-time evidence is claimed. Broad action/rig/object/partner requirements stay open; all fourteen release evidence arrays remain empty and the full-project goal remains active.

Large assets, raw failures, observations and local drivers stay ignored. Receipt SHA256 identities:

- Fresh correction study: `40b423c81b49b715ede7d227a02d27d70814ae8516a1cb99760edb37fc030473`.
- Reusable complete export replay: `b3342315f1a15650824e50e954d323f1bb681f3bc1ba0924130400e3f2304efc`.
- Current replay with stricter selection/approval binding: `bcf85c23e7a95ff9a57b613aa9772ee6069a023852664bcb52175d2b7c2122f5`.
- Actual import-independence check for the current replay: `f707bb7a0eefe6791dc1d3d5f2fba94d33ab46e99bae6cf20792c2ba5c0769b9`.
- Complete model and all-native reference replay: `82d2c4942694459a14f9efa49d54aea715d25967cb00bda35bc10cb59d280cd7`.
- Current bounded-memory half-step variant: `22dd287d1af913ee58a9462a6380b425589b8825f04062f2804c217949f35e73`.
- Complete saved-key and appended-library replay: `4aab442a7b0ef90947ca26ee243b28f53037cd3ca53760be2c8b12d4c119776d`.
- Next diagnostic anchor, retaining original limits and geometry failure: `afda24e468ea6dd4ad45bbeb312285cd5b0e0bdf9ed64017b2f454df811d392a`.
