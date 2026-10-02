# Playback floor constraints and protected contact keys

The fixed crawl candidate now passes the sampled playback floor limit and
preserves its previously passing left-shin contact at authored keys. The other
three contacts still fail. The left-shin proxy also exceeds tolerance during
the full half-open frame interval, and two intermediate proposals exceed the
exact contact limit after serialization. The candidate is rejected and the
original remains selected. This is an experimental correction method, with
neither anatomy nor animation quality approved.

## Method and fixed request

`scripts/rig_mesh_trajectory.py` adds the explicit combination
`--feasibility --guarded-trials --playback-guards`. It remains a CLI experiment;
Studio does not expose this mode. Default fitting behavior stays unchanged.

The playback adapter models the actual float32 baked TRS channels, shortest-arc
quaternion interpolation and full weighted skin. Constraints cover 120 Hz,
every native key and every adjacent channel midpoint. It uses central finite
differences of continuous pre-serialization channels at the current lowest
vertex, through both neighboring endpoints and the temporal basis. These
derivatives are a surrogate for quantized values; vertex changes and finite
sampling prevent a global or continuous collision guarantee. The independent
decoded export floor screen remains required in every mesh-trajectory mode.

Whole authored intervals passing the original key contact screen are protected
through both fitting stages and trial retention. The protected row indices
`[0, 4, 8]` are the three keys of one left-shin interval, not three contacts.
Protection currently uses pre-serialization key geometry; it does not establish
continuous contact or exact serialized protection for every proposal.

Reused the original Cesium crawl and unchanged four wrist/shin proxy targets,
active at frames 54 through 56, 120 frames at 30 fps, 13 by 45 controls and
ten-frame spacing. Source SHA-256 is
`393337840a57d4290731779668996be2588e79414af7882196e7113e2c8037bf`;
draft SHA-256 is
`47ee9ccc862ef2547c6331bd12b2f768056f6d63322ff04a8b9ec81f5e3bf1c8`.
These are unreviewed geometric proxies. A stationary simultaneous hold and
anatomical palms/kneecaps have not been confirmed.

The floor/contact screens remain 5/20 mm, with the existing normalized
one-percent optimization interior margin. Original root horizontal/vertical/
step caps remain 40/120/15 mm and joint-step allowance 5 degrees, alongside
source rotation-step plus 0.5 degrees and the existing component constraints.
Declared floor/contact iteration budgets remain 30/60; equal budgets do not
imply equal computation.

## Preserved numerical failure and deterministic restoration

The first new fit stops its floor phase after 18 iterations, status 8. Float32
values stall 7.359 nanometres beyond the stricter 4.95 mm inner floor boundary,
although the 5 mm screen passes. Contact pursuit is correctly skipped. Its
candidate and archived implementation remain under
`reports/crawl-body-contact-playback-guards-v1/`; no result was overwritten.

A separate diagnostic verifies that a uniform 3.007298 mm root-control lift
restores the original floor under every unchanged motion limit while retaining
the protected key contact. The final implementation tries this bounded,
verified restoration before numerical floor optimization. In the fresh v2 fit,
it restores floor with zero optimizer iterations; metadata explicitly records
`attempted=false`, deterministic restoration and no optimizer status. This is
verified restoration, not a claim of SLSQP convergence.

The contact stage then exhausts 60 iterations, status 9. It records 837 finite
probes and retains 61 updates across both stages: one floor lift, then 36
segments, 23 lifted segments and one evaluated contact endpoint. Optimizer
exceptions preserve evaluated proposals, selected controls and failure metadata.

## Independent result

| Measure | Original | Previous guarded trial | Playback guards v2 |
| --- | ---: | ---: | ---: |
| Worst authored-key contact error | 140.697 mm | 61.173 mm | 77.493 mm |
| Left-shin key-span contact error | 14.430 mm | 61.166 mm | 20.000 mm |
| Failing contact intervals at keys | 3 | 4 | 3 |
| Playback floor depth | 7.957 mm | 5.032 mm | 4.950 mm |
| Failed floor samples out of 701 | 236 | 4 | 0 |
| Left-shin full-frame hold error | 15.502 mm | 66.823 mm | 21.028 mm |

