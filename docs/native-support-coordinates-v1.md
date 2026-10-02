# Independently decoded coordinate repair

Bounded coordinate repair is now available through the native support CLI.
It turns the [saved coordinate diagnostic](native-support-quantized-v1.md) into
a reproducible, archived four-trial job with the existing independent final
audit. This is deterministic processing of rigged motion; Kimodo is unchanged.

**One of four completed warm-start trials passes the job's sampled checks.**
The standalone job selects trial 2 (zero-based index 1); its separate stricter
absolute-peak guard still fails. No release-quality approval is established.
The earlier coordinate diagnostic remains separate evidence.

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

## Validation and completed development evidence

Fifteen new tests exercise a discontinuous two-contact screen, frozen unrelated
controls, boxes, numerical-candidate reconstruction, independently rejected
exports, changing constraint populations, budgets and ambiguous modes. Real
four-trial fixture jobs check the archive, source-matched controls, unchanged
caps, exact warm replay and coordinate-to-coordinate chaining. Mutating an
ancestor GLB blocks a subsequent job. All **1,316 Python tests** and
**14 JavaScript suites** pass. Preceding commit `cc0d68f` passed Windows/Linux
hosted checks.

`reports/native-support-coordinate-repair-v1` is the completed development study.
It starts from all four saved `native-support-quantized-repair-v1` controls, with
eight iterations and a 2e-7-radian trust radius. Its request binds 1,193 ancestor
files and uses the same Studio v2 source, support planes, intervals and bounds.
The source SHA256 remains
`87c185ddf0dc50dec7e56bbc4c301f66896ed460a53c6c8eb6797ce5a89107c7`.
These four warm starts are optimizer controls for the same source clip and rig,
not four model-generation seeds, actions or held-out examples. Their
acceleration-time/reference-weight pairs are (0.05,0.5), (0.05,5), (0.15,0.5)
and (0.15,5).

| Trial | Starting worst excess | Final worst excess | Rate failures | Iterations / stop |
| --- | --- | --- | --- | --- |
| 1 | 0.0036578101 | 0.0036418172 | 67 / 13 / 25 / 14 | 8 / budget |
| 2 | 0.0000030829 | 0 | 0 / 0 / 0 / 0 | 7 / sampled constraints |
| 3 | 0.0109091337 | 0.0109055244 | 76 / 9 / 19 / 14 | 8 / budget |
| 4 | 0.0010863128 | 0.0010672018 | 59 / 14 / 14 / 11 | 8 / budget |

All four sampled support/preservation checks pass across 701 times, with 142
stance samples per foot. The study preserves 104,308 numerical screens and
35 decoded GLB probes, including four warm starts. Three variants still fail
the unchanged rate screen; their failures remain visible. Every final GLB
replays byte-for-byte from its controls. Rounded-key proxy/decoder component
error remains below 9.993e-16; normalized constraint differences remain below
1.226e-11. All 1,461 bound study, ancestor, replay and foot-audit files rehash.
The original input and all failed proposals remain available; the standalone
candidate is byte-identical to the passing trial. This is not Studio selection.

### Completed trial 2: qualified progress

The second warm start now completes its seven coordinate iterations with zero
failing rows under the job's unchanged four-bin source-rate screen. Its sampled
support, clock, displacement, local-angle and preservation checks pass. The
first warm start completes eight iterations and still fails 67/13/25/14 rate
rows. The remaining two also reach their budgets and fail. The final standalone
selection is the second warm start; it remains quality-unapproved.

An independent decoded audit of completed trial 2 reproduces the zero failing
rows, but also reproduces **failure of the separate 1e-7 absolute-peak guard**.
Its stricter diagnostic is not the job's 1e-5 four-bin acceptance tolerance.
Neither tolerance has changed. This distinction prevents a sampled acceptance
result from being presented as a release-quality result.

Across 142 stance samples, the left/right fully foot-owned mesh regions contain
52/53 vertices. Lowest heights remain 0.2500-1.4699 mm and 0.2500-1.3384 mm
above the authored -0.056 m plane. Maximum ankle tangential distances from the
stance start are 3.1125/2.7288 mm; per-foot vertex maxima are 3.7755/4.3785 mm.
Maximum per-vertex tangential travel is 8.9159/12.3922 mm over each stance.
These are trajectories of ankle and foot vertices, not tracked sole-contact
patches; they do not certify planted feet, contact forces or absence of skating.
The source has similar tangential motion. The different ground-zero condition
that exceeded the 30 mm displacement box remains unresolved.

`reports/native-support-plantedness-v1/result.json` binds the completed trial
and reproduces its rate and absolute-peak diagnostics. Its SHA256 is
`3bc8633705feb11c8dc85c7ad3b550eaa126ebe2489b6cc5037752e536bf4f15`.
The foot audit was made before full-study completion and retains its original
pending-selection flag. The subsequent completed study resolves that selection;
stationary sole contact, continuous collision, engine and human quality remain
unverified.

Completed result hashes:

- Fit: `5125614185cb2a674cb33c138fea448715b5e69d1756ff9634b37074f214f455`.
- Controls replay: `e6066db2b52a917f6fd24dce377ae0095236e34c83ca701983df9ed09d384ae9`.
- Rehash receipt: `fbc675b75cb98f52963317187c36e3fb63827407ed5e8c4085632beadd01a19d`.

Hosted Windows run 36949739111 exposed a 1.918e-11 proxy/decoder diagnostic
difference in two quantized-column tests. The revised tests require exact
exported quaternion keys, pose agreement within 2e-14, and grouped-versus-separate
rounded-model differences within 1e-8. They budget normalized floating roundoff
as `64 * float64_epsilon / dt²` and propagate the independently measured endpoint
errors into the exported finite difference. No production solver, clip gate or
acceptance tolerance changes. The revised full local suite passes all 1,316
Python tests and 14 JavaScript suites. Subsequent hosted run 36952881401 for
commit `23e5b3d` passes both Windows and Linux, confirming the fix.

The passing proposal still needs stricter peak, engine, geometry, broad
rig/action/scene and human cleanup validation. The other starts retain larger
optimization failures. No new
training, held-out use, engine/GPU/browser rendering, human review or release
approval is claimed. All 14 release capabilities remain unapproved and the
full-project goal remains active.
