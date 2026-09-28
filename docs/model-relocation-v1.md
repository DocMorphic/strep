# Resolve model weights from the current project

Runtime loading already derived model paths from the current project and pinned source lock. Several preflight and verification paths instead trusted absolute directories recorded when the weights were acquired. After moving a project, those checks could fail or inspect a surviving old copy while loading the new one.

`strep.model_directory` now resolves acquisition entries through the current pinned model locations. Unknown repositories, revision mismatches and directories resolving outside the project are rejected. The historical acquisition manifest is preserved. A missing current copy never falls back to old weights.

Generation, encoder/cache validation and study verification now use this resolver. Model bytes and inference mathematics are unchanged. Frozen experiment implementation snapshots remain untouched; older cache provenance may correctly require a fresh encoding run if it pins a changed loader script.

The read-only audit in `reports/model-relocation-v1/verification.json` checked all 39 recorded files across four models, totaling 17,547,869,698 bytes, against their recorded hashes. The acquisition manifest remained unchanged. Six synthetic filesystem tests cover relocation into a directory with spaces, a surviving stale copy, missing current weights and invalid pins. These checks do not demonstrate a portable virtual environment, offline installation or complete inference after moving a real project.

The initial full suite had 441 passes and one failure: the pose-target HTTP test used the real project's worker lock while a trajectory experiment was running. The test now uses its temporary source workspace for the real lock implementation. The production lock is unchanged. The isolated rerun passed all 442 tests in 127.85 seconds. A subsequent addition explicitly exercises real lock contention, checks HTTP 409 with no output or source mutation, then checks success after releasing the lock; that focused test passed in 9.53 seconds. The initial log is retained as `full-tests.log`; the successful suite and added assertion are recorded separately as `full-tests-isolated.log` and `lock-isolation-test.log` in the same report directory. Four existing PyTorch deprecation warnings and one SLSQP trial-clipping warning occurred in the full suite; accepted solver bounds remain independently tested.

Reproduce the read-only file audit from the project root:

```powershell
.venv\Scripts\python.exe scripts/verify_model_locations.py --output reports/model-locations-check.json
.venv\Scripts\python.exe -m pytest -q tests/test_model_paths.py
```

This is development evidence for the active full-project goal. Offline installation and release acceptance remain incomplete.
