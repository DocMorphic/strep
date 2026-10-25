# Corrected wave: forward playback, completion and restart

The corrected CesiumMan wave passes sampled forward playback with the existing,
explicitly acknowledged 30 Hz terminal-hold adapter in Godot 4.7.2. This extends
the [earlier seeking comparison](studio-surface-wave-engine-v1.md); it does not
erase the ordinary-import endpoint clock failure or approve transitions.

## Continuous player test

The study imports the unchanged candidate GLB once, installs the hold, then
runs five schedules on the same AnimationPlayer. Each source-time observation
uses `advance(next_time - previous_time)`. There is no seek, native-track
replacement, source resampling, root extraction or explicit stop/reset between
runs. Geometry observations are written in chunks of at most 400 while that
same player continues, avoiding a restart at a batch boundary.

| Update schedule | Source-domain observations |
| --- | ---: |
| Complete native-key/eighth/960 Hz clock | 4,737 |
| 30 Hz plus exact source endpoint | 121 |
| 60 Hz plus exact source endpoint | 240 |
| Seventeen-frame steps plus endpoint | 9 |
| Repeating uneven frame-time pattern | 143 |

The uneven pattern repeats 1/144, 1/24, 1/60, 1/120 and 1/15 seconds, clipping
only the final step to the exact source endpoint. Each run additionally checks
the middle of the terminal hold, advances past the adapted end by 1 microsecond,
and advances another 0.25 seconds after completion. The next run calls `play`
on that naturally completed player and checks its initial pose again.

All 5,250 source-domain observations pass the unchanged 1 ns clock, 0.0001
matrix-element, 0.1 mm imported-skin and 5 mm floor thresholds. Maximum reported
clock error is zero; maximum matrix-element error is 9.802945e-7, skin error
is 0.056550 mm, and floor penetration is 4.821438 mm. The complete original
3,273-vertex imported skin is checked, retaining the importer's raw weights.

All five runs remain active throughout the source and middle of the hold,
emit exactly one completion signal after crossing the adapted end, then stay
stopped without emitting another signal. All 15 terminal observations match
the native final pose within the same pose, skin and floor limits. The final
held floor depth is 3.955448 mm. Imported track fingerprints remain unchanged
through all five runs and agree with the previous seeking study.

The clip SHA-256 remains
`7678f1bafd355cf3f368c0d2d263e033f1a65ecb657553fa5517871f48d748f0`.
Source duration is 3.9666666984558105 seconds; adapted playback duration is
4.000000031789144 seconds. This is an explicit duration contract for this clip,
not a silent extension of ordinary-import acceptance.

## Evidence and limits

The guarded job completed in 77.83 seconds including admission, with peak
observed process-tree RSS of 238,428,160 bytes. All 78 resource observations
replay. An independent standard-library verifier reconstructs all five clocks
from source bytes and the declared schedule, checks raw clock/playing/signal
observations and the pass decisions, and verifies input/capture hashes. Raw
engine output, diagnostics, result and verifier are retained locally in
`reports/studio-surface-wave-playback-v1/` in the development checkout.

The test covers manual forward AnimationPlayer advancement at speed 1, ordinary
imported tracks plus the explicit hold, repeated completion and restart. It
does not cover wall-clock rendering performance, reverse playback, looping,
crossfades, root-motion extraction, gameplay markers, physics, GPU skinning,
contacts, continuous geometry or perceived quality. A stopped final pose and
a correct restart do not imply a seamless animation loop. No quality or release
gate changes, and the original remains selected in Studio.

## Connection-pose screen

A separate read-only diagnostic compares the corrected wave's end against its
own corrected start and the starts of seven existing CesiumMan transfers. It
uses native clocks, complete vertex populations and unchanged world placement.
It also reports root-translation-relative skin gaps, without changing any
asset. Native last/first-interval joint velocities are reported separately from
the zero outgoing velocity after a terminal hold. No transition is generated,
no semantic compatibility is inferred, and there is no new quality threshold.

The corrected wave's direct repeat has a maximum vertex gap of 109.327 mm,
root-relative gap of 108.762 mm and local joint-angle gap of 12.424 degrees.
Both endpoints satisfy the floor limit, but the poses do not form a seamless
loop. This does not make the one-shot wave invalid; looping needs a separate
authored treatment.

| Existing destination start | Maximum raw vertex gap | Incoming floor depth |
| --- | ---: | ---: |
| Jump/land | 222.120 mm | 10.653 mm |
| Crawl | 1,111.476 mm | 7.171 mm |
| Dance | 165.353 mm | 8.863 mm |
| Original wave | 108.272 mm | 8.322 mm |
| Kick | 711.309 mm | 7.370 mm |
| Get-up | 1,687.071 mm | 163.640 mm |
| Run/roll/stand | 616.072 mm | 6.801 mm |

Every original destination starts outside the unchanged 5 mm floor limit.
Large posture differences, especially entering a ground action, also require
deliberate action sequencing; arbitrary pairs are not assumed appropriate.
Raw world gaps include placement differences. Removing root translation still
leaves gaps, so translating the root alone cannot match these connection poses.

Evidence remains in `reports/studio-surface-wave-boundary-v1/` in the
development checkout. Its guarded job completed and all 24 resource observations
replay. The next transition work needs explicit cuts, destination repair and
support-aware bridges; neither direct chaining nor automatic looping is approved
by the successful forward-playback result.
