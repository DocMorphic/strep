# Support articulation and bounded planting convergence

Protected animated toe joints influence the fixed contact patches in all
36 support intervals of the existing 18-clip development population. A matched
run/roll/stand search with sixteen iterations also improves on eight iterations,
but still fails the original native motion/contact and imported contact checks.
The input remains selected. These observations motivate an explicit toe-edit
experiment; neither establishes that frozen toes cause the failures.

## Read-only articulation report

`scripts/native_support_articulation.py` accepts a source GLB and its existing
source-bound native support draft. It reports each foot's descendant nodes,
original leg-only edit permissions, fixed patch vertex identities, positive
skin weights, and source-local rotation tracks. These are the existing
`RigAsset` loader's validated, normalized native weights, not the stored
accessor payload. Repeated influence slots are summed by node without further
normalization or dropping influences. The fully foot-bound
region guard remains in force; a dominant foot influence does not admit an
otherwise unsupported mixed sole.

Local rotation evidence includes sampled angle from the exact authored stance
start and maximum speed on adjacent original native intervals overlapping the
stance. Authored endpoints retain their float64 values while the sampler uses
the stored native clock. Near-coincident boundaries are never differentiated
as a merged velocity clock. Shorter tracks retain source endpoint clamping;
single-key rotation channels report constant motion with no speed intervals.
An unanimated descendant reports no rotation channel, rather than a fabricated
track. These are local track measurements, not world-motion or acceleration
limits, force/balance evidence, or a continuous-motion certificate.

The report archives implementation bytes and binds source/draft hashes and
runtime versions. Reusing an output directory or changing inputs/methods
rejects success. It generates no corrected clip and changes no permissions,
selection, quality approval, training admission, or release approval.

```powershell
.venv/Scripts/python.exe scripts/native_support_articulation.py source.glb support-draft.json reports/fresh-articulation
```

The corrected development population is saved locally under
`reports/native-support-articulation-breadth-v3/`. It reuses six actions on
CesiumMan and female/male Quaternius assets from the earlier contact study.
All 18 source clips and 36 authored intervals have protected animated foot
descendants with positive fixed-patch weights. This is inspection of existing
development clips, not new generated motion, independent held-out breadth,
engine observations, or approval of those stance labels.

In the female run/roll/stand case, the left patch's protected toe weights are
approximately 0.428/0.962/0.972 and the right patch's are 0.962/1.000/0.972.
Sampled toe-local angles from stance start reach about 0.22 and 0.38 degrees.
The leaf nodes responsible for earlier world acceleration excesses have no
direct patch weights and no local rotation channels. Their world motion still
depends on their ancestors. Weight, a moving ancestor, and a failing rate row
are distinct observations; they do not establish causation or authorize edits.

## Same search with a larger bounded budget

`reports/native-frame-budget-v2/` retains the same female source, initial raw
warm seed, draft, source caps, four source bins, 0.001 radian trust radius,
all twelve frame clocks and separate 4.99 mm/s proposal target. Public limits
remain 1 mm anchor error and 5 mm/s speed. Root/all translations, unrelated
rotations, native clocks, frozen keys and edit/angle/displacement bounds stay
protected. Exterior ramps remain disabled.

The completed historical eight-iteration run is compared with sixteen
iterations from the same initial seed. All first 24 raw/shadow probe pairs,
their exact bytes and merits, and the first eight complete iteration histories
reproduce exactly. Computational methods are unchanged; the current job
differs only by the previously documented archive-closure fix. Executed
historical archives remain separate and this difference is verified
structurally. The longer run tests convergence rather than repeating a
completed experiment merely to publish it.

| Budget | Native left/right anchor (mm) | Native left/right speed (mm/s) | Original failed rate rows: speed/acceleration/angular speed/angular acceleration | Worst imported frame speed (mm/s) |
| --- | --- | --- | --- | --- |
| 8 iterations, historical | 1.354312 / 1.484648 | 7.385402 / 9.625968 | 24 / 23 / 4 / 14 | 9.780831 |
| 16 iterations | 1.141046 / 1.211663 | 6.105352 / 8.142963 | 28 / 21 / 4 / 9 | 8.206508 |

The maximum normalized raw/shadow deficit decreases from 1.1946778795 to
0.8073194880, but remains positive. Support/edit bounds and authored clearance
pass; native contact and original source rates fail. The speed-row failure
count increases even as the worst normalized deficit decreases. Reduced error
is not acceptance, general convergence, infeasibility evidence, or animator
quality improvement.

Actual headless Godot import adds 612 source/proposal pose observations across
two scenes with 65 bones and three surfaces. Repeated source poses are not new
held-out coverage. The proposal's worst left/right game-frame speeds are
6.232815/8.206508 mm/s; all twelve speed clocks fail for both feet. Imported
left/right anchors are 0.990773/1.211641 mm. Maximum engine/native position
differences remain below 0.177 mm. The imported left anchor passes while its
native anchor fails, illustrating why combined independent checks remain
necessary. Every original selection stays the exact input GLB.

A preliminary attempt stopped at preflight because it required identical
historical job bytes despite the archive-only fix. No fitting/import started
there; its failure is preserved under `reports/native-frame-budget-v1/`.
The corrected study uses a fresh directory and verifies both the allowed
archive-only difference and actual first-eight-iteration reproduction.

## Validation and next work

Seventeen new model-free fixtures cover analytic local SLERP, exact authored
endpoints, separate speed clocks, shorter/single-key/static tracks, repeated
and zero-weight slots, explicitly identified loader normalization, fully-bound region rejection, source/draft/method
binding, immutable inputs and directory reuse. All 68 focused support/skin/
contact/report checks pass on the final source. Both model-free CI platforms
include the new tests. The preceding public commit's four hosted CI jobs also
completed successfully; new-commit CI is reported separately after pushing.

An early fixture caught endpoint downcasting in `np.r_`; explicit float64
endpoint arrays fix it. Earlier inspection outputs remain separate, and the
corrected final population binds current methods. Verification receipt:
`reports/native-support-articulation-validation-v2/verification.json`.

The next correction experiment should require a separately source/draft-bound
declaration of additional rotation nodes and cumulative angle limits. It must
preserve original source-rate caps, root/translation tracks, frozen clocks/keys,
skin payloads and independent raw/shadow/engine checks, and must not masquerade
as an old leg-only contract pass. Broader phase/body, scene and partner contacts,
action/style/rig validation, human cleanup and measured learning remain open.
No live browser/HTTP, fresh GPU appearance, target-rig SOMA NPZ conversion,
human realism, training admission or model-quality improvement is claimed.
All release gates and the formal 72×5 population remain unchanged; the full
project goal stays active.
