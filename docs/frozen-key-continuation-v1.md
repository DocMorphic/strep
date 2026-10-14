# Frozen correction workers across application updates

The native-key studies record all Python files and require matching current and archived source bytes. This protects reproducibility, but also makes an unrelated Studio server change prevent resuming an older correction. `scripts/frozen_key_continuation.py` provides an explicit execution environment for those recorded methods. It does not weaken the existing current-source checks or rewrite old result/request/replay receipts.

The builder requires the [public continuation recipe](native-key-continuation-job-v1.md) with independently recorded parent result/request/replay SHA256 bindings. It locates the original initializer through the bound recipe and reconciles every Python file in both immutable archives. Conflicting recorded versions reject rather than silently choosing a version. Missing continuation/replay orchestration files come from an explicit three-file helper list, with their current bytes bound separately. Every source input and archive hash is checked before copying and again afterward. Only inputs and fresh outputs under the local project's reports directory are supported.

The separate worker process imports the resulting frozen scripts. It checks the complete source-file population, rejects extra source or bytecode, disables bytecode writes, and rejects an already-populated numerical import environment. Original algorithms retain their historical source-hash root. The one explicit runtime assignment sets the archived lock module's root to the live project so this worker competes for the same OS lock as generation and other corrections. The bootstrap's hash and shared lock root are recorded in both runtime and execution receipts. No process may use the frozen directory as a separate worker-lock namespace.

This executes archived Python code: use source archives from your own trusted, reviewed project runs. A hash identifies source bytes; it is not an independent code-safety review. This version is a local CLI prerequisite for Studio integration. It adds no Studio selector, recursive continuation chain, private-trial migration, approval or new model inference.

Using the prepared offline environment, build a fresh runtime through the ordinary supervisor:

```powershell
uv run --offline --isolated --no-project --python 3.10 --with-requirements requirements-ci.txt python scripts/run_guarded_job.py --worker scripts/frozen_key_continuation.py --output reports/frozen-build-guard --expected-rss-mib 2048 --stable-seconds 15 --admission-seconds 600 --max-seconds 900 -- build reports/continuation-recipe.json reports/frozen-runtime
```

Then execute the correction in a fresh worker and output directory:

```powershell
uv run --offline --isolated --no-project --python 3.10 --with-requirements requirements-ci.txt python scripts/run_guarded_job.py --worker scripts/frozen_key_continuation.py --output reports/frozen-run-guard --expected-rss-mib 2048 --stable-seconds 15 --admission-seconds 600 --max-seconds 900 -- run reports/frozen-runtime reports/frozen-correction
```

Replay with independently recorded new result/request hashes:

```powershell
uv run --offline --isolated --no-project --python 3.10 --with-requirements requirements-ci.txt python scripts/run_guarded_job.py --worker scripts/frozen_key_continuation.py --output reports/frozen-replay-guard --expected-rss-mib 2048 --stable-seconds 15 --admission-seconds 600 --max-seconds 900 -- audit reports/frozen-runtime reports/frozen-correction reports/frozen-replay --expected-result-sha256 <trusted-result> --expected-request-sha256 <trusted-request>
```

To audit an existing public continuation job, add `--audit-producer <job> --expected-result-sha256 <trusted-result> --expected-request-sha256 <trusted-request>` to the build command. Its complete method archive is reconciled as a third snapshot, and the runtime is bound to that exact audited job. This covers later audit modules absent from the earlier parent. Without that option, an existing job can only replay if all its recorded methods already agree with the frozen files. Each supervisor's resource trace is separately replayed with `scripts/audit_guarded_job.py`. The unchanged RAM/RSS/time guards and one-worker policy apply; dependencies remain a separately prepared offline environment. This is source reproducibility, not a bundled installer or dependency-container snapshot.

## Checked bootstrap behavior

Seventeen selected tests pass in 14.41 seconds; the final guard completes in 31.656 seconds with 33 resource observations, and its trace replays. Controlled subprocess fixtures prove that changed live source cannot replace archived imports, that run/audit receipts retain the shared project lock root, and that a held live lock blocks the archived worker. Tests reject changed parent/replay/input/archive/bootstrap bindings, conflicting versions, escaped paths, altered scope, extra Python source and bytecode. These controlled fixtures test bootstrap behavior, not humanoid animation quality. Evidence remains under ignored `reports/frozen-key-continuation-validation-v1`, `-v2` and `-v3`.

The first development-character replay stops before any clip reconstruction because the later job records an audit module absent from the two earlier archives. Its failed guard completes in 30.610 seconds/32 observations and its resource trace replays honestly as failed. The explicit third snapshot fixes this provenance gap; original source, proposals and failure evidence remain unchanged.

## Complete development-character replay

The corrected builder reconciles 1,397 frozen Python files from the original initializer, standard parent and independently bound continuation job. It completes in 80.609 seconds/81 resource observations, and its trace replays. A fresh frozen worker then recreates all five actual exports, complete contact/geometry/motion observation arrays and every retention decision. Its numerical receipt preserves the original initializer/reference and the exact 41-rate/17-floor rejection; the optimizer is not run. The execution receipt records the live project lock root and complete runtime hash. Numerical execution takes 194.937 seconds; the guard takes 296.922 seconds including RAM admission, with all 294 observations replayed. The earlier failed replay remains intact. Evidence stays under ignored `reports/frozen-key-continuation-v2` and `-v3`.

No new correction, inference, training, engine execution, held-out fixture, animator ratings or cleanup measurements occur. The earlier best private result remains 35/12 and rejected. All fourteen release capabilities and calibration gates remain unchanged and unapproved; the entire-project goal stays active. The published preceding command commit `cb9a97f` passes all eight focused hosted jobs on Windows/Linux; the new source's hosted checks are a separate outcome. Next is explicit Studio job integration using this runtime, followed by broader action/rig/style/scene/partner/runtime/held-out and human validation.
