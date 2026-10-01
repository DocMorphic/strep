# Finer temporal controls for guarded native contact fitting

The [supported dual-guard fit](dual-guarded-contact-v1.md) preserves sampled
contact and mesh separation without worsening absolute or reference-excess peaks,
but original motion limits still fail. Its largest acceleration excesses occur
near 1.591667 s, earlier than contact. Only one of 72 total coarse-control
components saturates its component bound, so increasing the bound alone is not
justified by this result.

## Matched refinement

Bisect all four existing temporal control intervals. Each arm joint now has
seven interior rotation-vector knots plus its retained contact angular step,
for 72 controls per actor instead of 36. This gives localized timing freedom
throughout the edit window rather than adding a hand-selected knot at one failing
sample. The source's native output key clocks and fractional contact are unchanged.

The refined space contains the complete old control space: interpolate the old
knot vectors onto the new knots and copy the contact step. Tests verify identical
sampled poses for the lifted controls in both double precision and float32, with
no increase in component magnitudes. Additional tests check retained contact,
actual export/decoder agreement, immutable keys, zero controls, local support and
the structural rate-dependency masks.

The experiment starts from `contact-rate-path-v1`, the same input as the prior
coarse dual-guard fit. It retains the original pose/rate references, all 53 mesh
audit times, 0.45 mm auxiliary hand-plane clearance, both peak guards, their
numerical tolerances and structural proposal masks. The 120-iteration limit and
0.15 radian component bounds are unchanged. More controls increase the number of
function evaluations and may change wall time; this is not an equal-compute claim.
The peak ceilings remain those of the matched starting clips, not the later
coarse fitted result. Comparisons against that later result must be reported
separately rather than implied by a guard pass.

```powershell
.venv/Scripts/python.exe scripts/study_refined_guard_contact.py reports/contact-rate-path-v1 reports/<fresh-refined-fit>
```

The local evidence chain and separately acquired character are required. Prior
raw results stay immutable. The completed fit and independent diagnoses are summarized below. No new model training, Studio promotion, held-out
use, or release-quality claim follows from temporal refinement.


## Results

Both actors reach the 120-iteration limit; convergence is not claimed. Actor A
accepts half its final proposal and actor B the full proposal. Objectives fall
from 0.08155325 to 0.02950258 (63.8241%) and from 0.07761605 to 0.00679396
(91.2467%). All 53 sampled inter-actor mesh checks pass with zero crossings and
vertex depth. The contact gap is 1.00004444 mm. Original edit budgets, clocks,
untouched channels, protected poses and both source-anchored peak guards pass.

All four original motion-limit groups still fail, although counts and maximum
excesses improve versus the coarse fitted result:

| Rate group | Coarse failing rows | Refined failing rows | Coarse maximum excess | Refined maximum excess |
| --- | ---: | ---: | ---: | ---: |
| Position speed | 143 | 113 | 0.416848 m/s | 0.192642 m/s |
| Position acceleration | 294 | 250 | 63.870684 m/sÂ² | 39.215081 m/sÂ² |
| Angular speed | 1,330 | 1,002 | 2.206541 rad/s | 1.366928 rad/s |
| Angular acceleration | 222 | 130 | 229.019441 rad/sÂ² | 140.645985 rad/sÂ² |

An independent comparison against the matched starting clips finds no absolute
peak regressions. Against the later coarse fit, actor A has none; actor B has
two angular-acceleration increases: 6.475241 rad/sÂ² at LeftArm and 0.00005503
rad/sÂ² at LeftHandIndex3. Thus source-guard success is not universal dominance
over the coarse alternative. The optional `--baseline` comparison binds both
completed studies and rejects mismatched starting sources or audit clocks.

Contact-marker velocity jumps fall from the coarse fit's 0.333194/0.426167 m/s
to 0.295204/0.274806 m/s. Large approach acceleration errors remain near
1.591667 s. Sampled floor penetration remains 6.003415 mm. The 0.45 mm auxiliary
planes pass on the selected pair; the stricter 0.5 mm comparison fails.

## Full-proposal geometry diagnostic

Exact proposal replay identifies actor A's full-step rejection as an auxiliary
hand-plane miss of 20.101389 micrometres. Both actors' full steps pass their
source-anchored rate-peak guards and original joint budgets. A separate export
replays these saved controls without optimization or acceptance, retaining the
failed plane test in its result.

All 53 full-proposal mesh samples also pass, with a 1.00002634 mm contact gap.
This shows that a failed conservative plane guide does not establish a sampled
mesh collision. It does not establish continuous collision freedom, relax the
plane comparison, or promote this diagnostic candidate.

The full pair's original-limit failures are 124 / 292 / 975 / 144 rows for
position speed / position acceleration / angular speed / angular acceleration.
Maximum excesses are 0.191452 m/s, 25.281921 m/sÂ², 1.366928 rad/s and
138.945515 rad/sÂ². Some counts increase versus the selected pair despite lower
worst acceleration errors. Keep these alternatives and their tradeoffs visible.

Next preserve intermediate optimizer controls and check their actual serialized
feasibility rather than selecting only from the final proposal's backoffs. Earlier
scores suggest potentially useful iterates, but their feasibility was not verified
and their controls were not saved in this study. Use direct mesh evidence to
investigate surrogate failures without silently changing declared comparisons.

```powershell
.venv/Scripts/python.exe scripts/diagnose_native_absolute_rates.py reports/refined-guard-contact-v1 reports/<fresh-vs-coarse> --baseline reports/supported-guard-contact-v1
.venv/Scripts/python.exe scripts/replay_full_refined_contact.py reports/refined-guard-contact-v1 reports/<fresh-full-replay>
```

## Verification and evidence

All 1,086 model-free Python source tests pass. Initial independent diagnostic
processes stopped before writing completion records; their partial v1 outputs
remain untouched. The fresh v2 diagnostics completed and reproduce the selected
rates and saved proposal scores. A deduplicated rehash of 5,471 bound files finds
no mismatches. No heavy fitting worker remains active.

The local comparison at `reports/refined-contact-review-v2/viewer.html` includes
starting, coarse, selected refined and full diagnostic clips. Diagnostic labels
and failed auxiliary-plane checks are shown explicitly. All eight copied GLBs
pass offline format/loader checks with zero errors or warnings; the diagnostic
label and failed-plane note are verified in the generated manifest. Browser rendering,
engine playback and human quality remain unverified for these exports. No new
training or reserved held-out evaluation occurred; nothing is promoted to Studio.

| Study | Result SHA-256 |
| --- | --- |
| Refined fit | `242d44fb1d13e1a019d01c161e5b420d6b3aaf2f62baf755c7a9a01bded8cd90` |
| Absolute rates vs starting clips, v2 | `5fb2ba7f1b6e3dcd3412a25d78f6eb9a5402e61e49db6a3b0a937f61190feef2` |
| Absolute rates vs coarse fit, v2 | `9a339fc8d45fa3f017db2f229933d82314fbd382c0112832bf57e67e60a4631a` |
| Turnaround diagnosis, v2 | `e62a5209e5ffdd9187269ae090f201966e1a391f5e6bb162679b9d9ef9564286` |
| Proposal replay, v2 | `4ec7cbd9fce5918dcd5d291fddc48ae55a0758b865b7e78082f952d8dc08832c` |
| Full-proposal mesh diagnostic | `779aeae5a4796a82c4c99372e068630b9e5727c35a5d9f15a0a3af2239e296d2` |
