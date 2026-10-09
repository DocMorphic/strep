# Admit offline jobs before loading their models

A runtime memory floor can stop a job safely while still letting it start with too little RAM to load. The contact batch exposed this twice: its third window was interrupted after two completed stages, and a retry stopped during startup before producing any motion. The verified state remains the second completed batch stage; partial work is preserved and cannot become a continuation origin.

`run_guarded_job.py` adds a lightweight wrapper for a chosen Python worker. The caller supplies an explicit expected process-tree RSS estimate. Admission requires that estimate plus the reserved available RAM to remain available across the configured sampled interval. A low sample resets readiness. Admission expiry, another owned worker, or lost headroom just before launch yields `deferred`, with no model child started. The wrapper imports no Torch or model assets while waiting.

After launch, the wrapper accounts for the actual subprocess tree and its exit. Default hard guards remain 600 MiB available RAM, 7 GiB process-tree RSS and 3,600 seconds; callers can only keep or tighten them. It saves the worker and guard source, hashes arguments without copying them into the protocol, records a complete resource trace, preserves logs and never overwrites an existing guard directory. The worker retains responsibility for its job lock, motion protocol and quality decisions. This wrapper does not make process completion an animation approval.

```powershell
.venv/Scripts/python.exe scripts/run_guarded_job.py --worker reports/prepared-contact-worker.py --output reports/new-contact-guard --expected-rss-mib 2048 --stable-seconds 15 --admission-seconds 60
.venv/Scripts/python.exe scripts/audit_guarded_job.py reports/new-contact-guard --output reports/new-contact-guard-replay.json
```

The 2 GiB estimate is a conservative profile for this observed native contact workload, whose earlier process-tree peak was about 1.4 GB. It is not a profile for every generation, training or engine job. Available RAM must therefore reach **2,776,629,248 bytes** for this retry. Memory may still change after admission; sampled runtime guards remain necessary. GPU/VRAM admission, automatic queue integration and broader workload calibration remain open.

The independent resource auditor replays saved phase/clock/memory samples, the stable interval, final launch check, RSS peak, RAM/RSS/time stop decision, recorded exit and worker liveness. It binds archived source and trace hashes. Its certificate concerns observed resource handling, not worker computations or motion quality; it does not prove resource behavior between samples.

An asset-free fixture passes 35 focused checks without Torch. Tests include actual offline subprocess execution with literal arguments, low-memory and busy-worker deferral, last-moment admission revocation, owned descendant termination, RAM/RSS/time guards, nonzero exits, changed worker source, resealed phase tampering and altered source archives. The two new test modules join the existing model-free manifest, increasing its inventory to 409 Python modules with 39 Node suites. Existing workflow jobs, dependencies and permissions are unchanged.

## Observed retry

The startup retry stopped after 4.157 seconds when available RAM fell to 558,809,088 bytes, below the unchanged 629,145,600-byte floor. It produced no completed native result. A first admission-enabled attempt then observed 61 samples over 60.672 seconds and deferred without launching its model child.

The traced V4 wrapper observes 61 samples over 60.703 seconds. Available RAM ranges from 1,911,320,576 to 2,589,220,864 bytes, below the 2,776,629,248-byte admission requirement throughout. It records `deferred / admission_timeout`, starts no model child, creates no native batch output and terminates its supervisor. Independent replay verifies every resource sample, the deadline decision, phase/clock/peak consistency and the archived worker/implementation bindings. No native fit was attempted or promoted by either admission-enabled wrapper.

The 35 source checks pass both in the checkout and in a fresh asset-free fixture using an environment without Torch; the fixture completes in 6.58 seconds. Imports of the supervisor and auditor leave Torch unloaded. The model-free inventory is 409 Python modules and 39 Node suites; the existing workflow is unchanged.

Traced protocol SHA-256: `b9185af27b2e7f37133416c68084b941beff87edcbe56e69bb419e5e1d1f35f8`. Resource trace SHA-256: `93ccc18437faf0b253deea276a92f04024f49a8c2c05bccb487751c4f96b35f0`.

The contact study still has zero complete physical and keyed passes across its 62 contact keys. All fourteen release capabilities remain unapproved, and the full-project goal remains active.

## Parent exit accounting correction (2026-10-09)

Linux source CI for `04aee0d` found three failed guard tests: RAM, RSS and time guards recorded the expected failed status and reason, but the killed worker's reported exit was zero. The shared termination helper had waited for the parent with psutil before `Popen.wait()` could collect its exit status. The guarded-job wrapper now requests `kill_tree(..., reap_parent=False)`: descendants are still stopped and waited for, and the owning `Popen` handle alone reaps the parent. The helper retains its previous default for existing callers. Both the guard-stop and supervisor-exception paths use the new option; resource limits and failed-status decisions are unchanged.

61 checks pass in a fresh asset-free source fixture without Torch. They exercise actual owned subprocess/descendant termination, RAM/RSS/time guards, supervisor exceptions, exact nonzero exit accounting, invalid options, and a platform-independent assertion that psutil never waits for the Popen-owned parent. The existing guarded-job module stays in the model-free manifest, and the previously undeclared process-monitor regression module now joins it, raising coverage to 412 Python modules and 41 Node suites. These local runs were on Windows; the Linux CI regression must still pass before claiming cross-platform validation. Existing historical records are immutable, and this correction adds no motion or release approval.
