# Export-feedback repair in Studio's checked fit

Studio's **Fit saved checked pins** workflow now runs export-feedback correction after fitting and before building the preview/download package. It retains the original fit under the take's `initial-fit/` folder and every feedback proposal under the job's `result/export-feedback/` folder. The source and its raw/limb history remain unchanged. The existing general **Apply contact edit** workflow is unchanged.

The selected native motion, GLB, BVH, root track and contact track are copied together from the verified feedback result. Contact-target measurements are recomputed for that motion; body evaluation, export audit and validation come from the selected proposal. Final metrics, flags, sequence diagnostics and the ZIP are then produced from the selected result. The recipe records final original-relative root lift and rotation change while explicitly labeling earlier optimizer/stage measurements as initial-fit diagnostics.

Final checked-fit flags now include raw positive added floor depth, global joint-rate excess and negative serialized constraint slack. A sub-micrometre depth regression cannot disappear merely because it falls below the diagnostic category. Completion still means that processing finished, not that the animation is approved.

The contact panel distinguishes a selected correction from a retained fitted motion, reports whether sampled export/native constraints pass, and links to repair decisions, final joint-rate measurements and the initial native fit. Missing repair measurements are unavailable, not passing. Existing point-contact measurements remain visible. A numerical pass is explicitly labeled unapproved for animation quality.

## Real supervisor-to-engine verification

A new job consumes the saved wave-11 timing check through the actual checked-job preparation and supervisor. It uses the existing two-stage, 60-iteration fitting budget and metre-scaled point objective; this integration does not silently switch Studio to the longer research configurations. Fitting took 479 objective evaluations. Fitting, feedback, evaluation and packaging took 182.73 seconds on the local machine.

The fitted motion's approach point-speed limit failed. Feedback accepts its first proposal with a maximum root-height adjustment of **1.720429e-6 m**. This is a precision correction, not evidence of visibly improved style or naturalness.

| Final measured check | Result |
| --- | --- |
| Left-foot pin, frames 50–70 | 3.941420 mm maximum; 0 of 81 samples above 5 mm |
| Point-phase speed/acceleration | All original ceilings pass |
| Global joint speed | 3.866860 m/s, below 3.866922 m/s |
| Global joint acceleration | 455.530339 m/s², below 455.601356 m/s² |
| Added floor penetration | Zero |
| Outside-window joint/basis/skin differences | Exactly zero at 80 observations |
| Serialized minimum constraint slack | Positive, 1.638840e-5 |
| Body and final export flags | None |

Actual Godot playback passes **284 new pose observations**, two requested boundary events, four callback-mutation rejections, forward/reverse playback and unload. Maximum actor matrix error is 1.02e-6. These events describe requested pin boundaries, not independently verified physical support.

The job's source/method freeze, feedback input/artifact hashes and retained initial-fit hashes were checked. Selected recipe root lift, audit, contact targets, body flags and summary agree with the selected motion. The ZIP's native/GLB/root/contact/recipe/evidence/review files match their corresponding final files exactly.

The real study-list handler lists the job as complete and ready. Direct file-handler calls return matching bytes for seven routes, including preview, package, repair decisions, global-rate measurements and the initial fit. These checks invoke Python handlers directly; they use no HTTP connection. The actual result also renders in the offline DOM harness with the correct pass state, unapproved-quality notice and all four review links.

Fifty-seven distinct focused Python tests pass across selection, original budgets, held poses, metadata replacement, artifact tampering, strict final flags, revision-bound job preparation and desktop builds. Offline contact-review and timing-workflow checks pass. Existing Torch deprecation and SciPy option-passthrough warnings remain. No browser rendering or human review was performed.

Local evidence is retained under `reports/studio-export-feedback-v1/` and `reports/contact-jobs/studio-export-feedback-v1/`. This verifies one real checked-contact workflow. It does not solve the retained crawl/kick joint/support failures, generalize the stationary-pin adapter to moving objects or partners, or approve any of the fourteen release capabilities.
