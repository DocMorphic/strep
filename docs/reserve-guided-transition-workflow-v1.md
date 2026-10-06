# Offline reserve-guided transition workflow

`scripts/native_transition_contact_fit.py` creates a separate bridge correction with explicit solver targets and independently audits its appended clips against the original authored limits. It reuses the existing source-bound transition recipe, motion solver, original acceptance auditor and native track exporter. Earlier transition-fit methods remain unchanged so their retained studies still verify against their original method snapshots.

## Request and commands

The request uses schema `strep-native-transition-contact-fit-v1` and exactly four fields: `schema`, `recipe`, `reserve`, `seed`. The `recipe` binding contains `path` and `sha256` for an existing `strep-native-transition-scene-fit-v1` recipe. Paths resolve relative to the request file. The reserve uses the [explicit reserve schema](native-contact-reserve-v1.md), with `contacts_sha256` binding the sealed source transition's `scene.json`, and a nonempty `reserves_m` map from existing contact IDs to positive metres smaller than their original position limits.

`seed` is either null or a `path`/`sha256` binding for a JSON file containing a finite numeric `controls` list of the exact required size. A previous probe file may supply those controls. This initializes a new optimizer epoch; it does not inherit previous iteration counts, optimizer history, feasibility or approval. The starting controls must pass all protected original source conditions. Contact failures may remain at the start and are retained as observations.

```text
python scripts/native_transition_contact_fit.py run reserve-request.json reports/my-reserved-bridge
python scripts/native_transition_contact_fit.py verify reports/my-reserved-bridge
```

The output must be fresh and separate from the source and every input. The run holds the existing local worker lock and uses one CPU thread. It requires the installed scene-proposal dependencies, explicitly bound character/scene files and an eligible native transition recipe; no model sampling or network acquisition occurs.

## Artifacts and replay

The output includes the exact request/recipe/optional seed bytes, original transition snapshot, complete method archive, original rate-cap arrays, explicit reserve binding, raw optimization probes/history and a separate `candidate/` folder. Candidate scene/actor GLBs, root references, contact/event tracks and geometry observations use the existing native artifact format. Original libraries and binary prefixes remain; the selected proposal is an appended clip. Existing engine tools can consume its `candidate/scene.json`, but this workflow does not claim an engine check merely because native export succeeds.

Pure verification re-reads current and archived bindings, typed cap arrays and all stored probes, independently decodes the appended candidate, replays original acceptance and regenerates native tracks in temporary directories. It checks complete expected candidate/probe file populations and compares complete typed decisions. Inputs and methods are checked again at replay completion. Transferred gameplay markers remain unconfirmed, runtime dispatch stays disabled, and engine/quality/training/release approval remains false.

A failed numerical condition can complete as a retained negative proposal. An invalid binding, changed file or incomplete/failed pipeline cannot verify as complete. Verification depends on the original local input paths and installed numerical implementation; this is not a standalone portable solver archive, a Studio Apply route, a universal precision guarantee or production motion-quality approval.

## Validation

All 44 focused tests pass with zero skips: 20 reserve validation/copy cases and 24 workflow input/seed/cap/probe integrity cases. They test metadata and numeric input invariants, not natural motion. The local source receipt is `reports/transition-contact-workflow-source-v1/result.json`, SHA256 `f6dc8f87f1a67c5fb20b64e197780abefb547e868267bc8d47636d571bbaca4b`.

The actual offline CLI exits zero after generation and internal independent replay. On the retained five-knot generated fixture, one actual iteration uses the complete 1,707-time / 665,730-query population and passes native contact/motion/source and actor-transition conditions under the original limits. Native partner gap is `19.494052 µm` against `20 µm`; whole-scene geometry still fails. Original prior files and methods remain unchanged. CLI receipt: `reports/transition-contact-workflow-v1/result.json`, SHA256 `7276f7784eaab5be6e4c95482c354d55aa2581528487d1d84985b3e08567f6bf`.

A separate real serial CPU/headless Godot saved-resource run checks the newly exported candidate at all 1,707 times. Imported partner gap is `19.589304 µm`, and original contact, pose, full CPU-skin, object-pose and root-reference fidelity pass. The one owned engine exits zero with a clean log and stopped tree; the driver is terminal and its lock is free. Imported geometry remains failed. Engine receipt: `reports/transition-contact-workflow-engine-v1/result.json`, SHA256 `77539945c6a368109f1f673c42f12bf238752b03d23965bc64365a348933570a`.

The full numerical verifier rejects three rehashed copies of the actual artifact: forged quality approval, altered original cap dtype and changed trial controls without matching motion bytes. Original artifact/method bytes remain unchanged and the worker lock is free. Integrity receipt: `reports/transition-contact-workflow-integrity-v1/result.json`, SHA256 `53688bae1b76b6b7f2efd9bdf2bbf3f042b2657f19d59ce7526246053e621ae5`.

These generated closed-cube skins and arbitrary gestures establish workflow and import behavior, not human high-five quality or held-out production motion. No live Studio/HTTP/browser, rendering/GPU, physics, new model sampling/training or human review occurred. Production action/rig/object/partner quality and developer/animator cleanup remain open, and all fourteen release evidence arrays remain empty.
