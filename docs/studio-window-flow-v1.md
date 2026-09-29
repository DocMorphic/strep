# Real Studio windowed-contact workflow

The new selected-range path has now run through the actual Studio backend: source metadata, immutable preparation, fitting, geometry audit, full-skin preservation audit, review bundles and downloadable reports. It was invoked directly through the same functions used by Studio, without HTTP or browser interaction. The prior exact-owner process was allowed to finish first; no numerical workers competed for the shared lock.

The authored request selected the completed arm-guide candidate from `window-range-review-v1` and keys **[23, 133]**. Its ordinary Studio fit used three stages of forty iterations and a 300-second limit, finishing in **150.875 seconds**. This is a new edit whose reference is the selected candidate, using ordinary Studio settings. It is **not** a matched alternative to the full physical-root study, which keeps the original raw motion as its edit reference and different solver settings.

The workflow completes while correctly retaining failures:

- **461/490 contact samples fail**, compared with 478 in its selected input.
- **368/717 geometry samples fail**, compared with 379 in its selected input.
- Source-relative edit bounds pass. Locked interpolation segments match the selected input's skin within **0.078 micrometres**.
- Boundary-straddling samples change by **0.01655 mm**. This exceeds the numerical preservation allowance and appears as an explicit boundary regression.
- All **360 source/candidate Godot actor-frames** pass import-transform verification, with joint-position discrepancy below **0.394 micrometres**. This confirms fidelity, not contact or naturalness.

Verification checks all **37 source snapshot files**, exact endpoint agreement between request/protocol/audit, matching result identities, consistent assessment across pipeline and candidate bundle, and **seven download/bundle routes**. Both range reports appear in the completed job's manifest. No human ratings were entered and no quality approval was granted.

The review is retained under `reports/scene-region-jobs/studio-window-flow-v1`. Exact preparation/run method, fit log, owner identity, engine evidence and verification are under `reports/studio-window-flow-v1`. The final report binds the package inputs and methods by hash. Browser interaction remains unverified; all fourteen release capabilities remain unapproved.
