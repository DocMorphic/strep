# Frame-121 grasp diagnostic

The full directly bounded root trial still fails. Before another full-duration solve, this diagnostic repeats the original difficult grasp frame into five keys and freezes both scene objects at their frame-121 poses. Neither tested configuration finds a usable grasp. This is development diagnosis, not a new action, a held-out sample, a loop, or a feasibility proof.

## Construction and controls

`reports/region-frame121-static-v1/prepare.py` preserves the exact construction method. Original motion comes from `reports/region-full-transfer-v1/input-motion.npz`; initialization comes from `reports/region-object-grip-seed-v2/motion.npz`. Every frame-varying array is copied from frame 121 into five keys. Box and distant-prop poses are frozen, and the two grip intervals become frames 0-4. Mesh, geometry, actor placement, contact regions and tolerances stay unchanged. Original source frame 121 remains the correction-budget reference; the initializer does not replace it.

The fixture validates motion and both regional constraints. Copied vertex positions are identical to the originals at frame 121, and object pose discrepancies are below 1e-12. Original/seed minimum native skin-box gaps are -54.256800/-38.993169 mm. `fixture.json` binds construction, source, seed, skin, scene and generated fixture hashes.

Both fits use six stages, 100 iterations, a 600-second ceiling, balanced regional loss, augmented regional and per-vertex object inequalities, full sparse skinning, stage witness refresh, 0.05 mm object margin, 0.01 mm contact gap margin, original edit bounds and directly bounded root coordinates. Numerical source was unchanged during either fit.

The guarded configuration retains the export-rate objective and 0.0005 acceleration margin fraction. The matched spatial diagnostic disables that objective and its dependent margin; all other protocol fields except timestamp match. This is an explicit diagnostic ablation, not relaxation of production acceptance. The five repeated keys remain independent optimization variables: they are not constrained to remain an identical pose.

## Results

| Exported measurement | Rate guard enabled | Rate guard disabled |
| --- | ---: | ---: |
| Runtime / objective evaluations | 35.656 s / 379 | 48.813 s / 830 |
| Failed contacts / 34 | 17 | 34 |
| Failed geometry samples / 17 | 17 | 17 |
| Worst box penetration | 38.814574 mm | 13.040549 mm |
| Peak joint speed | 5.89398e-8 m/s | 0.071770 m/s |
| Peak joint acceleration | 7.07277e-6 m/s² | 2.730737 m/s² |
| Maximum rotation change from initializer | 0.006243° | 12.789437° |
| Root lift range | 0.022012-0.022012 mm | 64.925305-67.761011 mm |

Both satisfy original rotation/root edit bounds. All 20 source/candidate actor-frames across the two Godot checks reproduce 77 joints with position discrepancy below 0.184 micrometres. This establishes export fidelity, not successful contact.

The frozen source has nearly zero sampled speed/acceleration. The guarded objective records reference peaks of approximately 5.85e-14 m/s and 1.34e-11 m/s²; its normalization scales clamp to 1e-6 in their respective units. Large penalty excursions appear during line-search probes, while accepted rotations barely move. Four guarded stages terminate on relative objective reduction, after two hit iteration limits. That termination does not establish feasible contact or a small projected gradient. Removing the rate objective allows substantial pose/root changes, but loses all contact samples and introduces movement between the nominally repeated keys. Every unguarded stage hits the iteration limit.

An initial no-guard invocation mistakenly retained the dependent nonzero acceleration margin. Validation rejected it with `Acceleration margin requires the export-rate guard`; `spatial-only/result.json` preserves the failed attempt. The corrected diagnostic uses a fresh `spatial-only-v2` directory. No output was overwritten.

## Interpretation and retained evidence

The rate penalty is sensitive to an effectively static reference, and removing it alone does not solve this grasp. Neither result proves the original pose constraints are infeasible or identifies a unique cause of full-motion failure. Before another expensive full-duration run, a genuinely shared-pose diagnostic should remove temporal degrees of freedom explicitly and inspect spatial residuals and conditioning. It must retain the original source bounds and skin constraints. Successful static contact would still require separate trajectory, anatomical and human validation.

Exact protocols, implementation snapshots, native output, decoded geometry/rate checks and Godot checks remain under `reports/region-frame121-static-v1`. `compare.py` verifies fixture hashes, protocol differences and result/audit bindings before writing `comparison.json`; `audit_spatial.py` preserves the second audit method. The first audit used the completed exact fitting process. Neither comparison received live browser or human review. All 14 release capabilities remain unapproved.
