# Joint search for planted native motion

The offline joint plant job varies native thigh, shin and foot rotations together
to address the rate failures left by deterministic foot centering. It checks
fixed source foot contacts, support geometry and source-relative motion rates
in both raw GLB and a shadow of editable native serialization. Neither a lower
optimizer score nor an imported file establishes an acceptable animation.

## Controls and acceptance

`native_joint_plant.py` frees three local rotation-vector components for each
of the three leg joints at interior native keys. A full 120-key edit window
has 1,053 scalar controls. Each component box includes the authored rotation
ball; separate radial constraints reject excessive box corners. All root and
other translations, unrelated joint tracks, native key clocks, skin/mesh
payloads and outside/boundary keys remain protected. Original-relative
angular and ankle displacement bounds are cumulative, even with a warm seed.

The source/base/draft-bound policy and fixed source vertex patch come from
[explicit foot planting](native-foot-plant-v1.md). Each original patch vertex
has its own stance-start tangent anchor. Contacts use 120 Hz samples plus exact
stance boundaries; tangential speeds use the actual intervals between samples.
This job also requires the authored lower clearance, with the existing 1e-8 m
numeric allowance, alongside maximum support gap, edit budgets and original
four-bin positional/angular speed and acceleration caps with their unchanged
1e-5 allowance. Only affected joints enter the search model; the separate
serialized audit still checks every joint.

No ankle-only reach corridor is precomputed. Direct rotations preserve bone
lengths through the existing hierarchy, allowing searches the earlier exact
ankle-target IK rejected. That freedom does not prove a feasible solution.

`native_joint_plant_job.py` offers two bounded searches. The default uses
colored FP32-key finite differences and LP minimax/L1 directions, followed
by up to ten independently decoded step sizes. The optional coordinate method
screens six bounded step sizes in each sign and independently decodes up to
three ranked choices. Both accept intermediate steps only when the worst
positive constraint deficit improves, or when the same worst deficit has a
smaller squared deficit. That ranking can increase the number of failing rows;
only the complete final gates determine output selection.

Raw proposals are exported and read by the scalar native GLB sampler. The
optional shadow preview rounds rotations through the existing FP32 quaternion
and FP32 matrix path before a separate export/decoder check. It is a model of
the representation boundary, not verification of actual NPZ conversion.
Repeated identical GLB hashes reuse the first independently decoded values;
reports identify that first file and the number of unique decoded contents.
Every proposal file and hash remains saved. Batch interpolation and scalar
decoding differ by up to 1.347e-12 in a near-identity fixture; final acceptance
always uses the scalar decoder and the unchanged gates.

Selection requires passing independent raw and shadow audits and their signed
constraint populations. If any gate fails, or the input is already satisfactory,
the selected GLB is an exact copy of the input. Controls, requests, original
source/seed/method hashes, method archives, rejected probes, progress and audits
remain available. A selected raw proposal still needs actual editable native
conversion, followed by an independent contact audit of that converted preview.
No Studio route or training admission is added by this CLI experiment.

## Matched development trials

The same historical wave, kick and crawl inputs, numerical stance intervals
and original authoring bounds are retained. Policies specify 1 mm patch anchor
error and 5 mm/s speed. These are explicit development limits, not universal
realism thresholds or human contact annotations. The first search uses four
iterations at .001 radian trust; a second starts from those rejected proposals
with eight iterations, .001 for wave and .01 for kick/crawl. Trust controls the
optimizer step; it does not widen authoring budgets or acceptance limits.

| Trial | Clip | Anchor error, mm | Patch speed, mm/s | Failed rate rows | Selection |
| --- | --- | --- | --- | --- | --- |
| Four iterations | Wave | 0.513110 | 5.000083610 | 0 / 2 / 4 / 3 | Exact input |
| Four iterations | Kick | 18.028257 | 164.389488 | 362 / 6 / 85 / 17 | Exact input |
| Four iterations | Crawl | 331.478140 | 1633.264953 | 3 / 4 / 4 / 1 | Exact input |
| Eight more | Wave | 0.513110 | 5.000000731 | 1 / 1 / 4 / 0 | Exact input |
| Eight more | Kick | 11.579421 | 59.396348 | 583 / 174 / 465 / 221 | Exact input |
| Eight more | Crawl | 291.456447 | 1269.092724 | 16 / 16 / 32 / 14 | Exact input |

