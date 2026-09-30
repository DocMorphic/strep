# Pinned source preparation for Windows development setup

The public repository excludes the upstream Kimodo checkout. Previously,
`scripts/setup.ps1` could install CUDA PyTorch before discovering that
`vendor/kimodo` was missing. It also overwrote the recorded development
environment in `benchmarks/environment.windows.txt`.

Setup now checks for Git and Node.js alongside uv. After creating Python 3.10,
it runs `scripts/prepare_vendor.py` before installing Python packages. This
standard-library helper fetches the exact commit from `benchmarks/sources.lock.json`
from the official Kimodo Git repository into a temporary directory, verifies the
commit and clean checkout, and moves it to the absent `vendor/kimodo` destination.
It does not acquire model weights or install packages.

An existing clean checkout at the pinned commit is reused without fetching.
An occupied folder, different revision or local changes cause an error while
preserving the existing files. A failed fetch leaves its temporary directory for
inspection and does not publish an incomplete checkout as `vendor/kimodo`.
The source lock is checked again before publication; a mid-operation change
causes failure. Paths are checked to remain inside the project before the move.

From the project root, source preparation can also run independently with any
compatible Python 3.10+ interpreter and Git:

```powershell
python scripts/prepare_vendor.py
python scripts/prepare_vendor.py --check
```

The first command may fetch source code when it is absent. `--check` only
verifies an existing checkout. The complete developer setup entry remains:

```powershell
powershell -File scripts/setup.ps1
```

Each successful package-environment capture now goes into a unique ignored
`reports/setup/<id>/environment.windows.txt` directory. The historical environment
record in `benchmarks` remains unchanged. Setup prints the new report directory.

Thirteen tests use local Git repositories, including a remote tip newer than the
locked commit. They cover exact commit selection, detached checkout, reuse with
an unavailable remote, preservation of tracked/untracked changes and wrong
revisions, occupied destinations, failed fetches, changing locks, invalid pins
and missing-source check mode. The actual development checkout independently
passes `--check` at commit `58e781898b3d7e328a676a75d3e338c45dce3ad9`.
The PowerShell script passes syntax parsing. No package installation or model
download was performed for this change.
All 778 minimal public Python checks pass, including the new source tests.

This repairs source preparation, not the entire clean-clone installer. Dependency
resolution is still not a fully hashed installation lock; character payloads,
viewer dependencies, gated models, engine setup, native MotionCorrection and
complete clean-environment inference validation remain separate work. Existing
personal offline-installation evidence is described in `offline-install-v1.md`;
it does not establish a redistributable release.
