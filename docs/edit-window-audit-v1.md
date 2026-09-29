# Independent edit-window export audit

`audit_scene_edit_window.py` verifies preservation against the exact starting motion by comparing independently decoded seed and candidate GLBs. It checks all rig joints and the complete SOMA skinned mesh at 120 Hz. This replaces a one-off joint-only check with a reusable, hash-bound report; it does not approve contact, dynamics or animation quality.

The audit verifies the completed result, candidate/native output hashes, protocol, scene, seed binding, mesh, clock and rig identities before comparison. A fitter with a declared initializer supplies it automatically. Older guide protocols require an explicit `--seed` whose hash must already be bound by their input protocol. A different declared initializer is rejected. The audit preserves its re-exported seed reference and records every sampled discrepancy.

Samples are split into intervals whose interpolation keys are both locked, segments crossing an edit boundary, and the edited window itself. All outside times are also summarized together. Missing coverage is reported as unavailable rather than a pass. The numerical preservation allowance is 1 micrometre for joint/skin positions and 1e-6 for rotation-matrix elements; it is not a physical contact tolerance or a calibrated release threshold.

## Verified completed clip

The earlier windowed arm-guide clip was measured against its exact starting seed. Its hand contacts and geometry remain failed; this audit only establishes preservation outside the requested edit window.

| Sample group | Samples | Maximum joint-position change | Maximum skin-position change |
| --- | ---: | ---: | ---: |
| Both interpolation keys locked | 370 | 0.136 µm | 0.137 µm |
| Outside-time boundary segments | 6 | 0.067 µm | 0.069 µm |
| All outside times | 376 | 0.136 µm | 0.137 µm |
| Edited window | 341 | 174.918 mm | 188.458 mm |

The outside groups pass the numerical check. Changes within the selected window are expected and do not count as preservation failures. The maximum outside rotation-matrix element discrepancy is below 1.40e-7. Native-window preservation alone would not have established these between-key and full-skin results.

## Review integration

The review publisher now requires a matching `--window` audit for a fit whose protocol declares an edit window. It recomputes sample-group summaries, validates complete ordered clocks, tolerances, result/window identity and bound input hashes, and rejects missing or inconsistent evidence before writing a review directory. Locked-segment and boundary-segment failures become separate regression flags. The report is downloadable from the existing scene review, and the candidate note reports its locked-motion preservation outcome. Existing contact failures and the absence of human review remain visible.

Eighteen focused audit, publisher and support tests pass. They include missing clock samples, duplicate times, invalid errors, no locked coverage, a boundary failure despite matching locked segments, stale result/selection identity and falsified summaries. An actual missing-report publication is rejected before any output is created. The completed `window-preservation-review-v1` collection passes thirteen file hashes and twelve permitted offline routes; its Python snapshot remains unserved. No live browser check was performed.

Evidence is retained under `reports/edit-window-audit-v1`, including the complete comparison and publisher verification. The long-running `region-windowed-surface-v1` contact solve continues independently with its captured implementation unchanged; this new audit will be applied only after its result exists. All fourteen release capabilities remain unapproved.

```powershell
.venv\Scripts\python.exe scripts/audit_scene_edit_window.py reports/completed-fit reports/fresh-window-audit
```
