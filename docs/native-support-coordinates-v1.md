# Independently decoded coordinate repair

Bounded coordinate repair is now available through the native support CLI.
It turns the [saved coordinate diagnostic](native-support-quantized-v1.md) into
a reproducible, archived four-trial job with the existing independent final
audit. This is deterministic processing of rigged motion; Kimodo is unchanged.

**The new real four-seed study is still running.** No accepted motion or release
approval is established by that study yet. The earlier single-seed diagnostic
still fails three position-speed rows and remains separate evidence.

## Method

Each iteration starts from an independently exported and decoded constraint
vector. The structural graph identifies native controls connected to positive
rows. For each such control, the search screens both signs at six fractions of
the trust radius: 1, 0.5, 0.25, 0.1, 0.05 and 0.025. Changes intersect the original
parameter boxes. Zero changes and repeated clipped coordinate changes are
skipped. Every screen evaluates the full signed constraint vector with float32
quaternion keys and float64 interpolation; inactive rows remain present.

The job retains each iteration's starting vector, columns, radius, numerical
screens and scores. These records can reconstruct every numerical candidate.
Numerical screens are distinct from exported GLB probes.

The three best promising screens, at most, are separately exported and decoded.
A decoded step replaces the current controls only when its worst positive
normalized excess decreases by more than 1e-12, or ties within 1e-12 while its
squared positive excess decreases by more than 1e-15. Rejected exports remain
saved. A promising proxy cannot override this decoded gate. If no choice is
accepted, the trust radius shrinks by four; below 1e-9 radians the search reports
a stall. It can also reach the iteration budget. Neither outcome certifies
infeasibility.

The final native job checks every rate group, sampled support heights,
displacement and local angles, native clocks, untouched channels and frozen,
free, root and other-branch motion. These checks retain the existing authoring
limits, selected-input four-bin caps and 1e-5 rate tolerance. Solver success or
a lower error cannot select a clip that fails the final audit.

## Reproduction

```powershell
.venv/Scripts/python.exe scripts/native_support_job.py source.glb draft.json `
  reports/fresh-coordinate-repair --joint-rates --joint-swivel `
  --joint-foot-orientation --repair-from reports/completed-warm-study `
  --repair-iterations 8 --repair-trust 0.0000002 --repair-coordinates
```

Coordinate mode implies rounded-key screening; `--repair-quantized` is not
required. It uses 1–32 iterations and a positive trust radius up to 0.001 radians.
The ordinary Studio, smoothing and minimax repair defaults remain unchanged.

The warm folder must be an immediate completed `reports/` study, source/draft
matched and hash intact, with four ordered orientation, minimax repair or
coordinate repair trials. Each saved vector must reproduce its previous GLB
exactly. The new request binds ancestor inputs, archived implementations,
outputs, probes, controls and result hashes. Coordinate jobs can supply a later
warm start without dropping their ancestry. The new implementation is archived
with the other imported methods. A changed ancestor blocks a new job before
its folder is created.

## Validation and pending evidence

Fifteen new tests exercise a discontinuous two-contact screen, frozen unrelated
controls, boxes, numerical-candidate reconstruction, independently rejected
exports, changing constraint populations, budgets and ambiguous modes. Real
four-trial fixture jobs check the archive, source-matched controls, unchanged
caps, exact warm replay and coordinate-to-coordinate chaining. Mutating an
ancestor GLB blocks a subsequent job. All **1,316 Python tests** and
**14 JavaScript suites** pass. Preceding commit `cc0d68f` passed Windows/Linux
hosted checks.

`reports/native-support-coordinate-repair-v1` is the running development study.
It starts from all four saved `native-support-quantized-repair-v1` controls, with
eight iterations and a 2e-7-radian trust radius. Its request binds 1,193 ancestor
files and uses the same Studio v2 source, support planes, intervals and bounds.
The source SHA256 remains
`87c185ddf0dc50dec7e56bbc4c301f66896ed460a53c6c8eb6797ce5a89107c7`.
Partial iteration records are observations, not final acceptance evidence.

After terminal completion, all final proposals still need controls replay,
evidence rehash and a recorded selection decision. Passing proposals also need
engine, geometry, broad rig/action/scene and human cleanup validation. No new
training, held-out use, engine/GPU/browser rendering, human review or release
approval is claimed. All 14 release capabilities remain unapproved and the
full-project goal remains active.
