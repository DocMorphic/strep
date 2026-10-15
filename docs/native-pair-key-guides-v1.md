# Joint native-key approach fitting

`scripts/native_pair_key_guides.py` connects two original-bound
`KeyIntervalModel` instances to one conic proposal. It fits their existing
native animation keys and one shared offset per explicitly supplied regional
separation guide. It applies to a declared two-actor scene, rather than an
action-name whitelist. It does not approve a collision, contact or animation.

Each actor retains every original rotation and complete-clock joint displacement
row and every original linear/angular speed and acceleration row. These form
the **hard prefix** of the local conic model, with original caps, scales and
tolerance unchanged. A bad previously corrected curve cannot become the new
source epoch: both interval seeds must be zero relative to the original assets.
The two models must bind the same source scene, policy and complete sample clock.

Contact points are rebuilt using **both edited actors**. World targets and
object-local targets retain their declared meanings; hold-contact speeds use
the original authored frame populations. This avoids fitting each actor against
the other actor's old pose. All source floor minima are measured on the complete
declared geometry clock. The local model protects original contacts and complete
floor observations against worsening, including sources that already fail.
This protection is a proposal bound: original authored contact/floor acceptance
remains unchanged, and a protected existing failure still fails the release.
A passing condition may move within its original bound; a positive violation
may not increase. This is protection against condition regression, rather than
requiring every already acceptable contact error or floor gap to stay identical.

Each guide declares its two actor regions, existing clock time, unit world axis,
midpoint, permitted offset shift, clearance and reserve. Every supplied vertex
participates. A common plane offset lets the two actors share the correction.
The region and axis are explicit geometric inputs; there is no anatomical or
continuous collision certificate. Malformed, missing, duplicate or out-of-range
populations are rejected. A finite Jacobian budget rejects the complete model
if exceeded; it never discards small entries or sampled conditions to fit.

Linearization anchors native/contact vectors and complete floor minima to the
provided decoded observations. Differences use the matching continuous native
curve, retaining the actual finite step per column. Floor witness gradients and
region halfspaces use the existing exact affine halfspace-to-norm conversion
inside the declared trust box. Complete nonlinear floor minima, actual contact
errors and serialized animation still need independent checking after a step.

## Evidence

The affected local selection passes **48 checks in 120.07 s**, covering the new
joint model, existing interval rows and native pair surface/conic helpers. The
new module contributes **17 cases**, including:

- Equal edits on both real affine-skinned actors retain zero relative contact
  error; fixing one partner at its source pose produces a nonzero error.
- Every original native row/cap/scale appears unchanged in the joint model.
  The complete native population is hard, and both actor control blocks reach
  the same contact rows in the sparse derivative.
- A shared plane shift changes the two region gaps with opposite signs.
- Independently exported and decoded actor clips feed the same full native and
  coupled-contact model, retaining their original caps.
- Invalid axes, actors, times, regions and settings reject, as do changed source
  rate caps, incomplete worlds and a Jacobian budget that cannot hold all entries.

The 512 MiB CPU test guard completes in **137.000 s**, peak sampled process-tree
RSS **143,200,256 bytes**, with all **136** resource observations replayed and
an additional 600 MiB free floor. Local records remain under ignored
`reports/native-pair-key-guides-tests-v2`. An earlier launcher names a nonexistent
test file and exits with pytest code 4 before collecting any tests; its failed
17.172-second guard and all 19 resource observations remain preserved separately
under `reports/native-pair-key-guides-tests-v1`. It is not a production or test
assertion failure and is not counted among the passing checks.

The source inventories now declare **520 Python test modules / 45 Node suites**;
contact/rig contains **84 Python modules / five Node suites**. This focused
selection does not establish a full-inventory or release pass.

