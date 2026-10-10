# Public source checks

The current explicit inventory contains **439 Python modules and 41 Node suites**. The [supplied-rig scene-force checks](scene-contact-forces-v1.md) pass all 95 focused tests, including thirteen new complete-clock, actual-skin/geometry and explicit-COM regressions alongside the earlier force/dynamics checks. A separate [conic backoff fixture repair](conic-fixture-integrity-v1.md) passes 135 resume/conic/integration checks; [hosted run 38028032428](https://github.com/DocMorphic/strep/actions/runs/38028032428) passes all twelve Linux/Windows jobs at `b3e040f48b9fa1d2a6d5cba54554eb6378d69c30` with the then-current 428-module/41-suite inventory. Later superseded hosted requests were cancelled. [Hosted run 38042959748](https://github.com/DocMorphic/strep/actions/runs/38042959748) completes successfully at `7a54bb9baa343208b74845cf3146df64077d33eb`; subsequent documentation evidence remains separate from those software checks. The [explicit body-tree diagnostic](articulated-motion-dynamics-v1.md) additionally passes 38 focused tree/rigid-body tests. The [supplied-GLB body bridge/workflow](rig-articulated-dynamics-v1.md) passes 64 focused checks locally, adding two declared modules. The [margin-attempt hydration repair](conic-margin-hydration-v1.md) passes 261 focused numerical/native CPU fixture checks, including three new metadata-isolation regressions. The [full development retrieval workflow](full-development-retrieval-v1.md) passes twenty-seven local checks across three declared modules, including the complete 390-by-78 synthetic score population, original method snapshots and multi-batch/unknown-family provenance; actual model/scalar-audit evidence remains separate. The [pinned evaluator payload preflight](text-motion-checkpoint-integrity-v1.md) adds one declared module and passes 47 focused checks, with 27 checkpoint/preparation checks repeated after the final preparation recheck. The [exact chain reach diagnostic](equatorial-arm-guide-v1.md) adds one declared module and passes 21 focused checks; actual target-bound/arm-fit replays remain separate. Software tests do not approve animation quality, inference, engine behavior or the release.

Earlier proposal snapshot: the inventory contained 416 Python modules and 41 Node suites. Twenty new [guarded conic integration checks](guarded-conic-start-v1.md), 33 [direct norm-cone checks](geometry-conic-start-v1.md), ten [proposal callback regressions](proposal-callback-derivatives-v1.md) and the 82 existing solver checks passed without Torch. A separate 584-check frozen CPU fixture validated native coupling/replay, supplemented by all 62 final native continuation checks. Historical hosted results below retain their original scope.

The native character-correction workflow adds CPU job, continuation, contact
revision, evidence-tampering and offline HTTP-handler regressions, plus a Node
DOM workflow. No live Studio connection or renderer is used. In
[run 37175584147](https://github.com/DocMorphic/strep/actions/runs/37175584147),
the Linux source job and both adapter jobs passed. The Windows Python step
reported 2,639 passed and three skipped in 1,761 seconds, then the 30-minute
job limit canceled the run before its Node checks. This is an incomplete hosted
run, not a passing Windows run. At that point the source-job limit was raised
to 45 minutes for its existing suite and subsequent editor checks.

The public repository now defines a GitHub Actions workflow for a suite that needs no motion checkpoint, gated text encoder, character payload, saved study or Godot executable. It runs on Windows and Linux with Python 3.10, pinned NumPy/SciPy/pytest/Trimesh/Rtree requirements and Node 24. Both push and pull-request events run it; manual dispatch is also available.

The suite checks primitive preview geometry, endpoint travel bounds, exact rate/pose conflict certificates, reproducibility of the Studio HTML build and offline contact-editor behavior. This is software regression coverage, not a full-suite, inference, engine, visual or animation-quality approval. The legacy geometry/scene comparison test imports the full Torch-based pipeline and remains outside this model-free suite.

Before publication, a tracked-files archive of commit `954b6fc` was extracted into a new directory with no local `reports`, `models` or virtual environment. A fresh isolated Python environment installed only `requirements-ci.txt` and its package dependencies. All **48 selected Python tests and both Node editor tests passed** from that extracted checkout. Initial collection exposed the legacy geometry test's Torch dependency; it was excluded from this explicitly model-free suite, not changed or presented as passing. Local evidence stays under ignored `reports/model-free-ci-v1`.

The workflow follows [GitHub's Python testing guidance](https://docs.github.com/en/actions/tutorials/build-and-test-code/python). Action revisions are pinned to full commits, its token has read-only contents permission, checkout does not persist credentials, and test execution sets the Hugging Face/Transformers offline flags. Dependency installation still requires network access on a new runner; this does not establish a complete offline installation of Strep.

## Run locally on Windows

Use a separate environment to preserve an existing inference installation:

```powershell
py -3.10 -m venv .venv-ci
.venv-ci\Scripts\python.exe -m pip install --only-binary=:all: -r requirements-ci.txt
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
.venv-ci\Scripts\python.exe -m pytest -q tests/test_object_geometry_mesh.py tests/test_point_rate_reachability.py tests/test_contact_rate_feasibility.py tests/test_contact_engine_events.py tests/test_contact_pose_reachability.py tests/test_contact_pose_sphere_bound.py tests/test_desktop_build.py tests/test_desktop_build_preservation.py
node tests/test_contact_timing_editor.mjs
node tests/test_contact_export_review.mjs
```

The dedicated environment is ignored by Git. The broader test suite still requires separately provisioned assets and tools; all release capabilities remain unapproved.

## Hosted verification

[GitHub run 36642216213](https://github.com/DocMorphic/strep/actions/runs/36642216213), at commit `ac78f29`, passed on both Windows and Linux: 48 Python tests and both Node editor checks per operating system. The first workflow attempt failed YAML parsing because an unquoted command contained a colon; the corrected workflow uses a block string and was locally parsed before the successful run. Hosted success covers this declared source suite only, not the complete model or game-animation pipeline.


The current suite also includes nine authored contact-event timing regressions (57 Python tests total). Historical 48-test results above retain their original scope. These tests cover landing intervals, short clips, multiple regions, empty authored contacts and rejection of invalid clocks/intervals.


The Phase-I feasibility adapter adds 11 model-free tests for normalized Jacobians, feasible and infeasible toy systems, hard constraints, variable bounds and malformed inputs. Positive diagnostic slack cannot turn solver success into contact acceptance. The real cylinder pose study remains an asset-dependent integration experiment.


Eight inward-feasibility LP tests now cover common progress, conflicting constraints, protected passing rows, nonlinear curvature reserve and invalid input. The selected public Python suite now contains 77 tests. This is source verification, not animation approval.


Three LSMR diagnostic tests add fixed-system iteration-cap comparisons, independent damped normal-residual checks and invalid-input rejection. The selected public Python suite now contains 80 tests; this does not qualify a motion or the full product.

## Worker-lock portability

The native scene fitter exposed a Windows-only worker-lock import in Linux CI
at commit `d5aafd5`. [That run](https://github.com/DocMorphic/strep/actions/runs/37096023942)
passed Windows source checks and both adapter jobs, but Linux source collection
failed before its tests ran. The failure is retained as a software portability
issue; it does not change the recorded correction-study outcomes.

The shared lock now uses Windows nonblocking byte locking or POSIX nonblocking
`flock`, retaining the same project lock file and one-job rule. Closing the file
or exiting a process releases ownership; a leftover lock file does not represent
a live job. Contention is reported as busy, while unrelated filesystem errors
remain errors. This is a lock between local processes on supported local
filesystems, not distributed GPU-job scheduling.

Ten model-free regressions cover independent handles, exceptions, contention
between real processes, normal and forced process exit, and error classification.
Both Windows and Linux source jobs run them. Locally, all 142 focused lock,
native scene, clock, edit, rate and skin checks pass on Windows. Hosted Linux
verification is separate from that local result. No model study is repeated,
and no animation, import, training or release approval is granted.

## Current execution headroom

At commit `968d933`, [Windows job 111660213669](https://github.com/DocMorphic/strep/actions/runs/37276266024/job/111660213669) reported **3,300 passed and one skipped** in **3,562.97 seconds**. GitHub's check annotation then records that the job exceeded its **one-hour maximum execution time**. The subsequent Node editor checks were skipped, so the hosted Windows job remains cancelled rather than approved. Its Python result is useful partial evidence, not a completed CI result.

The `source-checks` job now has **90 minutes** of execution headroom and explicitly sets `OPENBLAS_NUM_THREADS`, `OMP_NUM_THREADS` and `MKL_NUM_THREADS` to one, matching the bounded numerical runtime used for local studies. Other job budgets remain unchanged. YAML parsing and exact before/after comparison verify that all test lists, editor commands, matrices, dependencies, action pins and permissions are preserved. No assertion or acceptance limit is removed. Faster execution under these settings has not yet been demonstrated by a completed hosted run; current CI remains pending/in progress.


## Complete contact-interval coverage

The declared inventory now contains 407 Python modules and 39 Node suites. Pure NumPy interval coverage is included in the model-free manifest; exact saved native interval audits are included in the CPU-native job. All existing entries, dependency/action pins, permissions, matrices and job budgets are preserved. Final isolated local validation passes 457 focused checks across fourteen modules and 188 checks across four modules without Torch, including maximum contact-key capacity plus two exterior boundaries. Native study and independent replay results are described in [Complete contact interval](contact-interval-audit-v1.md). Local source results do not establish a completed hosted run or animation/release approval.

The [portable contact-point attribution workflow](contact-point-attribution-v1.md) passes 204 material/patch/revision/Studio-region checks and 20 focused attribution checks after the final float64 normalization refinement. It extends two existing source and test modules, leaving the declared 436-module/41-suite inventory unchanged. The actual ten-point native replay and separate failed articulated contact fits are experimental evidence, not software-test or release approval.


## Previous-pose continuation checks (2026-10-10)

The optional [source-capped previous-pose helper](pose-continuation-v1.md) adds nineteen cases to the existing bounded-ball test file, and registers both previously undeclared bounded-pose files. Together with the four existing bounded/ball checks, **23 checks pass** without Torch, model/asset payloads or engine fixtures. They cover redundant previous-pose choice, actual source norms/unreachable targets, current translation/protected-node/input preservation, invalid-candidate fallback and malformed populations/caps/weights/hierarchies/rigid transforms. All eighteen owned test resource observations replay. Three separate actual source API calls match the frozen native-rig candidates exactly, with twenty-one replayed resource observations. These test/replay scopes do not approve full motion: the complete exported continuation contact clock remains failed. Source coverage becomes 438 Python test modules / 41 Node suites; previous passing hosted commit results retain their original versions and the changed source needs its own hosted outcome. The first publication verifier catches the previously missing registrations; its failed receipt stays preserved and the corrected inventory is replayed separately.
