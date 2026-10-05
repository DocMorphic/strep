# Saved contact stencil composition

`scripts/saved_contact_stencil_step.py` turns explicitly selected local-response measurements into a bounded direction for a subsequent motion check. It reads saved data; it runs no model, forward kinematics, geometry, engine or optimizer. Control masks remain rig-specific declarations, not an action whitelist or inferred anatomy.

The caller pins a complete `native_contact_mask_probe.py` result and supplies the original producer-bound baseline controls. The tool verifies the producer/request/input/method bindings, selected condition archives, their reductions, complete row populations, exact coordinate/sign/step declarations and baseline identity. JSON, NPZ payloads and original NPY headers have explicit complete-data budgets. Missing data, duplicate coordinates, clipping and mismatched populations reject. Nothing is silently thinned or normalized into a different acceptance rule.

For a decoded baseline residual vector `r0` and selected measured coordinate responses `rk`, the prediction is `r0 + sum(rk - r0)`. Every original native/motion/point row and surface row participates. A direction is written only if every predicted native row passes, every passing surface row remains passing, every failed surface row gains no excess, and neither worst nor total squared positive surface error increases, with at least one improving strictly. Each selected coordinate changes by its exact original signed step; all others stay fixed. The maximum allowed step is .005 normalized control units, with at most eight distinct components.

These are finite affine secants, combining predicted stencils with a decoded anchor. They have no cross-term, finite-difference or Float32 serialization error certificate. A test explicitly constructs a nonlinear response whose single-coordinate samples and combined affine prediction pass while its actual joint response fails. A passing prediction never claims decoded or physical feasibility, collision verification, retention, training admission or animation quality.

```powershell
python scripts/saved_contact_stencil_step.py SAVED_MASK_STUDY FRESH_OUTPUT --result-sha256 PRODUCER_RESULT_SHA256 --baseline-source ORIGINAL_BASELINE.npy --picks 6 18
```

`request.json` records the complete input and method bindings; `prediction.npz` stores all predicted rows, controls and direction. `seed-direction.npy` exists only for a direction satisfying the predicted guards. `result.json` distinguishes predicted conditions from actual checks. Source/input/archive mutation prevents a complete receipt. The caller must perform actual export/decode, original source-derived motion and point checks, complete surface guards, full mesh measurement, engine validation and the remaining quality gates before retaining or releasing a correction.

## Development result

The [local finger experiment](local-finger-contact-response-v1.md) provides a decoded baseline and 24 signed predictions for one humanoid/two spheres. Explicit probe numbers 6 and 18 change controls 33 and 69 by -.005 each. Their composition preserves all **303,761** native/motion/point rows and **30,990** surface rows, with zero predicted native or guarded-surface failures. Predicted worst/total surface scores improve from `[1.9132966708083026, 7467.535326933635]` to `[1.9017585931868466, 7421.533099650448]`.

Adding probe 22 further lowers total predicted error to 7416.305085308059 but fails protected native row 260825 with normalized excess .006681365558722022. That three-component diagnostic writes no seed. This is a failed local prediction, not proof of global infeasibility or a reason to weaken a motion cap.

The original single-finger full mesh worker continues its unchanged 2,552-sample audit. A separate actual two-finger export/decode check is queued on exact owned original process handles, verified by creation times and commands. It holds no production lock while waiting and starts only after zero original exits and a complete bound geometry receipt. It independently re-exports/re-decodes the baseline, requires exact reproduction of all original saved condition arrays, and then measures the composed candidate. It cannot retain a clip or claim that the earlier single-finger mesh audit covers a different candidate. Both the original full mesh result and the new actual combined result remain pending.

## Source checks

An isolated public-source copy passes **58 tests** in **6.02 s**: **27 new composition cases and 31 unchanged mask/normal-bound cases**. They cover complete secants, original hard/guard conditions, explicit baseline/probe identity, rebound tampering, incomplete populations, nonlinear cross terms, malformed/oversized NPY headers and actual tiny GLB APIs in the existing mask tests. No model, vendor code or downloaded character is copied. Workflow YAML parsing succeeds; current remote CI is pending. An initial 21-case focused run passed; six baseline-header checks were then added before a fresh complete run. Earlier v1 composition output is preserved; v2 uses the final header-bounded implementation and produces identical prediction/seed bytes.

Source-check receipt SHA256: `45e6bccbc68d173da6385ebcffcd8b5b3f4bbddc3a9edd4903ccb5f9b911b01d`.
Two-component composition result SHA256: `a3afb3dceb8a04f20dcaf0b5b5d9e48b327741a3b4c2bca2ad1e8d797f53fe18`.
Rejected three-component result SHA256: `1e39f8074b2685b5d4c55f0362cc192b73519019bb3923dc5fc5f6bdfa2a007e`.

Raw observations and the serial driver remain local under ignored `reports/`. All prior surface failures and original selection remain visible. Anatomical/human review, cleanup measurements, held-out action/rig/object/partner studies and release acceptance remain outstanding. The single full-project goal remains active.
