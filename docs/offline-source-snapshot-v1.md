# Checked Strep source in personal offline builds

The personal installer previously checked the pinned Kimodo source revision and hashed its completed output, but did not bind Strep's own files to a captured source inventory. Editing Strep during a build could therefore produce a package containing files from different development states without a source-change error.

`build_offline_install.py` now captures eligible files under `scripts`, `assets`, `benchmarks` and `integrations` in `project-source.json`. It copies those exact paths and checks each copied file against its captured hash. Before completing the build it checks the source file set/content again, verifies the copied project, and checks the final installation inventory against the original project hashes. `installation.json` also records the hash of `project-source.json`. Detected changes prevent the build from receiving a complete status.

The existing exclusions for Python caches, Git metadata, `.pth` files and editable-runtime stubs remain unchanged. Vendor source, model files and the standalone runtime retain their separate verification. This is a checked content inventory, not an atomic filesystem snapshot or publisher signature. Existing personal installations are unchanged.

Twenty-three focused snapshot, builder and portable-integrity tests pass. Tests cover source additions/removals/edits, corrupted destination files, changed bytes during final inventory, path containment and preservation of existing copies. Tiny synthetic runtime/vendor fixtures exercise the actual builder through both successful completion and rejected mid-build changes; these fixtures are not offline release evidence.

An additional actual copy test verifies all 803 eligible script files, including the scene-feedback UI/importer, the physical-root optimizer and the built Studio page. An isolated Python invocation imports the copied feedback, optimizer and snapshot modules from `C:\wassup\Strep Source Snapshot Check v1`; it uses the development Python runtime. The exact method, source inventory, hashes and import paths are retained under `reports/offline-source-snapshot-v1`.

This verifies the changed source-copy component. It does not replace the earlier full personal-installation studies or establish a new standalone installation, inference run, browser check, second-machine test or release approval. All 14 release capabilities remain unapproved.
