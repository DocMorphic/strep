# Inspect recorded native rate failures without loading a model

`scripts/native_rate_receipts.py` identifies the joints and sampled times behind
stored/unrounded rate-comparison failures. It uses Python's standard library,
reads retained vectors and source GLB identities, and writes a fresh JSON report.
It performs no model inference, pose decoding, geometry query or correction.

The comparison receipt must occur exactly once in its complete parent result.
The observation archive, source request and source rig must match their recorded
hashes. The tool checks every recorded residual, finite cap/positive scale,
ordered clock, group size, failure count and pass decision. Object arrays,
duplicate vector members, incomplete shapes and changed source identities are
rejected. Only the existing one-actor storage-comparison layout is understood;
other archive layouts need explicit adapters rather than guessed indices.

All six native groups remain visible. Rate detail maps the original skin-joint
order and the two-sample speed or three-sample acceleration stencil. Positional
rows list strict rotation ancestors; angular rows also include the joint itself.
These are structural influences, not edit permissions or a promise of repair.
Track/displacement groups retain complete counts without inferred per-row names.

Detailed rows are paginated, with 256 per report by default. Counts and pass
decisions always cover the entire recorded population. The report explicitly
states whether all rate details are included; use `--detail-offset` and
`--maximum-details` to retrieve further pages. The inspection's implementation
and every input are hashed. An archived pass remains an archived decision, not
fresh validation of a pose or of an imported animation.

```powershell
.venv/Scripts/python.exe scripts/native_rate_receipts.py `
  --receipt reports/kenney-kick-temporal-layout-v1/storage-diagnostic/fine/1-4/result.json `
  --observations reports/kenney-kick-temporal-layout-v1/storage-diagnostic/fine/1-4/observations.npz `
  --source reports/kenney-kick-temporal-layout-v1/fine/fit/contacts.json `
  --bindings reports/kenney-kick-temporal-layout-v1/storage-diagnostic/result.json `
  --actor character --output reports/my-rate-inspection.json
```

This reads the existing development archives; it does not recreate them or
require their model/numerical dependencies. The output path must be fresh.

## Verified development receipt population

The tool inspected both unchanged starts and all twenty changed proposals from
the [timing study](kenney-kick-temporal-layout-v1.md): 22 receipts, each containing
107,527 original conditions. Every detailed failure fits its untruncated report.
The retained two stored passes and seventeen changed unrounded-only passes
match the earlier decoder study. No earlier outputs were modified.

The finer layout's `1-4` positional-acceleration failure is **LeftToes**, node 53,
skin-joint slot 40, rate frame 183. Its stencil is 1.525000, 1.533333 and
1.541667 seconds. The recorded effective norm cap is 52.910208958 m/s²; the
absolute excess reconstructed from its residual/scale is 0.000332572 m/s².
Among the four permitted tracks, its strict rotation ancestors are nodes
50, 51 and 52. Its own rotation cannot move its origin. These facts explain
the direct-storage study's target; its completed outcome is recorded below.

Six standard-library tests pass, including altered provenance, complete known
row/joint mapping, unrounded-only failures, paging without changing totals,
nonfinite/invalid populations and unsupported or duplicate NPY members. The
complete source inventory adds this module: 467 Python modules and 42 Node
suites. That inventory declaration is not a full-suite pass claim. The focused
[Windows/Linux workflow at `14c8ace`](https://github.com/DocMorphic/strep/actions/runs/38180150599)
passes 689 Python checks per OS, 23 subtests and the offline editor. The
[subsequent stored-component study](kenney-kick-position-storage-v1.md) clears
the recorded positional-rate failure and replays the still-failed floor.

Local reports are retained under `reports/native-rate-receipt-study-v1`.
Actual pose/geometry/engine checks and human review remain separate. Source
selection, motion limits, training admission and release approvals are unchanged.
