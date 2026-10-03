# Native planting with fixed game-frame proposal constraints

The opt-in joint planting search now constrains every declared game-frame
contact clock before exporting a proposal. This addresses the observed gap
between a native legacy-clock pass and imported frame-clock failures. It
does not substitute a native pose model for an actual engine import.

`scripts/native_joint_plant_job.py` accepts `--frame-sampling` and
`--exterior-seed-ramp`, independently or together. Existing default and Studio
planting behavior remain unchanged. These are experimental CLI options;
they are not enabled automatically for a user-authored action.

## Fixed clock population

`FramePlantProblem` keeps the original uniform 120 Hz motion-rate samples,
source caps, four source bins and tolerance exactly. It adds all twelve
30/60/120 Hz × 0/0.25/0.5/0.75 frame clocks from the existing fixed sampling
contract. Every requested clock needs at least two stance frames; an
unavailable population rejects initialization rather than substituting
boundaries or a different clock.

The geometric sample union contains the legacy clock, exact stance/edit
bounds, native keys/midpoints and every new game-frame point. Anchor error,
foot-region clearance and maximum gap are checked on that union. Velocity
is checked separately on the unchanged legacy contact clock and adjacent
ticks of each game-frame clock. Near-coincident native keys and exact
endpoints are never differentiated as a combined clock. No rate or phase
is dropped after seeing an output.

Root and translation tracks, unrelated rotations, source mesh/skin payloads,
native clocks, original edit bounds and frozen keys stay protected. Both raw
FP32 and shadow-native exports are independently decoded for search step
selection. Final original serialized audits still cover all joints and
the authored contact/support/edit conditions. Source-rate limits are never
omitted or rebuilt around a fitted clip.

The existing region contract requires at least one mesh region whose positive
influences all lie in the relevant foot subtree. A mixed sole without such a
region remains rejected, even if one foot has the dominant weight. No weight
is dropped or renormalized to admit it. Whole-foot/body penetration and more
general deforming contact regions still need separate support.

The new model uses the source native skin and pose decoder. The actual
engine can still change joint numerics, bindings/weights and contact speeds.
Neither a native frame-clock pass nor the shadow-native approximation
certifies imported playback, actual SOMA-native NPZ conversion, GPU
appearance or continuous collision.

## Exterior seed ramps

The second option initializes rotation-vector corrections outside the
native keys whose timestamps fall in the stance. Cubic Hermite polynomials
join their estimated edge slopes to zero correction and zero slope at the
original edit boundaries. Interior stance-key vectors stay exact;
source rotations are retained at boundaries and outside the edit window.
An exterior component overshoot rejects the proposal instead of clipping it.
All radial angle, displacement, contact and source-rate checks still apply.

These polynomials shape **native key values**. The exported rotation tracks
remain LINEAR/SLERP, so continuous derivatives or C1 motion are not promised.
Changing a key just outside a fractional stance endpoint can also change
interpolated poses inside that stance. Every result therefore needs the same
independent geometric, rate, shadow and engine checks. The solver is free
to revise this initial ramp; smoothing is not a final constraint or approval.

## Reproducible use

With already acquired, source-bound local inputs:

```powershell
.venv/Scripts/python.exe scripts/native_joint_plant_job.py source.glb base.glb draft.json policy.json reports/fresh-frame-fit --seed prior-proposal.glb --iterations 8 --trust .001 --frame-sampling --exterior-seed-ramp
```

Use a fresh output directory. Requests archive the sampling contract and
hash, input/method hashes and the explicit ramp description. Unique decoded
probes, raw/shadow deficits, final original audits, selected input/proposal
and controls remain separate. Failed proposals retain the supplied base;
neither source/control binding nor saved success labels supply human quality,
training admission or release approval.

## Matched development study

`reports/native-frame-roll-v1/` freezes the existing female Quaternius
run/roll/stand source, prior raw seed, original draft and separate 4.99 mm/s
proposal target. The public policy remains 1 mm anchor error and 5 mm/s
patch speed. All three new variants use eight joint LP iterations with
0.001 radian trust: exterior ramps alone, game-frame constraints alone, and
both together. Source rates remain present in every variant.

The prior completed original search is a historical comparator, not a new
run. Its archived methods/inputs remain verified. Only the opt-in job
orchestration source differs; the restoration and original audit functions
are structurally identical, and redecoding reproduces the historical final
merit and complete original audit. Each new proposal receives an independent
original public audit and actual headless Godot import across the legacy
and all twelve frame-clock populations.

All three searches and their actual imports complete. They add 1,836
source/proposal pose observations across six scene imports, each with
65 bones and three surfaces. Repeated source observations and the reused
612-observation historical control are not new held-out action coverage.

| Variant | Native left/right speed (mm/s) | Original rate failures: speed/acceleration/angular speed/angular acceleration | Worst imported frame speed (mm/s) | Selected output |
| --- | --- | --- | --- | --- |
| Historical original | 5.536534 / 16.080120 | 32 / 23 / 4 / 10 | 16.120047 | Exact input |
| Exterior ramps | 6.167438 / 12.030422 | 28 / 22 / 4 / 10 | 12.137823 | Exact input |
| Game-frame constraints | 7.385402 / 9.625968 | 24 / 23 / 4 / 14 | 9.780831 | Exact input |
| Frames plus ramps | 7.482717 / 10.854916 | 24 / 22 / 4 / 14 | 10.889149 | Exact input |

Support/edit bounds and authored clearance pass, but all native contact/rate
and combined imported contact checks fail. The frame-constrained search
trades lower right-foot speed for worse left-foot anchors/speed and more
angular-acceleration failures than the historical comparator. Adding ramps
is not uniformly better than adding frame constraints alone. Reduced worst
deficit or one foot's speed does not establish animation-quality improvement.
Objective sums from different clock populations are not directly comparable.

An archive-closure fix after the terminal study includes the sampling module
even for ramp-only requests, because importing the ramp module loads that
dependency. Executed methods stay archived separately. The study-wide request
already binds that dependency and each actual engine audit archives it.
The correction changes method archiving, not the executed fitting functions
or constraints; no completed search is rerun simply to publish the metadata fix.

The final regression checks pass 1,859 model-free Python tests, all 16
JavaScript suites and 215 CPU adapter/native-pipeline tests. Sixteen new
fixtures cover all fixed clocks, unchanged source caps, scalar raw/shadow
decodes, structural finite differences, native-key exterior ramps, hard
overshoot rejection, unsupported mixed soles, saved flags/dependencies and
passing/failed input retention. Two initial mixed-sole tests incorrectly
expected admission; inspection confirmed the existing fully-bound-region
guard and the fixtures now verify rejection, without changing that guard.

Both previous completed Studio planting packages remain serveable from their
bound archives. The owned idle Studio listener is refreshed after terminal
workers/checks using process/socket evidence only. Live HTTP/browser behavior
and fresh GPU appearance remain unverified. Receipt:
`reports/native-frame-roll-validation-v1/verification.json`.

This development case does not stand in for broad action or rig coverage,
human stance labels, force/balance, semantic correctness or animator cleanup.
The full project goal and release requirements remain unchanged.
