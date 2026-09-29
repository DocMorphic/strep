# Clearance-buffer continuation and guide transfer

Increasing the solver's object-clearance target does not finish the shared-pose grasp repair. It improves exported minimum box clearance from the matched control's 1.919823 mm to 1.934233 mm, still below the unchanged 2 mm requirement, while increasing maximum sampled support drift from 4.324187 to 4.988552 mm. Both hands remain valid. The larger buffer is not adopted as a default or treated as a release success.

## Cause and controlled test

The four remaining vertices in the previous buffered candidate are included in full-skin fitting. Reconstructing their actual solver residuals gives positive violations of 0.228–0.282 mm, including the 0.05 mm existing solver margin. The reconstructed maximum agrees with the retained final-stage record within 0.1 micrometres. This rules out omission from sampling as the cause of these particular failures; it does not prove infeasibility or convergence.

`reports/region-clearance-buffer-v1/method.py` performs fresh solves from the same `region-buffer-continuation-v1/buffered/motion.npz`. The original source remains the edit reference. Both arms retain the 0.001 regional buffer, both inferred foot supports, six stages of 100 iterations, 600-second budget, full sparse skin, per-vertex object constraints, shared pose and export-rate guard. Only the object solver margin changes: 0.05 versus 0.4 mm, corresponding to solver targets of 2.05 versus 2.4 mm. Independent acceptance stays at 2 mm. Optimizer state and multipliers restart.

| Exported measurement | Control | Larger clearance buffer |
| --- | ---: | ---: |
| Runtime / evaluations | 161.531 s / 1,302 | 172.641 s / 1,374 |
| Failed hand-contact samples / 34 | 0 | 0 |
| Failed geometry samples / 17 | 17 | 17 |
| Minimum box clearance | 1.919823 mm | 1.934233 mm |
| Failed source-support samples / 34 | 0 | 0 |
| Maximum support drift | 4.324187 mm | 4.988552 mm |

Three native vertices remain below 2 mm in the larger-buffer result: vertex 10977 on the right forearm, and vertices 3545 and 11878 on the right pinky. The previously failing left-palm vertex now exceeds 2 mm. All six larger-buffer stages hit their iteration limits. Five control stages hit their limits; one stops on relative objective reduction. These exits do not establish complete feasibility.

Both outputs repeat exactly across five keys, preserve original edit bounds and pass twenty new Godot source/candidate actor-frame checks with joint position discrepancy below 0.204 micrometres. The larger-buffer root lift is 11.477816 mm, minimum floor gap is 11.006799 mm and maximum original rotation edit is 33.574993 degrees. No moving interaction, transition, planted sole, force balance or human quality claim follows from these static measurements.

`compare.py` verifies matched protocol settings, input and implementation hashes and completed audit hashes. `residual_diagnosis.py` and `final_clearance_diagnosis.py` retain exact localization methods. Studio collections `region-clearance-control-review-v1` and `region-clearance-clearance-buffer-review-v1` each pass thirteen package hashes and twelve offline route checks, with the Python snapshot unserved. Both retain failed geometry status. No live browser or human review was performed.

## Transfer preparation

The object-frame initializer now accepts an integer reference anywhere within the authored contact interval, including its final frame. Previously it required the first frame even though the underlying transport supports arbitrary references. Frame zero of the guide must still match the full scene's object pose at the requested reference. The existing geometry/contact audit, guide hashes, contact definitions, original edit budgets and output validation remain required; default reference 60 is unchanged.

Seventeen focused tests pass, including world-pose reproduction and object-relative transport for start/middle/end guides, rejection of out-of-interval references, bounded moving-target fitting and unattainable-target handling. An actual integration check confirms that the failed-clearance guide above is rejected before creating any full-motion output. Full-motion transfer from frame 121 therefore remains pending, rather than silently using an unqualified guide.

Next address the remaining forearm/pinky clearance with explicit preservation of the passing hand and support constraints. The small benefit and reduced support margin do not justify another global target increase alone. Broader moving-scene verification and all fourteen release capabilities remain open.
