# Apply export-feedback correction to saved contact edits

`scripts/contact_export_repair.py` provides a file/export adapter for the [reusable feedback core](export-feedback-core-v1.md). It accepts a saved source, fitted seed, checked stationary-pin plan and original edit budgets. It creates a separate output folder, retains all proposals, and never overwrites the source or promotes animation quality. It is available through Python and the command line; Studio integration is still pending.

The adapter checks native motion, matching clocks and the source preview's poses, mesh, bind transforms and eight skin influences. It recomputes the saved point-rate reference from the original source. Every proposed root-height adjustment is checked against that original source's root and rotation budgets, retains root XZ and the seed's rotations, and preserves held native poses exactly. Export inspection includes BVH/GLB validation, point/global rates, fixed material-point pins, full-mesh floor depth, outside-window poses, serialized constraints and body flags.

This currently supports the existing native SOMA stationary-pin workflow at 30 fps, with its 4–901-frame checked-window limits. It does not yet operate on arbitrary imported rigs, moving targets or scene/partner constraints. Its original source/history and licensed local character dependencies must be available. A local infeasible linear step is a search failure, not proof that no joint-pose or other correction exists.

For an existing saved edit, supply the original budgets recorded by that edit:

```powershell
.venv\Scripts\python.exe scripts/contact_export_repair.py `
  --source reports/contact-jobs/MY_JOB/source-take `
  --seed reports/contact-jobs/MY_JOB/candidate `
  --checked-plan reports/contact-jobs/MY_JOB/checked-plan `
  --output reports/MY_NEW_REPAIR `
  --max-root-lift-m 0.22 --max-rotation-degrees 40
```

The output path must be new. The CLI acquires the existing single-worker lock. Python callers must already hold it. Process identity, input hashes, method snapshots, proposal audits, selected output and completion hashes are retained. Missing or changed references and failed exports remain failures.

## Measured adapter run

Forty-four focused tests pass across original-source budgets, exact held poses, feedback selection and earlier measured helpers. The CLI help command passes. A three-case run creates fresh exports using the adapter:

| Input | Result |
| --- | --- |
| Original crawl-22 fitted seed | Rejects the first exported release regression, accepts the second proposal, and reproduces the earlier passing native candidate byte for byte; maximum root adjustment 1.750220e-6 m. |
| Restarted crawl-11 | Local linear search remains infeasible at every optional-headroom level; retains the input motion and all pin/floor/body failures. |
| Restarted kick-11 | Local linear search remains infeasible at every optional-headroom level; retains the input motion and all pin/rate/body failures. |

Both retained restart motions are byte-identical to their supplied native inputs. The successful crawl-22 repair has no body flags; the other cases retain ten and four flags respectively. Completion files, every saved artifact, original inputs and historical method snapshots were verified. Evidence is retained in ignored `reports/contact-export-adapter-v1/`.

After this run, the adapter gained an explicit source-preview preflight. All three real sources pass that check. A deliberately mismatched but structurally compatible preview is rejected through the adapter before output creation. The search/export path was unchanged by that addition; the expensive three-case run was not repeated.

There are no new engine observations or human ratings from this adapter verification. The selected native files match previously engine-tested files, but this is not a new engine-import test and does not approve motion realism. Broader joint/support correction, Studio integration and the full release matrix remain open.
