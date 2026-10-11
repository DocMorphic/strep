# Captured reference motion on a supplied character

Completed 2026-10-11. The [captured reference intake](cmu-ground-reference-v1.md)
now has a direct, model-free transfer path to a supplied rigged GLB. It does
not require converting the motion to SOMA, loading a generation model or
inventing contact annotations. It remains a development transfer baseline,
not a cleaned animation or training target.

[Source profiles](../scripts/acclaim_rig_transfer.py) bind the ASF checksum,
zero-channel reference convention and all 19 anatomical roles. Each role names
its position segment and orientation segment separately. The two explicit CMU
development mappings anchor hands at `lwrist`/`rwrist` while taking orientation
from `lhand`/`rhand`, composing wrist twist and hand articulation without selecting
uncaptured finger/thumb channels. Source ancestry, distinct roles and orientation
ancestry are checked. These choices require anatomical review; role names alone
do not establish capture validity.

Target profiles retain the existing default-node calibration and bone
translations. Root movement scales with mean leg lengths, with explicit world
offsets. There is no automatic floor lift, positional IK, contact correction,
filtering or downsampling. The derived GLB appends an animation while retaining
original animation metadata, accessors, buffer views, payload bytes, materials
and equivalent default transforms. Original files remain unchanged. Every
capture key survives; exact source times and glTF float32 encoded times are
stored separately. Empty contact intervals mean **unknown contact evidence**.

The [frozen transfer protocol](../benchmarks/cmu-ground-transfer-v1.json) uses
the unchanged Kenney rig/profile, both complete CMU clips and the existing
5-mm floor tolerance. All **65 focused tests pass**, including 18 new transfer
checks and 47 importer checks. Synthetic assets exercise genuine export,
source/target checksum admission, ancestry, independent hand orientation,
clock/frame preservation, existing animations and retained terminal failures.

| Captured clip | Original keys | Floor failures | Worst native-key depth | Leg scale |
|---|---:|---:|---:|---:|
| Crawl 111/03 | 1,524 | 1,480 | 0.649773 m | 1.490427 |
| Get-up 140/08 | 898 | 446 | 0.367568 m | 1.464339 |

Both clips fail the full native-key floor condition. The worst scaled-source
head-position errors are 0.695261 m and 0.732011 m; worst hand errors are
0.772621 m and 0.732370 m. These are correspondence diagnostics, not anatomical
quality thresholds. They include fixed target proportions and reference/mapping
choices; the results do not isolate a causal explanation. No captured pose or
derived clip is promoted as a clean target.

GLB roundtrip maximum vertex error is at most `3.034e-7 m`. Separate Rodrigues
and SVD calibration, root/role-position reconstruction and alternate CPU skinning
check all **2,422 keys × 1,029 vertices = 2,492,238 vertex positions**. Maximum
floor difference is `2e-15 m`, rotation-matrix difference `1.985e-7`, root
difference `1.191e-7 m`, and role-error difference `1.777e-15 m`. Every floor
classification agrees. Clock quantization is at most `4.451e-7 s`. The replay
shares source parsing/FK and target asset reading/sampling; it provides separate
calibration and skin arithmetic, not independent capture semantics or continuous
geometry proof.

Source checks finish in 4.078 seconds at 191,037,440-byte peak RSS, with 22
resource observations replayed. The complete two-clip transfer/replay finishes
in 16.265 seconds at 128,339,968-byte peak RSS, with 34 observations replayed.
All inputs, method snapshots, raw references and failures remain local and bound
by hashes. Generated GLBs and dataset payloads are absent from the public repo.

The [CMU rights and attribution record](cmu-ground-reference-v1.md) still
applies; training admission remains false. No source skin, verified supports,
between-key collision checks, mechanics, engine import or human review is
supplied here. Next work is explicit positional fitting and authored support
targets on the target rig, followed by complete mesh/contact verification. A
reference transfer passing export checks does not establish that those targets
are feasible. All release requirements remain unchanged.

On a provisioned workspace, explicit source and target profiles can be used:

```powershell
.venv\Scripts\python.exe scripts/acclaim_rig_transfer.py --asf reports/cmu-ground-reference-v1/111.asf --amc reports/cmu-ground-reference-v1/111_03.amc --source-profile reports/cmu-ground-transfer-v1/crawl-111-03-source-profile.json --character reports/kenney-static-rig-adaptation-v1/character.glb --target-profile reports/kenney-development-transfer-v3/profile.json --fps 120 --length-convention cmu-inches --output reports/cmu-crawl-transfer-new
```

The output folder must be fresh. This CLI does not acquire assets, train a model
or add a Studio upload UI.
