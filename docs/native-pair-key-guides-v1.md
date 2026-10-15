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

## Actual motion study

The real source-native high-five trial under ignored
`reports/high-five-joint-native-approach-v1` starts from the original zero controls,
uses existing keys 30–48 for both actors, and retains the five previously declared
region axes at keys 34–38. It attempts one joint temporal conic step with every
original native row hard, followed by actual native exports and up to four
explicit backoff probes. Complete decoded motion, contact and floor checks
decide whether a proposal anchor can be retained; the original motion remains
selected for the project.

This study is running; no solver, exported-motion or geometry success is inferred
until its authoritative result. Its 1 GiB CPU estimate covers two simultaneous
interval models and the complete sparse populations, based on twice the earlier
346,353,664-byte moving-guide peak plus a 128 MiB allowance. The additional
600 MiB free floor stays in force; engine/model admission is unchanged. No model
or engine is run again. The [complete original baseline](native-scene-engine-completion-v1.md)
and [failed prior corrections](moving-region-contact-guidance-v1.md) remain
separate. Floor/support correction, meeting contact, full geometry, engine
comparison, broader motions/rigs/styles and human/cleanup evidence remain
required for the whole-project goal.
