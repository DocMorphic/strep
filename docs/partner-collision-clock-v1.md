# Complete partner collision clocks

Development component, 2026-10-18. The preceding high-five correction improved
point contact and overlap at frame 60. That does not establish clearance
elsewhere in its 120-frame animation. This study checks the complete original
integer clock in the exported files before choosing the next correction.

## Coverage component

`PartnerCollisionClock` validates the coverage of caller-bound depth-query
journals. The caller declares the original frame count, every variant and
actor, each actor's complete vertex count, the raw or saved representation,
and the original depth screen. Every ordered pair of distinct actors must
have one observation for every frame and variant. It does not inspect action
names or infer a contact window from the prompt.

Missing endpoints, variants or opposite directions leave coverage partial.
Duplicates cannot increase coverage. A malformed batch makes no partial state
update, and input/report mutation cannot alter retained observations. Tied
peaks are ordered deterministically, independently of batch arrival order.

Every supplied decision is recomputed at the exact original threshold.
Nonfinite depths, inconsistent failure counts, incorrect vertex populations,
missing fields and invalid peak indices reject. Completing a failing audit
means complete observations; it does not mean the animation passes.

Limits are explicit: one to 10,000 integer frames, up to eight variants and
eight actors, at most 100,000 complete pair conditions and 4,096 observations
per added batch. Source vertex counts are bounded positive integers. There is
no truncation to fit these limits. The bounded missing-condition excerpt is
diagnostic only; completeness uses the entire expected population.

This component validates a journal. It does not requery geometry, verify
asset/resource/source bindings or certify edge crossings, continuous time,
self-collision, dynamics, semantics, engine playback or human approval.
Those obligations remain separate and all release flags remain false.

## Saved-file study

The original native-conditioned pair and the retained contact-vector pair
use their unchanged GLBs and authored scene placements. Each of their 120
frames queries all 18,056 vertices in both directions against the partner's
original 36,108 triangles, retaining all eight skinning influences. The
existing 5 mm development screen stays unchanged. Conservative hull pruning
reduces work; retained points still use the original bounded signed-distance
query with at most 32 simultaneous points. No epsilon is added to depth.

Four-frame workers execute serially with owned locks, a 512 MiB process-tree
cap, 600 MiB available-memory reserve, 15-second stable admission and a
300-second execution cap. Each completed chunk preserves its observations,
inputs, resource trace and replay. A completed chunk is explicitly not a
completed full clock. The final aggregate must cover exactly 480 distinct
direction queries, spanning 240 saved variant-frames.

All 30 workers completed. Every original integer frame was queried in both
directions for both saved variants. The result changes the next correction:
frame 60 was not the worst collision pose.

| Saved-file diagnostic | Original native | Contact-vector correction |
| --- | --- | --- |
| Deepest penetration over all 120 frames | 32.272 mm, frame 36 | 32.448 mm, frame 37 |
| Frames exceeding the existing 5 mm screen | 23 | 22 |
| Summed vertex exceedances across all queries | 6,492 | 6,688 |

Eight frame maxima worsen: 35, 37, 56, 57, 58, 64, 65 and 66. No originally
passing frame becomes a new depth-screen failure. These counts concern frame
maxima; individual direction rows remain preserved separately. Fewer failed
frames does not compensate for worse peak depth or more vertex exceedances.

At frame 60, the earlier independent saved replay measured a reduction from
13.483 to 10.288 mm. This complete clock instead exposes deeper overlaps
before that event. The candidate remains rejected. All three point contacts
still pass their existing development screens, while its floor and native
motion ceilings still fail as previously independently measured.

The clock study applies the authored world placement after skinning, matching
the local optimization field. Its original and corrected files use exactly
the same method and placements. No equivalence to an unchecked raw clock or
continuous trajectory is inferred from earlier serialization fidelity.

All **36 coverage tests pass locally**, with no failures or skips. Tests
cover missing final conditions, both directions and all variants/actors,
strict boundary decisions, complete-but-failed clocks, transactional batches,
owned inputs/reports, deterministic ties, static/long clocks and invalid data.
Hosted results and the independent journal/resource replay will be recorded
after completion. Detailed files remain local under
`reports/contact-vector-saved-clock-v1`; source clips and failed trials are
never overwritten. Raw-clock, subframe, edge-only and self-collision checks
remain outstanding. The qualified partial reference, default selection and
entire-project release requirements are unchanged.
