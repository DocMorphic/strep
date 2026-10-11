# Continue from corrected native keys without rebasing the source

`native_storage_continuation.py` binds an intended control vector, its explicit
one-neighbor corrections and every edited actor's exact saved asset. It provides
a corrected start for `SceneProblem` while retaining the original scene and
edit reference. Source-rate caps therefore come from the original motion.
Loading this state checks payload identity; it does not declare a feasible
native/contact start or approve geometry. The optimizer still checks those.

`state_for` checks the corrected payload against the original authoring bounds,
then records the original authoring digest, source asset bindings, storage policy
digest, controls, corrections and selected animation indices. Source and saved
asset changes during binding are rejected. `StorageContinuationEdits` validates
the complete actor population and reproduces the corrected keys. Its initial
controls differ from the original zero controls, but the original scene,
source worlds, cap arrays, control boxes, windows and frozen keys remain.

The discrete corrections remain explicit on every proposed export and separate
from the intended unrounded curve. `check_continuation` detects changes to the
state, initial controls, policy, corrections, original authoring or bound files.
Call it before and after a numerical job. Every proposal still needs fresh
decoding and complete original motion/contact and geometry checks.

The 85 affected checks pass, then the complete 23-case continuation suite passes
after adding two binding-race checks: **87 distinct affected checks**. Cases
cover exact re-export, corrected world samples, unchanged original caps/worlds,
bad/partial state, changed index/hash, modified state or files, original proposal
bounds and files changing during payload audit. All 47 and 28 recorded resource
observations replay. The full source inventory adds this module: 468 Python
modules and 42 Node suites, without a new full-inventory pass claim.

The [completed development surface trial](kenney-kick-stored-surface-v1.md)
starts from the separately replayed native correction, preserving the original
72-control/cap epoch and complete 2,017-time floor population. It accepts an
export at fraction 1/256, but improves the peak by only 0.014255 mm and still
fails floor geometry. Fresh stored/unrounded screening distinguishes seven
storage-only rejections from the full fraction's two continuous failures.
The largest continuous-feasible proposal now also has a separately repaired
and freshly replayed native export, but its 47.600935-mm floor peak still fails.
No floor, engine, realism or release approval follows.

The [focused Windows/Linux workflow at `8d07889`](https://github.com/DocMorphic/strep/actions/runs/38183110085)
passes all six jobs: **712 Python checks per OS** (645 contact/rig, 35 lineage,
32 game packages), 23 subtests and the offline editor. The full source workflow
at that revision remains in progress; the latest complete full-inventory result
remains the earlier 466-module/42-Node run.
