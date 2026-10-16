# Explicit Kimodo checkpoint qualification and matched development comparison

The historical default remains Kimodo-SOMA-RP-v1.1. A separately acquired v1.2
checkpoint is a new experimental condition; its outputs cannot replace or rename
historical results. Neither version is an object-aware or partner-aware model.

## Loading contract

`scripts/kimodo_versioned_checkpoint.py` accepts an externally pinned local
acquisition receipt. It verifies the complete ten-file population and each stored
file's length and SHA-256 before construction. It accepts the smooth-root SOMA
family only, with a fixed revision and an explicit local checkpoint directory.
An acquisition receipt is provenance, not a quality or release approval.

The unresolved configuration must equal the installed historical baseline
configuration, use the four qualified upstream constructors, and contain only
the two expected local checkpoint interpolations. It is checked before resolution
or construction. A changed architecture or license requires separate qualification.
The actual upstream Kimodo constructor is retained. The existing bounded CUDA
transport copies and verifies all tensors without dtype conversion; temporary
constructor hooks are restored. Default dtype/device, vendor code, registry
aliases and the installed default manifest are unchanged. The caller supplies
the text encoder, and both Hugging Face and Transformers must be offline.

The source-only suite has 22 tests covering receipt/file binding and executable
or incompatible configuration rejection. It needs no weights, Torch or GPU.
Those tests do not prove the behavior of an actual GPU constructor.

## Actual v1.2 load-only probe

The separately guarded probe completed on the laptop's 8 GiB RTX 3070 Ti.
Checkpoint revision: `0e3c89024d896064b6851201373f7834784a386b`.
Weights SHA-256:
`fdcef624140a12c0a4840192ce0b75cafb4e73228a893da3864b4a990d3e919e`.
Pinned local vendor commit: `58e781898b3d7e328a676a75d3e338c45dce3ad9`.

All 408 tensors transferred and all 283,281,777 learned parameters were finite
float32 values on CUDA. The model has 30 internal joints, 77 output joints and
30 Hz output. Construction took 7.399 s; peak CUDA tensor allocation was
1,205,333,504 bytes. That allocation is not total driver-reported GPU usage.
The probe independently checked restored constructor hooks, unchanged defaults
and unchanged registry values. Its encoder deliberately throws on use: this was
construction, not motion generation or a text-encoder qualification.

The guard completed in 51.875 s; all 53 recorded resource observations and its
terminal status were independently replayed. The policy used a 2 GiB worker
estimate/cap plus 600 MiB free-memory reserve and a 15 s stable admission window.
The binding receipt SHA-256 is
`61a36831612d523dff87e396bc10a4eed42e09cc14605e61ebd839406d647a16`.
Local artifacts: `reports/kimodo-v12-load-probe-v1/` (ignored).

## Matched generation protocol

Use all seven requests and both original seeds (11 and 22) from the published
`benchmarks/kimodo-version-comparison-v1/requests.json`, copied byte-for-byte
from `reports/action-coverage-v1/request.json`: jump/land, crawl, dance/turn, wave,
kick/recover, get-up and run/roll/stand. Generate all 14 clips per version in
separate sequential processes, preserving every raw output and failed attempt.
These are reused development prompts, not held-out evaluation.

Both versions use the same pinned cached conditioning, 100 diffusion steps,
separated CFG weights [2,2], one sample, multi-prompt mode, five transition
frames, 30 Hz output, and no postprocessing or added constraints. Reset the
random seed before each clip. Both use the unchanged upstream constructor and
the same bounded CUDA transport; v1.1 uses its established installed loader and
v1.2 uses the explicit local receipt loader. Preserve both loader identities.

The conditioning qualification remains experimental original BF16 base/FP32
adapters with disk offloading; full 8B resident equivalence is untested. Holding
those cached features fixed controls the version comparison; it does not remove
that qualification. The fixed historical vendor is also an explicit condition,
not a claim to have tested the publisher's newer full software stack.

Validate all motion arrays, frame counts and proper rotation matrices. Report
per-clip height-mask and predicted-contact foot-speed proxies and joint-floor
depth/integral, with paired differences. Missing contact observations remain
missing rather than zero. Joint-floor depth is not mesh penetration; predicted
contacts are not independent ground truth. Reduced movement or omitted actions
can improve these proxies, so they cannot decide action correctness or realism.
No automatic default promotion, retargeting, engine or release approval follows.

Local artifacts: `reports/kimodo-version-comparison-v1/` (ignored).
## Completed matched generation and analysis

