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

Use all seven requests and both original seeds (11 and 22) from
`reports/action-coverage-v1/request.json`: jump/land, crawl, dance/turn, wave,
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
Results will be recorded after both guarded workers and independent replays
finish. Human review, object/partner geometry, rigs and export validation remain
separate requirements under the single project-wide goal.
