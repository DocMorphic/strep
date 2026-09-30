# First scene-derived paired fit and Studio publication

The saved retimed-and-trimmed development scene now completes the paired fitting, independent replay, engine validation and Studio publication workflow. The comparison is **Paired scene correction · Before / After**, under `scene-region-jobs/paired-curve-controls-trimmed-v1`. Both 111-frame versions remain editable and retain the exact contact time of 2.0917225950783 seconds.

This demonstrates the workflow, not a cleared interaction. The accepted half step improves peak penetration by only 0.003803 mm. Thirty-seven sampled times still fail the 5 mm screen; naturalness and full-clip quality remain unapproved.

| Local sampled check | Source | Half step |
| --- | ---: | ---: |
| Peak partner vertex penetration | 22.568796 mm | 22.564994 mm |
| Times over 5 mm | 37 / 126 | 37 / 126 |
| Maximum increase beyond each original depth ceiling | — | 0.000008945 mm |
| Maximum sampled floor-depth increase | — | 0 mm |
| Exported positional-motion limit failures | — | 0 |

The depth-ceiling discrepancy is below the existing 0.001 mm comparison tolerance. Complete mesh checks cover 126 times and 252 directional queries in the local edit window. They do not certify continuous collisions, triangle intersections, self-collision, full-clip dynamics or visual quality.

## Attempts and independent evidence

The first run, `scene-pair-fit-v1`, completed source geometry and solving but failed at a duplicate `status` logging argument. Its outputs remain unchanged. The repaired `scene-pair-fit-v2` reuses only the exactly bound geometry and reproduces every linearization array and solver control value.

The full step is retained and rejected: actor A exceeds 12 positional-motion rows and actor B exceeds two. The half step passes exported motion and edit checks and the fresh complete-mesh comparison. Both attempts preserve protected quaternion keys and decoded protected poses. Neither is a new generated action or a learned-model update.

Independent replay reconstructs all four attempted actor GLBs exactly, checks **76,692 joint-motion observations**, and verifies **4,287 source surface witnesses** through complete CPU skinning. The maximum witness-point discrepancy is 4.440892e-16 metres. Replay considers all joints and stencils rather than reusing the fitter's affected-row selection.

Godot imports both originals and both attempted pairs: **six clips and 666 actor-frame observations**. All retain 77 bones, one skinned surface, their duration and nonlooping playback. Maximum joint-position error is 7.168626e-7 metres; maximum basis-element error is 6.565565e-7. Import success does not override the full step's motion failure.

The completed study entered the Studio worker without repeating fitting. Existing engine observations were reused only after checking exact actor IDs, GLB bytes, native timing, observation methods and successful import results. Raw engine evidence is copied with its hashes. A changed clip requires new observations.

## Studio result

Publication copies the exact reviewed GLBs and reconstructs editable native motion. Across **444 actor-frames**, the reconstructed full skin agrees with the GLBs within **0.330 micrometres**. Both versions preserve the original scene placements, precise contact metadata and inherited foot-contact predictions.

Direct production-handler checks verify collection discovery, completed-job listing and source metadata. Ten artifact routes and both versions' continued eligibility for timing and paired edits are checked without HTTP or browser rendering. The local records are `reports/scene-pair-studio-review-v1.json` and the job's `fit`, `replay`, `engine` and publication provenance files. Rendered browser appearance and human review remain unverified.

Twenty-four distinct focused Python checks cover engine-evidence reuse, worker request/dispatch/publication safeguards, no-proposal completion and standalone CLI locking. The CLI and Studio worker now acquire the same OS lock; a real contended subprocess exits before loading inputs or creating an output folder. Pure engine reuse tests join model-free CI.

The next fitting decision should address why clearance changes so little under the current joints, window and motion constraints. Adding iterations without measuring that limitation would not establish useful correction. Broader actions, rigs, human ratings and all 14 release capabilities remain unapproved.