Both guarded model workers completed all 14 clips: 28 new neural generations,
not training, postprocessing or renamed historical outputs. All arrays, frame
counts and proper rotations validate. All 14 regenerated v1.1 clips have exactly
equal arrays to their historical counterparts across every saved array. This
supports reproduction for these particular seeds/inputs, not general equivalence
of all possible model executions.

The results are mixed. Each value below is an unweighted mean across clips;
the final column counts strictly lower values among the fourteen paired clips.

| Raw skeleton proxy | v1.1 | v1.2 | v1.2 lower |
| --- | ---: | ---: | ---: |
| Mean height-mask foot speed, m/s | 0.143399 | 0.134638 | 8/14 |
| Mean predicted-contact foot speed, m/s | 0.040030 | 0.041033 | 6/14 |
| Per-clip maximum joint-floor depth, mm | 45.166 | 42.810 | 5/14 |
| Joint-depth integral, m·s | 0.075799 | 0.085488 | 4/14 |

The height-mask sample populations differ (6,299 versus 6,692 intervals), as do
the model-predicted contact populations (7,526 versus 7,998). Neither is an
independent contact annotation, so masked means do not compare identical samples.
These fourteen pairs are too small and reused to establish broad quality claims.

Run/roll/stand maximum joint depth improves from 64.948/80.222 mm at seeds
11/22 to 7.309/25.135 mm. Crawl regresses from 109.636/70.797 mm to
125.612/95.555 mm; get-up still reaches 151.517 mm in one v1.2 clip. These
remain failures requiring correction and visual inspection. No claim about the
roll's semantic correctness follows from its better depth proxy.

The v1.1 worker completes in 170.688 s at 1,598,459,904 sampled process-tree
bytes (169 observations); v1.2 in 183.172 s at 1,580,924,928 bytes (181
observations). Both retain the 2 GiB estimate/cap and 600 MiB reserve. These
wall-clock totals include admission/setup and are not comparative inference
performance claims. Both recorded resource traces and terminal states replay.

The separately guarded analysis recomputes every stored metric and exports 28
grey SOMA previews with full root trajectories and every original frame. Every
decoded integer-frame joint/rotation is checked against its source; maximum
joint round-trip error is 6.115514e-7 m and maximum rotation-matrix element error
is 2.446521e-6. All eight stored skin weights are exact. Preview export is not
retargeting or game-engine import validation. The analysis completes in
34.719 s at 95,739,904 sampled bytes, with 36 observations independently replayed.

Comparison receipt SHA-256:
`55e67645370e6450f0c485dc5601f9d335df5eac84a9d9f2aa4d116a30e19c53`.
The 22 loader source tests also pass on Ubuntu (0.29 s) and Windows (1.05 s)
in [hosted run 38964162481](https://github.com/DocMorphic/strep/actions/runs/38964162481).
Inventories are 544 Python/45 Node suites, contact subset 108/five; these are
inventory counts, not full-inventory pass claims.

Decision: retain the historical default and preserve v1.2 as an explicit
condition. Use its corrected-split provenance when planning new research;
do not retroactively call v1.1 benchmark results uncontaminated. The next
comparison needs action correctness and developer/animator inspection before
any quality-based default change. Object/partner geometry, other rigs,
transitions, editing controls and full engine acceptance remain separate work.
No capability or release gate is approved by this experiment.

## Developer preview packet

The local `reports/kimodo-version-comparison-v1/packet/` contains the labelled
comparison, 28 preview GLBs, all local browser dependencies, licenses and a
README with review steps. Its 543-file ZIP has SHA-256
`3be76b4e6a301180fdb0cf844a2f661758aea7f61160210412e33b99d4655d68`
and size 28,238,320 bytes. Every archived file's bytes and ZIP CRC validate.
Packaging completes in 47.078 s at 37,003,264 sampled bytes; all 48 resource
observations replay. The viewer's module syntax validates; browser rendering
and interaction have not been tested. No server was started by this work.

To view the already prepared local packet on Windows, open PowerShell and run:

```powershell
cd C:\wassup\strep\reports\kimodo-version-comparison-v1\packet
py -3 serve.py --port 8772
```

Keep that window open, then visit `http://127.0.0.1:8772/viewer.html`. Choose
each action/seed and press Play. Watch at full speed first, then scrub landings,
plants and transitions. Record the version, action, seed, time and visible
defect or preference; either or both versions may be unsuitable. Playback is
not cleanup time. Stop the preview server with Ctrl+C when finished.
