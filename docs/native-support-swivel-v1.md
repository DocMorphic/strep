# Bounded knee-plane support search

The experimental joint support/rate CLI now allows each editable native knee
plane to swivel around its hip-to-ankle axis. It retains the source foot's native
world orientation and tangent position. The ordinary Studio/default solver is
unchanged. This adds deterministic solver freedom, not a trained motion model.

The completed 320-evaluation study **fails** combined acceptance. All four
serialized proposals pass sampled foot-height checks, but all four fail the
unchanged source-relative rate limits and exhaust their search budgets. The
selected output remains the byte-identical input. Lower residuals and fewer
failed rows do not establish convergence, feasibility or realistic motion.

## Method and reproduction

`native_support_swivel.SupportSwivelProblem` extends the existing
[joint native support/rate search](native-support-joint-rates-v1.md). It adds
one swivel variable per interior native edit key, bounded to the smaller of
5 degrees and the authored local-angle limit. Frozen boundary swivels are zero.
The matched request has 178 bends and 178 swivels, or **356 variables**.

Rigid two-bone IK transports the source bend plane and then applies the signed
swivel about the target leg axis. A zero lift with nonzero swivel is still an
edit. Native translations, exact per-key segment lengths, quaternion signs,
unchanged channels and frozen poses retain the parent method's policies.
The sparse derivative graph includes both kinds of variables. The unchanged
least-squares residual includes rate, height, displacement and angle excess.

Every final proposal is serialized to float32 GLB and independently decoded.
The authoring bounds, native-clock preservation, outside-motion preservation,
sampled support heights and all four source-rate screens must pass for selection.
The source-rate tolerance remains **1e-5**. A proxy score never overrides a failed
serialized audit.

```powershell
.venv/Scripts/python.exe scripts/native_support_job.py source.glb draft.json `
  reports/fresh-swivel-support --joint-rates --joint-swivel --joint-evaluations 320
```

Swivel mode requires joint-rate mode. Description-only mode rejects fitting
options. Requests archive the extra implementation and record the 5-degree
search limit, input hashes and evaluation budget (1–2000 per trial).

## Completed development study

`reports/native-support-swivel-rates-v1` uses the same frozen
[Studio v2 request](studio-native-support-v1.md) as the preceding bend-only
studies: source SHA-256
`87c185ddf0dc50dec7e56bbc4c301f66896ed460a53c6c8eb6797ce5a89107c7`,
Y-up plane offset **-0.056 m**, stance **[1.6,2.4] s** for each foot, edit keys
**[15,105]**, 0.25 mm clearance, 5 mm maximum gap, 30 mm maximum ankle
displacement and 45-degree local rotation limits. This remains a different
authored condition from the earlier unreachable ground-zero request.

All four trials pass height screens at **142 stance samples per foot** and
retain native clocks, frozen/free motion, the root and other branches across
**701 audit times**. Each optimizer reaches 320 evaluations without convergence.

| Trial | Failed rows: speed / acceleration / angular speed / angular acceleration | Final proxy squared residual | Largest swivel (degrees) |
| --- | --- | --- | --- |
| 1 | 54 / 13 / 18 / 8 | 0.0003273973 | 0.178440 |
| 2 | 51 / 16 / 8 / 12 | 0.0000451792 | 0.187769 |
| 3 | 67 / 16 / 17 / 12 | 0.0006927081 | 0.159396 |
| 4 | 42 / 12 / 14 / 6 | 0.0002223747 | 0.147943 |

Compared with the matched 320-evaluation bend-only search, all trials have
fewer acceleration, angular-speed and angular-acceleration failures. Trials
1, 2 and 4 also have fewer speed failures; trial 3 has two more. These are
diagnostic comparisons on one request, not a general improvement claim.

The completed result SHA-256 is
`05fceccae905f0de63a4f286dc71ee23fd12d41fa6ab7a7c6e79c0d05e356990`.
All **47** bound/input/output/archive files rehash without mismatch. Failed
proposals, raw input, support samples, root/event tracks and method archives
remain local under ignored `reports/`.

A separate **2000-evaluation** four-trial study is still running at this
publication (`reports/native-support-swivel-rates-v2`, session 78635). Its
input and implementation hashes still match the frozen request. No completed
result or acceptance is claimed for that study; it must be inspected before
further edits to its imported implementation.

## Validation and remaining work

Ten new tests compare signed/inclined-plane swivels against the independent
exact solver, cover zero-lift edits and exact zero-swivel parent equivalence,
verify native foot orientation/tangent retention and frozen/free/root behavior,
compare the quantized proxy with an independently decoded export, check sparse
dependencies including disjoint intervals, and reject invalid swivel limits.
The full source suite passes **1,251 Python tests** and **14 JavaScript suites**;
the 22 focused swivel/parent tests also pass. Preceding public commit `acbb4f0`
passed hosted Windows and Linux checks.

Support heights use positively weighted foot-owned vertices. This does not
establish whole-sole planting, horizontal slip correction, balance, physics,
continuous collision safety or action quality. No new engine/GPU/browser render,
human review, cleanup-time evidence, training, held-out use or release approval
is claimed. All 14 release capabilities remain unapproved and the single
full-project goal remains active.
