# Broaden contact coverage before fitting

The earlier dynamic trial correctly constrained its selected vertices but missed three neighbouring vertices. This follow-up fixes its initial selection before solving: every original contact vertex whose depth is within2 mm of that frame's unchanged cap. That yields113 vertices at15 fitting times. The selection was informed by rejected development results; it is not a conservative bound on future deformation or a held-out fixture.

`seeded_witness_selection.py` preserves both query directions and exact vertex/depth identities, includes the band boundary, and rejects malformed data, duplicates and an already-infeasible original pose. Eight selection tests pass. All original5,272 approximate rows, the motion objective, original initialization, absolute/adjacent edit limits, five-degree local neighbourhood, frame caps and final guard remain unchanged. The additional true-distance rows remain inequalities only.

The frozen preflight in `reports/seeded-dynamic-witness-proof-v1` checks all113 vertices at the original and last rejected poses. All226 retained distance comparisons agree within8.292e-16 m, and every seed constraint is feasible. Six fixed random directions plus the largest-Jacobian coordinate at each pose give14 decisive checks at step1e-5; all pass, with maximum scaled error2.7911e-8. Forty-two checks across three step sizes are retained. Initial evaluations take6.210/6.147 seconds locally. These are directional derivative and cost checks, not proof of optimisation convergence or animation quality.

`study_seeded_dynamic_witness.py` starts the new trial in `reports/seeded-dynamic-witness-cuts-v1` from the verified113 identities. It retains a maximum of three rounds and60 inner iterations per round. Every proposal receives all30 fitting-time geometry checks and the existing event-area/normal/objective/hard-edit guard. Newly violating vertices may be added within that fixed budget; no cap is enlarged.

The trial completed with its first proposal accepted by the unchanged local guard. The solver used60 inner iterations and486.889 seconds, reaching its iteration limit rather than convergence. The fresh30-time check reduced the peak depth from24.740384 mm to24.422624 mm, but14 samples remain above5 mm. Energy decreased from1406.651816 to1293.981533. Both event-region area checks, opposing normals and the recorded hard-edit bounds passed. No new witness round was needed.

`reports/seeded-dynamic-first-step-v1.json` verifies completion and candidate/geometry/decision hashes, reproduces depths from the retained geometry rows, checks the unchanged sample clock and independently reruns `screen_path_guard.select_step`. This is a modest accepted development step on a retrospectively selected scene, not a solved interaction or converged optimum.

`reports/seeded-dynamic-witness-validation-v1` completed export and full auditing at01:44:14UTC. Both actors pass integer and299 decoded half-frame edit/preservation checks. Godot checks600 actual actor-frames with maximum position error7.153e-7 m. All10 manifest assets, completion hashes and sample summaries were independently verified in `reports/seeded-dynamic-full-audit-v1.json`.

The full299-time comparison distinguishes the original raw motion from the already fitted initializer used by the local guard:

| Measurement | Original raw | Exported candidate |
|---|---:|---:|
| Peak partner penetration |21.6226 mm|24.4226 mm|
| Samples exceeding5 mm|9|14|
| Peak floor penetration|11.9591 mm|11.9591 mm|
| Named surface-vertex gap at event|64.9504 mm|21.2278 mm|
| Region vertices within3 mm, each direction|0 /0|11 /11|
| Event opposing-normal error|30.2879 degrees|5.9454 degrees|

The candidate improves contact-region proximity and the local fitted initializer, but worsens collision relative to the raw baseline. It fails the final collision/ground screens and remains a development artifact. Named-vertex gap and region proximity measure different things; neither supplies animator/anatomical approval. No conservative between-sample or self-collision claim is made. Further work must address the contact/collision tradeoff relative to the raw baseline, not promote a locally accepted step as a solved interaction.
