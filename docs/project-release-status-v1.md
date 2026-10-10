# Inspect the full-project release gaps

`project_release_status.py` reads the existing release matrix without Torch, model assets or network access. It separates each capability's declared status and development-reference count from its release reports, records missing reports, unbound held-out fixtures and unset acceptance gates, and binds the matrix, implementation and present release reports by SHA-256. All fourteen capabilities remain visible; action families are evaluation strata, not a prompt whitelist.

```powershell
python scripts/project_release_status.py --output reports/my-release-status/inventory.json
```

Choose a fresh report path. The tool preserves existing reports and requires in-project portable references; escaping paths, duplicate capability IDs/release references, ambiguous JSON, nonfinite values and changed inputs are rejected. Fixture references must be JSON. It counts development references without reading their contents. Release report files are fingerprinted, but their claims, metrics, reviewer identities, method freeze and fixture exposure are not validated by this inventory.

The current matrix yields fourteen capabilities with no release evidence, one unbound held-out fixture manifest and four unset gate fields: transitions, style calibration, force/balance validation and per-joint dynamics. These are nineteen configuration/evidence gaps, not nineteen motion defects or a full count of missing release work. Tests, file presence, a `complete` status or a report's approval flag never grant approval; every output explicitly remains `inventory_only`, with quality/release approval false.

Eighteen focused checks pass without Torch, including fourteen new cases. They exercise misleading completion claims, missing reports, reference containment, duplicate JSON/identities/evidence, nonfinite input, read-time mutation and immutable outputs, alongside existing prompt-reservation checks. The parsed CI inventory adds only the new test module and reaches 423 Python modules / 41 Node suites; workflow, dependencies and runtime budgets are unchanged. Latest hosted CI must be checked separately.

The actual configuration inventory remains local under ignored `reports/project-release-status-v1`. This is a diagnostic of release prerequisites, not generation, training, motion review or a release decision. The same project-wide goal remains active.
