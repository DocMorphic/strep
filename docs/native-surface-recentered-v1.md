# Optional candidate-centered surface restoration

Native surface fitting can now use `--restoration-model recentered` with one to
four restoration steps. The default remains `measured-cap`. This extends the
existing explicit storage-vector option to surface-vector proposals; it does
not switch authoring defaults or acceptance limits.

When a full proposal fails protected conditions after actual export/decoding,
the optional repair rebuilds its local derivatives and surface witnesses at
that rejected export. It starts from the same originally feasible animation
as ordinary surface fitting. It cannot adopt an infeasible starting clip.

Every rebuild retains the exact original ordered native caps and scales.
Contact no-worsening bounds use the last accepted motion's complete contact
reference. Geometry witness guards use the last accepted motion's worst
positive witness bound, even when the new witnesses or lifted offsets differ.
A rejected export cannot become a new, weaker acceptance baseline.

Each repair solve uses the original absolute control bounds, with a local
trust radius no larger than the primary radius and halved for subsequent
repairs. Up to ten fractions of each direction are actually serialized,
decoded and checked with the complete declared mesh population. A rejected
export with a smaller protected defect may become the next local working
point. It remains rejected and does not replace the accepted animation.

Retention still requires every original native condition to pass and complete
geometry to improve without worsening contact rows. Full mesh regression
overrides a passing local witness. The model is an affine proposal, not a
continuous collision certificate or a realism rating. No release, training
target, engine, support, semantic or review approval follows from retention.

The request and optimization result record the explicit mode. Completed atomic
iteration receipts include repair anchors, controls, model identities, solver
statuses and actual probe decisions. Interrupted jobs still require their
terminal guard record and cannot inherit a completed result.

Example, with already prepared and hash-bound scene inputs:

```powershell
python scripts/native_scene_fit.py scene-contacts.json scene-permissions.json `
  fresh-surface-fit `
  --proposal-model surface-vector --geometry-policy geometry-policy.json `
  --plane-guidance minimum-envelope --iterations 1 --trust .02 `
  --restoration-model recentered --restoration-steps 1
```

Run this inside the project's numerical environment and resource guard. The
floor-only example in the development study supplies no invented contacts;
object and partner scenes keep their explicitly authored contact policies.

## Validation

All 207 affected local checks pass, including actual source-bound exports,
continuations, original cap replay, full geometry archives and atomic iteration
receipts. An additional targeted check passes for rebuilt geometry witnesses
retaining the original bound: 208 distinct affected checks in total. Numerical
conic fixtures exercise repaired acceptance and native, contact and full-mesh
rejection; these fixtures do not establish realism on a generated character.

The initial test harness accidentally held the same lock as integration jobs;
27 jobs could not start. Its failed record remains retained. The corrected
harness holds the project lock while test jobs acquire their own local lock.
All 269 corrected-suite and 27 additional-check resource observations replay.
The focused Windows/Linux workflow now includes the surface and restoration
suites. Fresh hosted results and the development clip experiment remain pending.
