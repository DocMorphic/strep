# Measured sphere grasp fitting

The first full sphere-contact fit improves some errors but remains unsuitable for release. The input is the six-second, 180-frame development scene from [sphere release](sphere-release-v1.md): an existing actor, a 0.25 m sphere following a previously authored box trajectory, two material-point grip targets, and a distant prescribed sphere. It is not a new model sample or held-out test.

`scripts/study_sphere_contact_fit.py` freezes the scene and asset hashes, then runs the unchanged v8 floor/body/contact pipeline. The only runner extension is an explicit preview collection root, so saved-scene GLBs can be copied without relying on the old preview directory. The solver retains its three outer stages, 100-iteration budget per stage, 5 mm point target, 10-degree normal target, and bounded root/rotation edits. Its objective uses 1,250 selected skin vertices; verification measures all 18,056 vertices.

The run completed in 145.6 seconds under a 3 GiB process-tree limit and a 1.25 GiB free-memory reserve. Peak observed process-tree RSS was approximately 1.04 GiB. The fit made 326 objective evaluations. Maximum additional local joint rotation was 15.54 degrees, within its 40-degree bound; root lift was approximately 0.022 mm. These are correction bounds, not anatomical joint limits.

## Results

The independent auditor decodes the exported GLB at keys and quarter-frame times: 717 samples per variant, with 244 samples in each contact window. The window is `[60,121)`, matching the authored contact-end event. Its 30 mm scene-contact and 15-degree orientation screens are distinct from the solver's stricter internal targets.

| Dense measurement | Input | Fitted candidate |
| --- | --- | --- |
| Left grip maximum error | 25.064 mm | 25.301 mm |
| Left grip samples within 30 mm | 244/244 | 244/244 |
| Right grip maximum error | 112.082 mm | 38.356 mm |
| Right grip samples within 30 mm | 10/244 | 241/244 |
| Maximum actor/sphere penetration | 107.549 mm | 30.291 mm |
| Samples with penetration above 10 mm | 315/717 | 245/717 |
| Left palm maximum normal error | 19.317 degrees | 11.212 degrees |
| Right palm maximum normal error | 42.981 degrees | 13.491 degrees |
| Actor/floor penetration | 0 mm | 0 mm |

Neither hand reaches the 5 mm solver target at any sampled contact time. Both fitted palm normals pass the separate 15-degree diagnostic throughout the window, but their maxima still exceed the solver's 10-degree target. The largest fitted right-hand error occurs at contact entry. The left-hand maximum occurs at frame 120.75, after the last constrained key and before the release event.

Motion quality did not improve uniformly. Around release, peak left-palm speed increases from 0.139 to 0.441 m/s and right-palm speed from 0.146 to 0.729 m/s. Peak sampled joint acceleration increases from 27.45 to 53.68 m/s². These are descriptive kinematic measurements, not human naturalness scores. Existing fixed source-foot patches retain approximately 0.0115/0.0132 m/s mean sliding, with negligible measured change; those patches are inferred support candidates, not independent contact annotations.

Actual Godot imports pass all 360 actor-frame observations for input and candidate, checking all 77 bones at each frame. Maximum position error is below 0.36 micrometres. That establishes export fidelity, not grasp quality. This import check does not include rendered skin, object physics or human review.

## What the failures identify

At the candidate's worst collision sample, frame 66, penetration above 10 mm is localized to finger-weighted skin regions. The deepest point is on the left little-finger tip region. The v8 solver deliberately leaves finger articulation unchanged, so increasing the body/arm objective alone is not a demonstrated solution. Dominant skin-weight labels approximate anatomy; this localization is a peak-frame diagnostic, not an all-frame collision classification.

The copied object trajectory also places the 0.25 m sphere up to 50 mm below the floor, for 264 dense samples above the 10 mm depth screen. Both variants retain this input defect. An actor-only fit cannot correct a frozen object path; the prior release study checked floor behavior after release and did not establish valid pre-release placement.

Next work should distinguish input feasibility from correction: author a floor-valid object track as a separately named treatment; evaluate bounded finger articulation and full hand geometry; and constrain entry, the entire release interval, and temporal regressions. Keep the present outputs and thresholds unchanged. Passing static poses alone will not establish usable animation.

## Evidence and remaining scope

Local evidence: `reports/sphere-contact-fit-v1`, `reports/sphere-contact-fit-audit-v1`, and `reports/sphere-contact-fit-engine-v1`. Each preserves source hashes and implementation snapshots. Five focused tests cover explicit preview resolution, oriented scene geometry, and the fractional release-window contract. Generated artifacts are excluded from the public repository.

No checkpoint training, reserved evaluation prompts, animator ratings or cleanup-time observations were used. Browser rendering was not verified. The candidate is not promoted, and all project release capabilities remain unapproved.
