# Sampled correction bounds between native keys

`CorrectionCurve` evaluates source-relative rotation edits at explicit times
between stored LINEAR quaternion keys. It preserves every supplied joint,
sample and neighboring-time comparison. The saved wave that passes native-key
correction speed but fails between keys now reproduces through this calculation.
This enables fitting against the sampled failure; it does not establish a
continuous-time speed bound or approve a motion.

## Calculation and limits

Provide the immutable reference quaternion tracks, their native clock and an
explicit increasing sample clock. Candidate tracks must retain the complete
key/joint shape. The helper follows the native scalar sampler's endpoint,
shortest-arc SLERP and small-angle interpolation rules, then computes
`reference(t).inverse() * candidate(t)`. It returns angular edit magnitudes,
neighboring correction speeds and squared limit rows for positive per-joint
angle and speed allowances. A nonnegative row passes that sampled constraint.

The helper never chooses looser limits, changes reference tracks, inserts or
removes keys, selects a subset of samples, or authorizes editable joints. Those
permissions, source-file hashes, export quantization and final geometry/engine
checks remain with the caller. Invalid geometry, clocks, limits or an exceeded
complete-array budget reject the request. Its declared workspace estimate
excludes caller-owned control Jacobians.

Closely spaced native/uniform sample times need care. Batch and scalar
interpolation can differ by roundoff, which very short time differences amplify
in the speed calculation. The helper retains those neighbors and uses the
authoritative scalar sampler at both ends of differences shorter than 10 us.
It also retains the already-normalized relative `Rotation` objects when forming
neighbor differences. Converting them back to quaternions and normalizing again
caused a measurable mismatch in the saved fixture; removing that extra operation
matches the existing audit arithmetic without relaxing a limit.

## Checks and saved-fixture qualification

The 23 new regression cases cover scalar interpolation/rate agreement, antipodal
keys, small angles, accepted key normalization drift, Float32 clock boundaries
and their immediate Float64 neighbors, immutable reference copies, every final
joint/neighbor, invalid inputs and budget failures. A synthetic noncommuting
rotation case passes its native-key speed allowance while failing between keys.
Together with the existing native-key map suite, 81 checks pass. The new suite
is registered in both full and focused source inventories; no new hosted CI
pass is claimed.

The retained [plane-guided wave](wave-hand-head-plane-v1.md) supplies 120 native
keys, three right-arm joints and all 439 dense audit times. Direct comparison
with its scalar exported-clip audit measures:

| Quantity | Maximum discrepancy |
| --- | --- |
| Sampled quaternion component | 2.221e-16 |
| Original-relative angle | 2.132e-14 degrees |
| Sampled correction speed | 3.025e-11 degrees/second |

The native-key peak remains 39.996054599 degrees/second, while the dense peak
remains 40.135596445 against the unchanged 40-degree/second allowance. Both
verdicts reproduce. The curve reports 172 scalar-fallback samples and an
estimated 1,754,880-byte workspace for this fixture.

The first qualification stops at its strict comparison assertion; a second
diagnostic run records a 9.595e-8-degree/second error across a roughly 16 ns
neighbor interval. The redundant rotation normalization explains this failure.
The third run qualifies after the arithmetic correction. All three runs and
their 55 resource observations are retained and their resource traces replay.
This is fixture qualification, not a claim about all rigs or arbitrarily short
time differences.

## Coupled repair experiment

`reports/wave-region-curve-v1/` retains a separately guarded experiment using
complete moving head/hand region objectives and floor rows at all 46 affected
geometry times. Each time has its own initially selected separating direction.
All 439 retained dense times enter original-relative angle and correction-speed
rows during fitting. The original five-degree residual, 25-degree total and
40-degree/second allowances remain unchanged; right-arm nodes 14–16 at keys
51–60 are the only editable channels/keys. The earlier failed proposal is an
initial search point, not a newly approved source or reset of edit allowances.

The experiment has started; its outcome and independent exported replay are
pending. No accepted repair, engine result, naturalness rating or release
approval follows from the completed helper qualification. The full project goal
continues to require diverse actions, rigs, objects, partners and human review.
