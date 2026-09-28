# Personal offline installation experiment

This experiment copies the existing licensed local installation to a separate folder with spaces, without carrying over the development environment, credentials, inference caches or research outputs. It is a local portability test, not a redistributable release or a motion-quality approval. The full-project goal remains active.

## Build and launch

From the development project, run `.venv\Scripts\python.exe scripts\build_offline_install.py "C:\path\to\new installation"`. The destination must not exist and must be outside the development folder. The current builder requires Windows, the acquired pinned models, the clean pinned Kimodo checkout, the installed Python dependencies and the acquired Godot engine. It requires at least 40 GiB free space for the copy and subsequent encoder cache.

The result includes `Strep.cmd`, standalone Python 3.10, the installed dependency versions, locally exported Kimodo source, four pinned model snapshots, character/viewer assets, engine integration scripts and Godot. `Strep.cmd` starts the Studio; `Strep.cmd --port 8770` selects a different loopback port. `Strep.cmd verify` hashes every inventoried file, and `Strep.cmd probe` checks runtime paths, source identity and CUDA. A compatible NVIDIA GPU and its Windows driver remain host requirements.

Python uses a relative `python310._pth` file. The initial runtime probe caught this standalone Python build enabling the user site despite reporting isolated mode. The builder now explicitly initializes `ENABLE_USER_SITE=False` in the bundled `Lib/site.py`, before any user directory is processed. The original and patched hashes are recorded in `runtime/isolation-patch.json`; this is a documented local standard-library configuration patch. A canary package supplied through both `PYTHONUSERBASE` and `PYTHONPATH` remains undiscoverable. The editable Kimodo registration pointing into the development folder is excluded. Exported vendor files have a complete hash inventory tied to the source lock; missing, changed, extra or escaping files fail verification. The inventory is a local integrity record, not a publisher signature.

The runtime uses installation-local Hugging Face paths and offline flags, removes inherited token variables, and rejects external Python socket/DNS operations through an audit hook. Loopback remains available for Studio. This is not an OS firewall or sandbox and does not certify the behavior of native networking code. Credentials and derived encoder matrices are not copied. First-prompt encoding rebuilds its disk cache locally.

Acquisition records retain their original historical directories for provenance; model resolution uses the current installation and pinned revision. Preserved license files and dependency metadata do not grant redistribution rights. This builder is intended for the current user's local copy.

## Verification protocol

`reports/offline-install-v1/protocol.json` freezes a new five-second overhead-stretch prompt and seed 927 before inference. Verify the complete copied inventory and isolated runtime from an unrelated working directory with development tools absent from PATH. Check the empty Studio before generation. Run the uncached prompt, retain native motion and export diagnostics, then run `scripts/verify_offline_workflow.py` on the resulting action-job directory.

The workflow checker imports the bundled licensed CesiumMan, transfers the new motion, creates an 80-percent-speed edit, and imports native, transferred and retimed GLBs in the bundled Godot with every-frame joint checks. It never reruns an existing completed fixture or overwrites a previous result.

The scene viewer now discovers available scene collections through a local endpoint. It accepts an empty workspace and excludes engine-test manifests that contain cases rather than scenes. Existing development reports remain available in the original installation.

## Current evidence

The separate installation is `C:\wassup\Strep Offline Test`, served on port 8770. The original Studio remains on 8768. Build, probe, source checks, CUDA tensor check, external-package canary, Python network-guard checks, empty-workspace UI and all 34,655 revision-2 inventory hashes passed. The initial failed probe and original `site.py` are preserved. Final revision 3 contains four explicitly verified UI file updates on top of the complete revision-2 verification; before/after hashes and manifests are retained.

Actual Studio job `20260927-143634-0c84c3bf` generated and exported the frozen prompt/seed in 234.51 seconds including first-run encoder cache preparation. Motion inference was about 10 seconds; peak supervised process-tree RSS was 2,477,051,904 bytes. All 738 parameter-index entries refer to files inside the new installation. The UI assigned the request ID `custom-motion`; prompt, duration, label and seed match the frozen protocol.

The native 150-frame, transferred 150-frame and retimed 187-frame GLBs passed Godot 4.7.2 import and every-frame joint comparisons (487 frames). Maximum position error was 4.42e-7 m; maximum rotation-matrix element error was 6.03e-7. Eight HTTP artifact downloads match local hashes, and the native ZIP passes CRC and matching-member checks. Character results are rediscovered by the relocated UI, and the retimed clip scrubs correctly.

The stretch revealed a fixed-camera bug that cropped raised hands. Preview now computes bounds across the whole clip's bones in a horizontally root-relative frame, adds 18 cm skin allowance and fits the limiting field of view. This is a preview heuristic for the native SOMA character, not a mesh/contact certificate. Windowed/full-screen raised-arm views and playback through the final arms-down pose were visually checked. Empty scene controls are disabled, the empty preview has a useful message, and the obsolete link to development-server running reports is removed.

The full regression suite passed 569 tests with five existing warnings; after final UI changes, 14 targeted integrity/discovery/build tests passed. The installed UI rebuild matches its shipped sources. No action correctness, full-surface quality, independent human review or cleanup-time approval is implied. This one-machine experiment cannot establish support for every Windows/GPU combination or all authoring workflows. Release gates remain open; records are in `reports/offline-install-v1/` and the independent installation's `reports/` folder.
