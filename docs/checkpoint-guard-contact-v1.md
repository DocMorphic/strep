# Selecting serialized feasible contact checkpoints

The [refined contact fit](refined-guard-contact-v1.md) reduced motion errors, but
actor A retained only half of its final proposal. Earlier solver scores were
promising; their controls were not recorded, so their actual float32 feasibility
could not be tested later.

This matched study retains the same 72 controls, 120 solver iterations, starting
clips, original references, component bounds and actual contact/peak/plane limits.
Every callback saves its control vector. All nine dyadic backoffs from full
strength to 1/256 are evaluated after native float32 serialization. The lowest
objective among actually feasible candidates is retained across callbacks and
the final proposal, including when the solver itself fails to converge.

Every backoff is evaluated even when a full step is feasible: nonlinear motion
can make a smaller step better. Ties keep the first candidate. Nonfinite
measurements and controls outside the original component bounds are rejected.
Source retention remains the fallback when no serialized feasible improvement
exists. Checkpoint JSON is written through the existing atomic save operation.
This is candidate selection, not a relaxation of any acceptance test.

The selection cost excludes the solver's control regularizer, as in previous
studies. Original cap failures and human usability remain separate from peak
non-regression. Full-mesh audits run on the selected pair after export; selection
is not a continuous-collision or motion-quality certificate. All callback
records, attempted fractions and final proposals remain available for replay.
The added evaluations cost time; the same iteration budget is not an equal-compute
comparison.

```powershell
.venv/Scripts/python.exe scripts/study_checkpoint_guard_contact.py reports/contact-rate-path-v1 reports/<fresh-checkpoint-fit>
```

The local source chain and separately acquired character are required. Earlier
studies remain immutable. Focused tests cover intermediate retention, nonlinear
backoff selection, unchanged feasibility limits, contact drift, ties, immutable
input arrays and invalid data. Completed results and independent checks follow below. No new training, held-out use or Studio selection is
implied.


## Matched results

Both optimizers reach their 120-iteration limit. Their score histories and final
control vectors are identical to the previous refined run. Candidate selection
alone changes actor A's retained export: full strength at iteration 81 replaces
half strength at the final proposal. Actor B retains the final proposal, first
recorded at iteration 119; ties preserve that earlier label.

Actor A's selected objective falls from the previous 0.02950258 to 0.00669443,
a 77.3090% reduction. Relative to the matched starting clips, reductions are
91.7913% and 91.2467%. Each actor records 121 proposals and nine backoffs each,
including the final proposal. Cache reuse avoids recomputing identical controls.
The independent replay verifies selected controls against their recorded proposal
and fraction, reproduces selected scores/margins, checks every recorded feasibility
flag, and confirms the minimum feasible recorded score within 1e-10.

All 53 sampled inter-actor mesh checks pass with zero crossings and vertex depth.
Both source-anchored peak guards, original native joint budgets, clocks,
untouched channels, protected poses and 0.45 mm auxiliary hand planes pass.
The stricter 0.5 mm plane comparison fails. Contact-marker velocity jumps are
0.252647 / 0.274806 m/s. Sampled floor penetration remains 6.003415 mm.

All four original motion-limit groups still fail:

| Rate group | Previous selected rows | Checkpoint selected rows | Previous maximum excess | Checkpoint maximum excess |
| --- | ---: | ---: | ---: | ---: |
| Position speed | 113 | 129 | 0.192642 m/s | 0.191452 m/s |
| Position acceleration | 250 | 297 | 39.215081 m/s² | 25.282004 m/s² |
| Angular speed | 1,002 | 980 | 1.366928 rad/s | 1.366928 rad/s |
| Angular acceleration | 130 | 144 | 140.645985 rad/s² | 138.945515 rad/s² |

Source-anchored guard success is not dominance over an already improved
alternative. Against the previous selected pair, actor A has one absolute
position-acceleration regression (up to 0.840471 m/s² at LeftForeArm), one
angular-speed regression (0.013783 rad/s at LeftArm), and nine angular-acceleration
regressions (up to 24.222956 rad/s² at LeftHandIndex4). Actor B's motion is
unchanged. Retain both alternatives and their tradeoffs; a lower scalar objective
does not establish superior animator quality.

## Verification and next workflow work

All 1,091 model-free Python source tests pass. The local three-version comparison
at `reports/checkpoint-contact-review-v1/viewer.html` copies six native GLBs; all
pass offline format/loader checks with zero errors or warnings. Browser rendering,
engine playback, continuous collision freedom and human quality remain unverified.
All studies and check processes are terminal; prior raw results remain unchanged.

Next validate these native exports in Godot at their actual clocks, including the
fractional contact and guard times, then connect the candidate/review path to
Studio authoring. The existing engine runner accepts a manifest of fixed-rate
samples, while Studio's paired-fit pipeline expects its older prepared-request
schema. An explicit adapter is needed; this study cannot be adopted as an original
fixed-point fit because its authored palm-region condition and native export
representation differ. Keep failure reports and alternatives visible during
integration. No new training, held-out use or Studio promotion occurred.

| Study | Result SHA-256 |
| --- | --- |
| Checkpoint fit | `3872ee91a9a15ee2dc2a5753727865bc3dfa7731749a9c266a8fb7fc41efba17` |
| Absolute rates vs starting clips | `c4620efe405efa832d09848c851cd952908b2363b4eb3ab9761939189835f183` |
| Absolute rates vs previous selected pair | `2b6162cac2688def8bde9d87117e38337d1fda8d3f9206521194a08be169bfb7` |
| Checkpoint and proposal replay | `27b41b501a746ac2fcfe30bd7eb05e5412ee367817d2c893def743f0cfcdc5f7` |
| Turnaround diagnosis | `92198d39a129a57da6721f0d56a7545f5de8b6caaeee8480a2e2c1b15f033301` |
