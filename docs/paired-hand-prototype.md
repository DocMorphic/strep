# Coupled high-five correction: first diagnostic

The prototype jointly optimizes both actors' shoulder, upper-arm, forearm and wrist rotations toward one shared high-five event. Each actor contributes twelve variables to the same objective: palm point separation, opposing surface normals, finger direction and a small edit penalty. It does not alternate between frozen targets.

The input is the previously inspected left-hand high-five pair at seed 1301 from the breadth study. This is development evidence, not a held-out evaluation. Authored placement remains unchanged. A cosine-squared envelope applies the correction around frame 75; 121 of 150 frames remain outside the edit window. Root, torso, legs, all local translations and the original root/contact prediction tracks are protected. Angular budgets are edit limits, not anatomical joint limits.

The completed run is `reports/paired-hand-prototype-v3`. Its independent decoded-skin measurements at frame 75 are:

| Diagnostic | Original pair | Coupled candidate |
| --- | ---: | ---: |
| Palm separation | 272.953 mm | 0.00560 mm |
| Opposing palm-normal error | 17.195 degrees | 0.0687 degrees |
| Finger-direction difference | 85.515 degrees | 0.281 degrees |
| Maximum partner penetration | 0 mm | **16.564 mm** |
| Vertices exceeding 5 mm penetration, each direction | 0 | **200** |

**The candidate fails the partner collision diagnostic.** Aligning one palm point and its frame does not align the entire hand surface. The deepest vertex is primarily influenced by the little-finger base. A tiny point error is not evidence of a natural high-five. Neither input nor candidate is quality approved. The collision measurement covers the event frame only; the surrounding edit window, self-intersection, reaction, balance and physical contact remain unvalidated.

Both scenes were actually imported into Godot with two actors on the same clock. All 77 bone transforms were checked across all 150 frames for each actor: 600 actor-frames total. Maximum position discrepancy was 0.0000008345 m and maximum rotation-element discrepancy was 0.000002623. This establishes export consistency, not motion quality. Independent decode also verifies protected transforms, the fixed frames, source-track equality and edit limits; the largest adjacent correction was 2.601 degrees.

The first two failed attempts remain intact. V1 rejected an exact float32 export of float64 mesh positions; its guard now compares the expected serialized representation exactly. V2 exposed NumPy advanced-indexing axis relocation in the candidate joint-position array. V3 preserves the native array layout and passes the actual engine comparison. Their logs and explicit failure records are retained, rather than leaving failed processes labelled as running.

Three focused tests cover analytic derivatives for both actors, independently skinned palm position, the bounded edit envelope and invalid event placement. The next solver change needs constraints on the actual hand surfaces, followed by independent validation across the edited interval and additional seeds. It must retain failed candidates and may need finger articulation; increasing point-fit precision alone cannot resolve this measured failure. Sustained handshakes and full-body reactions require additional work.

## Surface-aware refinement: still rejected

`reports/paired-hand-clearance-v1` runs a fixed four-pass experiment. It finds nearby or penetrating surface vertices in both directions, builds triangle correspondences in batches of 32, and differentiates both actors' actual skinned points. Each inner solve holds the triangle coordinates and outward directions fixed; the next pass rebuilds them on the new pose. The existing global angular budgets remain unchanged, with an additional five-degree per-component inner trust interval. The objective uses a 2 mm separation margin and a fixed aggregate weight of 1000. This is a local approximation, not a continuous collision solver.

All four inner solves reached their 60-evaluation budgets without a convergence success flag. Peak event penetration declined through 14.75, 12.66, 11.54 and 10.82 mm. Every parameter vector and outcome is preserved. The final candidate was exported and independently decoded in `reports/paired-hand-prototype-v4`:

| Diagnostic | Point-fit candidate | Surface-refined candidate |
| --- | ---: | ---: |
| Palm separation | 0.00560 mm | **20.012 mm** |
| Opposing normal error | 0.0687 degrees | 13.793 degrees |
| Finger-direction difference | 0.281 degrees | 14.025 degrees |
| Maximum partner penetration | 16.564 mm | **10.820 mm** |
| Vertices exceeding 5 mm, each direction | 200 | **55** |

Reducing overlap introduces a visible palm gap and still fails the 5 mm collision diagnostic. The broad 30 mm point screen does not make that a believable high-five. V4 is retained as a rejected development candidate; none of these thresholds was relaxed. Because it already fails at the event, an expensive whole-window collision audit has not been used to suggest acceptance.

The V4 export again passes 600 actual Godot actor-frame comparisons and independent protection checks; protected transform discrepancy remains below 0.000000056. Input motion/GLB hashes, native array shapes and implementation snapshots are verified. Two new tests check independent skin positions, both sides of the surface-objective derivative and invalid initial corrections. No full-suite rerun, independent human review, finger correction or interaction-quality approval is claimed. Further work needs to address articulated fingers and temporal contact without accepting large gaps; the four-pass outcome does not establish that arm-only optimization can never work.

## Bounded finger experiment: contact retained, collision still fails

`reports/paired-finger-fit-v1` adds nineteen finger joints per actor and explicitly constrains the two palm points to coincide. The objective uses SLSQP with analytic derivatives and four fixed outer passes. Edit limits are 5 degrees at non-thumb metacarpals, 8 degrees at the thumb base, and 12 degrees at the remaining finger joints; the arm and temporal edit limits remain unchanged. These are small changes around the supplied pose, not anatomical angle limits. This experiment changes the variable set, optimizer and palm constraint together; it is not a finger-only ablation.

The final candidate in `reports/paired-hand-prototype-v5` keeps palm separation below 0.000004 mm, with opposing normals 5.437 degrees apart and finger directions 5.660 degrees apart. Nevertheless it penetrates by **16.564 mm**, with 86 and 87 vertices exceeding 5 mm in the two directions. Inner solves 1, 2 and 4 reported successful termination; solve 3 did not. None establishes global optimality or acceptable contact. SciPy's intermediate bound-clipping warnings are retained, and the exported edit bounds are independently checked.

Both actors and both variants again pass 600 actual Godot actor-frame comparisons, source hashes and native array-layout checks. Two focused tests passed in 14.13 seconds, covering all 138 parameter derivatives, both actors' skin influence, seed preservation and the equality Jacobian. The deepest reported vertex is also classified inside the partner by an independent ray-parity check. Both posed meshes have positive signed volume and consistent closed winding; an inverted mesh does not explain this failure. An inspected three-view projection is saved as `reports/paired-hand-prototype-v5/hand-inspection.png`; it is a diagnostic illustration with overlaid markers, not the collision oracle.

The relevant source limitation is now checked across the **entire 390-clip population**: all 38 articulated finger joints are constant through each raw clip and match the upstream relaxed-hands asset. `SOMASkeleton30.to_SOMASkeleton77` in `vendor/kimodo/kimodo/skeleton/definitions.py` fills the missing joints from that fixed asset. The body model does not generate those finger motions from the prompt. In this fixture, several finger joints would need roughly 19–34 degrees of rotation to reach the mesh's bind pose, beyond the small 12-degree edits in this experiment. Bind pose itself is not an anatomically reviewed high-five pose.

The next implementation should author explicit hand postures and grip targets, preserve their provenance separately from generated body motion, and validate their actual surfaces and temporal transitions. Further optimization around an unreviewed relaxed posture is insufficient evidence of a usable high-five. Neither candidate is promoted.
