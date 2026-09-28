# Fourth personal installation: generation history through asset edits

`C:\wassup\Strep Offline Test v4` is a fresh local installation built from the current scripts, assets, engine integrations, pinned licensed model files and standalone Python dependencies. Earlier installations remain intact. This is a same-laptop personal portability experiment, not a redistributable release.

The builder identity is recorded in `reports/offline-install-v4-builder.json`. The checker in `reports/offline-install-v4-check` waits for that exact PID and creation time to finish with a completed build status. Quiet output or a timeout never authorizes a replacement builder.

The fixed input manifest, `reports/offline-generation-history-fixtures-v1.json`, identifies two existing kick motions with different original mobility profiles, including motion bytes, generation records, requests and resolved briefs. `verify_offline_generation_history.py` copies those explicit data fixtures into the new installation before running any authoring jobs. Historical paths in generation records remain provenance; workflow modules and executable input paths must resolve inside the installation.

Using the installed runtime, the workflow creates two character transfers, a transition and its trimmed/retimed descendant. It verifies distinct original source identities, retained-copy counts, local/index/archive hashes, ZIP integrity,455 actual Godot pose samples, module isolation and exact desktop source/bundle agreement. This tests four newly produced assets without new model inference. It does not test UI interaction, motion quality or another computer.

The outer checker verifies the complete installation inventory before and after the workflow and retains both integrity records separately. Its runtime probe checks isolated local Python/PyTorch/Kimodo paths, CUDA and the existing Python external-network guard. PATH contains only Windows System32; Python path/home and token overrides are removed. The guard is not an OS firewall claim.

The builder and checker completed successfully. Both inventory checks verified all 34,836 bundled files. The four packages retained their expected source identities through 120 + 120 + 134 + 81 actual Godot pose samples. The maximum engine position error was 2.10e-7 m; the maximum basis-element error was 4.99e-7. Module paths and the shipped desktop bundle passed the declared checks.

`reports/offline-install-v4-check/completion.json` binds the final installation manifest, workflow, runtime probe and both inventories. `verified-summary.json` independently rechecks the retained package/index/source hashes and engine population. No inventoried file was repaired or replaced during this test. This verifies the declared same-laptop workflow, not new inference, UI interaction, another machine or motion quality. All release gates remain open.
