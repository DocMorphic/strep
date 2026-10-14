# Coordinating translation axes across native keys

The retained crawl correction has a fully passing intended curve and sampled
floor audit, but its serialized animation still fails 31 original motion rows.
A complete local translation study repairs its worst acceleration row without
introducing a new failure. Four independently decoded proposals retain 30
failures, so the original clip remains selected.

## Proposal method

`scripts/native_translation_stencil.py` ranks every absolute negative neighbor,
nearest value and positive neighbor on all three translation axes across up to
three native keys. The largest complete population is `3^9 = 19,683` proposals.
It rejects an insufficient population budget before materializing alternatives;
it never silently truncates the population. The nearest values come from the
original intended curve rounded to Float32. Changes never accumulate neighbor
steps on an already adjusted value.

For three uniform acceleration samples, an ancestor translation moves a joint
origin affinely while the other tracks stay fixed. The helper uses native
interpolation weights and the observed parent's complete linear transform,
including its scale. This provides a cheap local ranking, rather than a motion
acceptance decision. The existing single, paired and triple searches and their
defaults are unchanged. No production fitting integration is claimed.

The matched development study uses Root translation at keys 94, 95 and 96 to
target RightArm positional acceleration at uniform frame 379. These are the
three native keys supporting samples at 3.158333, 3.166667 and 3.175 seconds.
All 19,683 local assignments are ranked. Only the first four receive full
exports and complete motion/floor checks.

## Retained results

| Measurement | Replayed seed | Four proposals |
| --- | ---: | ---: |
| Intended motion failures | 0 | 0 |
| Original native motion failures | 31 | 30 each |
| Newly failed native rows | — | 0 each |
| Worst normalized motion excess | 1.936282358e-5 | 1.090261849e-5 each |
| Failed sampled floor times | 0 / 2,017 | 0 / 2,017 each |
| Peak floor depth | 4.998959799 mm | 4.998959799 mm each |

Of the complete local population, 7,108 are predicted to pass the single target
row. This is not a count of feasible clips. The first proposal's target excess
is predicted as -9.621660606e-5 and independently decoded as -9.621660568e-5.
Its predicted joint positions differ from the batch preview by at most
4.441e-16 metres. Every exported proposal still fails the complete motion gate.

The authoring request, source asset, 63 control values, original rate caps,
native clocks, original one-neighbor/64-correction policy and 5-mm floor limit
remain fixed. Each full export checks all 107,895 original motion conditions,
original edit permissions and all 2,017 floor times against all 1,029 referenced
vertices. Raw proposals and failures are retained under ignored `reports/`.

The study completes in 60.875 seconds of execution with 78 recorded resource
observations. A separate fresh replay completes in 63.828 seconds with 81
observations. Both resource traces independently replay against the unchanged
2,776,629,248-byte admission requirement. The public helper exactly reproduces
all 19,683 saved proposal rows. Fresh export bytes, complete decoded worlds and
motion rows, control/clock arrays, original recomputed caps, typed continuations
and every floor observation reproduce for all four proposals.

The failed first test invocation is retained: collection stops because the new
test omitted the repository's scripts-path setup. The corrected invocation
passes all 163 related tests in 53.08 seconds, including twenty new population,
native interpolation, budget, input and isolation checks. Its 71 resource
observations independently replay. Both Windows/Linux focused workflows pass
for preceding source commit `c1c0bb9`; hosted checks for this new helper still
remain required.

## Limits and next work

Complete local proposal enumeration covers one translation support and one
acceleration row. The other 19,679 alternatives are not exported or audited as
complete clips. Fresh replay shares repository arithmetic. Sampled floor
checks do not establish continuous collision freedom, anatomical realism,
action correctness, engine playback or animator approval.

Next, use the coordinated support method to address the remaining export
failures, then exercise the correction pipeline across broader actions, rigs,
object and partner interactions. No checkpoint or training change, reserved
held-out evaluation, live rendering/engine run, human rating or cleanup-time
approval occurs in this study. All fourteen release capabilities remain
unapproved under the single whole-project goal.