Rate groups are position speed/acceleration and angular speed/acceleration.
The wave's original deterministic plant had 66 failing rows; joint search
reduces that to nine and then six. It still exceeds patch speed and rate gates.
The kick's lower contact errors accompany many more failing rate rows. A
decrease in worst merit therefore cannot be reported as motion-quality
improvement. Crawl now exports proposals, but none passes. No infeasibility
certificate follows from these finite searches.

Both studies finish with zero raw selections and zero actual native contact
acceptances; actual NPZ conversion is not invoked for their failed proposals.
Each imports six selected/rejected clips into headless Godot, covering 720
native frames, 77 bones, one skin and non-looping playback. Maximum position
error is 8.945e-7 m and basis-element error 9.795e-7. Those CPU checks establish
import/pose fidelity only.

A separate four-iteration coordinate follow-up starts from the closest wave,
at 2e-7 radian trust. It completes 3,672 numerical screens and independently
decodes ten unique GLB contents. The fixed-patch contact gates finally pass:
anchor error is 0.513110 mm and speed is 4.999905138 mm/s. Three angular-speed
rows still fail, with raw and shadow worst normalized excess 1.13333427e-7.
The input therefore remains exact and actual NPZ conversion is not attempted.
Both selected and rejected clips pass another 240-frame CPU import comparison,
with maximum position error 5.437e-7 m and basis error 9.795e-7. Contact success
does not override rate failures or establish an acceptable animation.

## Invocation and verification

Use the existing source-matched support draft and planting policy, with a fresh
output directory and an optional preserved-track seed:

```powershell
.venv\Scripts\python.exe scripts/native_joint_plant_job.py original.glb current.glb support-draft.json plant-policy.json fresh-output --seed warm.glb --iterations 4 --trust 0.001
```

Add `--coordinates --trust 0.0000002` for bounded coordinate screens, or
`--raw-only` to explicitly omit the shadow representation. Raw-only selection
still cannot certify editable native conversion. Iterations are limited to
1–16; default search trust is at most .02 radians and coordinate trust at most
.001. The CLI uses the shared heavy-worker lock and one numerical thread.

126 model-free focused tests pass, including the new joint cases and previous
support, planting, diagnostic, round-trip, feasibility and coordinate tests.
They cover all observed toy graph dependencies, colored/individual derivatives,
independent raw/shadow decoding, radial rejection, frozen keys, failed proposal
retention, invalid modes, custom contact constraint populations and exact-content
cache references. A constructed oscillating toy actually passes every final
gate without mocked acceptance; it is software validation, not human review
or a Kimodo training example. New cases join hosted source CI. Prior commit
7c255e6 passes all four jobs in workflow 37058568813.

The immutable local studies are `reports/native-joint-plant-canary-v1` and
`reports/native-joint-plant-followup-v1`, plus the closest-wave
`reports/native-joint-plant-coordinate-v1`. A receipt binds public source and
immutable evidence at `reports/native-joint-plant-validation-v1/verification.json`.
Public Git excludes generated clips,
model/character payloads, credentials and detailed local records. This work
does not approve continuous clearance, force/balance consistency, rendered
appearance or animation semantics. There are no real model updates or human
submissions. All 14 release capabilities remain unapproved, the formal 72-by-five
population is untouched and the full-project goal remains active. General
actions/styles, scene/object/partner/finger targets, rig transfer, reviewed
licensed learning data and human cleanup/release evidence remain required.

A later bounded coordinate follow-up accepts the historical wave after actual native conversion. [Studio planted-contact authoring](studio-native-plant-v1.md) documents that separate result and exposes the guarded operation in both authoring panels. Earlier failures above remain unchanged.