Final decoded key errors are left shin 19.999999372 mm, right shin 69.312192 mm,
left hand 77.492970 mm and right hand 68.944960 mm. Full-frame hold left-hand
error reaches 88.080076 mm. All four contacts fail under that longer convention.
Inclusive first-to-last active-key spans and full half-open frame spans are
reported separately; neither is silently substituted for the intended hold.
The final protected key contact has only 0.628 nanometres of screen margin.

Final root horizontal/vertical/step edits are 40.000/98.736/14.664 mm. Original
raw hard motion limits pass. Original energy decreases 12.6880 to 6.8927, but
it is not the selection metric. Contact feasibility, naturalness and target
infeasibility are not established.

The independent dense observer covers four clips at 701 poses each: 2,804 poses
and 9,177,492 vertex observations. Every retained proposal is also separately
replayed with full original motion constraints, full-mesh key geometry and an
actual encoded GLB decoded at the native playback clock. This covers all 61
retained updates and 163,915,113 vertex observations. All retained proposals
pass the original raw motion checks and the decoded 5 mm floor cap. Rejected
geometry and motion are not exhaustively replayed.

Exact serialized protected-contact checks find two failed retained proposals:
contact records 554 and 691 exceed 20 mm by 3.668 and 1.093 nanometres. The
final candidate passes that key screen, but those failures remain recorded;
the contact cap was not relaxed. The guard therefore needs serialized contact
verification and an explicitly defined continuous hold before it can claim
general preservation.

Actual Godot 4.7.2 imports and seeks all four clips: 480 poses, 19 bones each,
maximum position discrepancy 3.464131e-7 m and basis discrepancy 6.601756e-7.
Duration, loop mode and one skinned surface match. Driving the original skin
from observed bones covers 1,571,040 vertex observations and reproduces the
final key floor pass and contact failures. This does not verify imported skin
weights, GPU rendering, between-key engine collision, semantics or forces.

## Evidence, validation and next work

The actual-rig playback derivative diagnostic tests three directions with
maximum normalized derivative error 3.762126e-8. Independent export floor
height parity differs by at most 1.428049e-9 m. The first diagnostic did not
archive method hashes; its weaker provenance remains explicit, followed by a
fresh archived diagnostic. Old diagnostics resolve changed live-source paths
to their immutable method archives; current v2 fitting sources match theirs.

The 287-file local receipt is
`reports/crawl-playback-guards-evidence-v1/verification.json`, SHA-256
`7d76396533e9e2421c556fe3981ed22cdd7f5b9438988ce00c8919bd1de2b84f`.
Final result/candidate hashes are respectively
`4f9ec493307eceba832feb73361ee4d592c32e385e5156a35849c650dac1764b` and
`3b048ff898dba8ee707387aeb32d76726f9db8604794c2ae050dcb36af10f578`.
Bulk reports, assets and model payloads stay local and ignored.

All 1,546 model-free Python tests and 14 JavaScript suites pass. The focused
group passes 77 cases; the new playback suite contributes 13 cases covering
actual export parity, independently evaluated derivatives, bounded restoration,
protected keys, mode validation and preserved interrupted probes. The receipt
records observed terminal completion, not a saved raw full-suite transcript.

Next define explicit continuous-contact interval semantics and verify serialized
protected contacts, then review anatomical patches and timing. Arbitrary
actions, scene/partner support, editing/style, rig transfer, loops/transitions,
imports and full-system validation remain in the same project-wide goal. No
inference, training, new seed, formal held-out use, browser/GPU rendering,
submitted developer/animator review or timed cleanup occurred in this study.
All 14 release capabilities remain unapproved.