The [focused hosted run](https://github.com/DocMorphic/strep/actions/runs/38715030869)
at `f0b028e` passes all **17 new cases on each OS**: Ubuntu **4.01 s**,
Windows **12.62 s**. This is distinct from the 48-case local affected selection.
After the diagnostic-message change, the [same focused selection](https://github.com/DocMorphic/strep/actions/runs/38715909389)
passes all 17 cases per OS at `5a76b6f`: Ubuntu **3.24 s**, Windows **10.40 s**.

## Actual motion study

The real source-native high-five trial under ignored
`reports/high-five-joint-native-approach-v1` starts from the original zero controls,
uses existing keys 30–48 for both actors, and retains the five previously declared
region axes at keys 34–38. It attempts one joint temporal conic step with every
original native row hard, followed by actual native exports and up to four
explicit backoff probes. Complete decoded motion, contact and floor checks
decide whether a proposal anchor can be retained; the original motion remains
selected for the project.

The initial 3,000,000-nonzero Jacobian budget stops the actual study before a
solver result or decoded proposal. It does not truncate any derivative or motion
population. The guard records **376.281 s**, peak sampled tree RSS **611,860,480
bytes**, with all **372** resource observations replayed. This is a declared
matrix-entry budget failure, not a RAM guard stop or a motion-feasibility result.
Its original source observations and failure remain intact. The actual model
contains **461 controls**, **619,662 hard original native rows** and **32,250
regional guide rows**, alongside coupled contacts and complete floor protection.

A fresh study under ignored `reports/high-five-joint-native-approach-v2` raises
only the sparse-entry budget to 6,000,000, with the **same 1 GiB RAM guard**, free
floor, time population, controls and motion/contact/geometry conditions. Doubling
the stored-entry allowance adds at most 48 MB of raw Float64/Int64 entry chunks,
before sparse assembly/solver overhead; this is an estimate, and the unchanged
RAM guard remains authoritative. The helper's failure message now reports the
actual count, column and limit; its mathematical operations are unchanged.
This continuation completes. Its full matrix has **3,011,949 nonzero entries**,
and its 655,949 norm rows include a **623,699-row hard prefix**: all 619,662
original native rows, three protected contacts and 4,034 complete floor rows.
The primary conic phase reports `Solved` after 68 iterations. The optional
minimum-control-norm phase reports `NumericalError`, including its retry; it is
not selected. The saved primary direction is used without claiming a successful
minimum-norm refinement.

The first actual two-clip export fails **11 native rows** and is rejected. The
half-size step passes **all 619,662 independently decoded native rows**, preserves
the original contact violations and complete floor conditions against regression,
and improves the region-guide objective. Worst guide deficit changes from
**38.882262 mm to 35.150691 mm**; squared guide deficits change from
3.520895112425822 to 1.4959131857254169 in the saved row units. This selects a
native-feasible experimental anchor, not a complete scene or project animation.

All five complete-mesh diagnostic times still fail pair geometry:

| Native time (s) | Surface outcomes | A inside B maximum | B inside A maximum |
| --- | ---: | ---: | ---: |
| 1.1333333253860474 | 201 | 5.686425 mm | 13.357914 mm |
| 1.1666666269302368 | 310 | 10.336497 mm | 20.334709 mm |
| 1.2000000476837158 | 162 | 19.992752 mm | 28.290856 mm |
| 1.2333333492279053 | 216 | 15.673294 mm | 32.433906 mm |
| 1.2666666507720947 | 136 | 18.224251 mm | 32.530843 mm |

This is not the complete geometry clock and does not establish overall geometry
improvement. Original meeting contacts and floor conditions remain failed. The
guard completes in **577.282 s**, peak sampled tree RSS **856,281,088 bytes**,
with all **569** resource observations replayed under the unchanged 1 GiB CPU
profile and additional 600 MiB free floor. Original files, both serialized probes,
full original norms, matrix, solver outcomes and geometry diagnostics remain
preserved. No clip is adopted and the original remains selected.

The 1 GiB CPU estimate covers two simultaneous
interval models and the complete sparse populations, based on twice the earlier
346,353,664-byte moving-guide peak plus a 128 MiB allowance. The additional
600 MiB free floor stays in force; engine/model admission is unchanged. No model
or engine is run again. The [complete original baseline](native-scene-engine-completion-v1.md)
and [failed prior corrections](moving-region-contact-guidance-v1.md) remain
separate. Floor/support correction, meeting contact, full geometry, engine
comparison, broader motions/rigs/styles and human/cleanup evidence remain
required for the whole-project goal.

## Independent native and floor replay

The selected half-step is checked again in a fresh process without calling
`PairKeyGuides` or `KeyIntervalModel`. A scalar native decoder reconstructs the
complete original/candidate worlds; direct quaternion differences and joint
displacements plus the existing independent motion-measure interface rebuild
all original magnitudes and caps. Every native bound passes, with source
caps/scales exactly reproduced. Maximum absolute magnitude discrepancies are
**3.4933e-16 / 2.8319e-16** for A/B in their respective row units. Maximum joint
displacements are **22.068546 / 17.236755 mm**, below the original 50-mm limit.

Every original and candidate vertex is skinned per frame through `RigAsset` on
all 2,017 declared times to recheck full floor minima. Maximum differences from
the saved floor observations are **3.2960e-17 / 3.4694e-17 m**. Both actors still
fail all 2,017 original floor checks, with no condition regression. Roots and
clip endpoints match exactly. Source mesh/skin/node data, the original animation
records and the original binary payload prefix are preserved. A standalone
scene-contact evaluator reproduces exactly unchanged, still-failed contact
arrays. These are fresh native checks, not an engine execution or a fresh pair
geometry query.

This replay completes in **163.687 s** under a 512 MiB CPU guard, peak sampled
tree RSS **243,642,368 bytes**, with all **163** resource observations replayed
and the additional 600 MiB free floor. Records remain under ignored
`reports/high-five-joint-native-replay-v1`. Fidelity, native feasibility and a
smaller guide deficit do not approve the still-failed interaction.

## Matched geometry counterexample

A read-only comparison binds the earlier retained original pose at
1.2333333492279053 s to exactly matching current source world matrices, unchanged
source inputs and unchanged registered geometry methods. It reuses the saved
original/proposal measurements rather than querying either pair again. Recorded
surface outcomes decrease from **222 to 216**, and A-inside-B maximum depth
decreases from **18.499823 to 15.673294 mm**. However, B-inside-A maximum depth
**increases from 32.087589 to 32.433906 mm**, a **0.346316-mm regression** in that
recorded measure. A smaller convex-region guide deficit therefore does not
establish better complete-mesh geometry.

This comparison is bound under ignored
`reports/high-five-joint-guide-counterexample-v1`; its guard completes in
**18.282 s**, peak sampled tree RSS **112,734,208 bytes**, with all **20** resource
observations replayed. It is a comparison
of saved floating-point measurements, not a fresh fallback-RNG reproducibility,
continuous collision or physical-quality proof. See the [journal caveat](native-geometry-journal-v1.md).
The next fitting step needs local collision-surface constraints alongside the
now-verified hard native motion model, rather than treating region-plane merit
as the final geometry objective. Full floor/support, meeting and whole-clock
geometry/engine/human requirements remain unchanged.
