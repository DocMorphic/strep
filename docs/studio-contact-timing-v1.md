# Stationary contact timing checks in Studio

Studio's **Clip inspector → Edit contacts → Check stationary-pin timing** now checks a saved current clip against authored world pins. Choose held start/end frames around the pin intervals, then select **Check timing only**. The job snapshots the motion and preview, records its implementation and input hashes, and returns a readable explanation, full report and bound contact-point specification.

This is a separate, read-only check. **Apply contact edit still uses the existing correction method and does not enforce these rate limits.** A timing check never creates a replacement animation, changes the draft, applies a proposed range or grants motion-quality approval. Passing the necessary travel test does not prove feasible acceleration, rig motion, collision avoidance or physical support.

The check currently supports native SOMA body-corrected takes with 4–901 frames and nonempty stationary world-pin intervals strictly inside two held interior frames. Existing material-point IDs are retained. Otherwise, each pin binds to the lowest source-region vertex at its interval start; the selection and exact ID are recorded for review. Inferred regions are not certified by this check. The GLB's mesh, encoded eight-weight data, inverse binds, duration and native poses are checked against the source motion before measurement.

Jobs distinguish `checked` from `needs_authoring_change`, and neither is listed as an animation ready for preview. Results return to the inspector, recover for the matching source after reload, and retain their report links. Frame-bound drafts persist locally. Saved results are explicitly labeled as potentially different from the current draft; polling does not repeatedly overwrite newer editing messages.

## Retained verification

The actual job path was exercised on `body-contact-v1/get-up-seed-11`, with both foot targets taken from frame 90 and authored intervals 30–149 inside window 20–159. It bound the two initially unspecified material points and measured **four endpoint travel conflicts**. No complete held-window expansion passes; no correction was run or animation created. The original source and user draft remain unchanged.

The final job verified two source snapshots, sixteen implementation files, and three downloadable routes. Maximum native-vs-GLB pose component error was **9.88e-7**; the original encoded eight-weight coefficients match exactly. A direct, read-only invocation of the real study-list handler confirms the result is reported as a timing check with `ready: false`. No HTTP or browser request was used for this verification.

The first attempt rejected legitimate decoded weight normalization by the GLB reader. That failed job and its source snapshot remain in `reports/studio-contact-timing-v1` / `reports/contact-jobs/studio-timing-check-v1`. Verification now compares the encoded GLB weights directly, without relaxing any motion limit. The corrected job and measurements are in `reports/studio-contact-timing-v2` / `reports/contact-jobs/studio-timing-check-v2`.

Twenty-six focused Python tests pass, including API compatibility, strict timing options, altered-input rejection, encoded-weight tampering and desktop build preservation. The offline Node editor test covers separate check/correction payloads, frame validation, matching-source results, report links, persistence and polling behavior. The local server was refreshed after verifying its exact owner, lack of children and an available worker lock. Browser rendering and human review remain unverified.

Next, a distinct correction mode can consume the checked point identities, edit window and rate policy through an immutable request, then export and audit an unapproved candidate. That requires integrating the newer fitter explicitly; the legacy Apply action must not silently acquire different motion semantics. The broader project goal and all fourteen release capabilities remain open.
