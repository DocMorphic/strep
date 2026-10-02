# Full-frame crawl contact study: preserved hold, rejected animation

The explicit frame-hold fit preserves the previously passing left-shin proxy
through its sampled full frame interval and keeps the sampled floor within
5 mm. Independent decoding of all 55 retained proposals finds no protected
hold or floor failures. The other three contacts still fail, so the exact
original remains selected. This is evidence about a bounded correction method,
not a usable crawl animation or general motion quality approval.

## Fixed inputs and changed condition

Used the same original Cesium clip, unchanged four wrist/shin proxy patches and
targets, active at frames 54 through 56, 120 frames at 30 fps, 13 by 45 controls
and ten-frame control spacing. Source SHA-256:
`393337840a57d4290731779668996be2588e79414af7882196e7113e2c8037bf`;
draft SHA-256:
`47ee9ccc862ef2547c6331bd12b2f768056f6d63322ff04a8b9ec81f5e3bf1c8`.
Original model/input provenance remains in the prior crawl/rig-transfer records.
No inference, training or new seed was used.

The [contact-clock implementation](mesh-contact-clock-v1.md) adds explicit
`--contact-clock frame-hold` alongside
`--feasibility --guarded-trials --playback-guards`. This is a different authored
condition from the prior authored-key study: the last active frame's tail now
belongs to the hold. Quantized contact samples are also included in fitting.
The patches are still unreviewed geometric proxies; neither anatomical support
nor the intended stationary simultaneous hold has been confirmed.

Floor/contact iteration budgets remain 30/60. Original edit/step caps, 5/20 mm
screens, source rotation-step allowance and inner optimization margin remain.
Identical declared budgets do not imply equal computation or equivalent tasks.
The frame-hold condition is not silently applied to historical results.

## Fit and final export

The existing verified 3.007298 mm uniform root-control lift restores the floor
before numerical optimization. Its metadata records deterministic restoration,
zero optimizer iterations and no optimizer status. Contact fitting exhausts
60 iterations, SLSQP status 9. There are 913 recorded probes and 55 retained
updates across both phases, including one initial floor lift and 54 contact
updates. The protected mask includes three original left-shin keys plus its
18 quantized hold samples.

| Independently decoded measure | Original | Prior authored-key fit | Frame-hold fit |
| --- | ---: | ---: | ---: |
| Left-shin error over full frame hold | 15.502 mm | 21.028 mm | 20.000 mm |
| Worst contact error over full frame hold | 148.539 mm | 88.080 mm | 86.263 mm |
| Failing intervals over full frame hold | 3 | 4 | 3 |
| Worst contact error at authored keys | 140.697 mm | 77.493 mm | 78.486 mm |
| Playback floor depth | 7.957 mm | 4.950 mm | 4.950 mm |
| Failed floor samples out of 701 | 236 | 0 | 0 |

Final key errors are left shin 19.015878 mm, right shin 71.241978 mm,
left hand 78.485835 mm and right hand 78.061065 mm. The left-shin full-hold
maximum is 19.999998779 mm, only 1.221 nanometres below the cap. Left-hand
full-hold error reaches 86.263318 mm. The floor maximum is 4.949999817 mm at
1.891666667 seconds. Three contacts fail under both key and full-hold screens.

Root horizontal/vertical/step edits are 40.000/96.361/13.364 mm. Raw full
motion checks pass under the existing numerical allowance; minimum normalized
motion constraint is -2.388851e-10, rather than strictly nonnegative. No bound
was relaxed. Original energy falls 12.6880 to 7.6570, but it is not the selection
metric. Predicted support-speed p95 remains 0.466366 m/s versus 0.490969 in the
source; a lower speed does not establish a planted contact.

Both solver/contact screens fail overall. The failed candidate, original,
controls, traces and independent inspections are retained locally. Numerical
and quality approval remain false; target infeasibility is not established.

## Retained proposals and engine evidence

Independent replay checks finite layout for all 913 recorded control vectors.
Every retained proposal is separately checked with the original full-Jacobian
motion limits and full-mesh raw key protection, then encoded as an actual GLB
and independently decoded at 701 poses. The hold observer independently
enumerates the half-open frame interval; it does not use the fitting contact
layout routine. This covers 55 retained updates and 147,792,315 vertex
observations. All retained decoded floors pass the exact 5 mm cap and all
protected decoded holds pass the exact 20 mm cap. No tolerance is added to
those two decoded screens.

The maximum measured difference between fitting playback contact values and
independent full-mesh contact distances is 3.463896e-16 m across these retained
proposals. This is a measured comparison on this request, not a universal
serialization guarantee. Rejected geometry and motion are not exhaustively
replayed. The final endpoint's saved parameters match the retained controls.

A separate dense four-clip observer covers original, previous unprotected
guarded trial, prior authored-key playback fit and current full-frame fit:
2,804 poses and 9,177,492 vertex observations. Inclusive key spans and full
half-open frame spans remain separate. The prior unprotected candidate still
fails four floor samples and all four contacts; the authored-key fit's
full-hold shin failure remains visible.

Actual Godot 4.7.2 imports and seeks all four clips: 480 poses, 19 bones each,
maximum position discrepancy 3.464131e-7 m and basis discrepancy 6.601756e-7.
Durations, loop mode and one skinned surface match. Reconstructing the original
skin from observed engine bones covers 1,571,040 vertex observations and
reproduces final key floor success and contact failures. Imported skin weights,
GPU rendering, between-key engine collision, forces and action correctness are
not established by this audit.

## Provenance and remaining work

The 240-file receipt at
`reports/crawl-frame-hold-evidence-v1/verification.json` verifies immutable
inputs, current/archived fitting methods, actual outputs, dense/engine/replay
helpers and their archives. SHA-256:
`6417cd87b46c89f92357949f7b1ea2193a24094a481cdb0f539f7a2277f4e984`.
Result/candidate hashes are respectively
`76583c6bea895d519714170fec0674b09267d116c3f22aebb6d689ca5ff75afa` and
`c638651bd985835edec75e860cb9582a882cfd28cbe9ca6ccf05f0dc71d3819a`.
Historical source references resolve to immutable archives. All fitting,
observer, engine and replay workers are terminal; their source was not modified
while they ran. Generated study payloads remain local and ignored.

All 1,564 Python tests and 14 JavaScript suites passed for the unchanged
implementation; hosted run 36988175988 passes Windows and Linux. No new
full-suite run was needed for this result-documentation batch.

Next expose the tested clock/fitting choice in Studio with unchanged source
retention and visible failures, and obtain review of anatomical patches and
contact timing before changing targets. The selected clock is currently global
to this CLI request; per-contact timing semantics and moving object/partner
targets require their own authoring paths. No continuous collision certificate,
human review, cleanup timing, formal reserved held-out use or release approval
follows from this single fixed request. All 14 capabilities remain unapproved;
arbitrary actions, scenes/partners, edits/style, rig transfer, loops/transitions,
imports and full-system validation remain in the same project-wide goal.
