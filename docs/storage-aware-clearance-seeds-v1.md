# Storage-aware internal seeds and uniform parameter proposals

The existing [multi-time clearance command](offline-multi-time-clearance-job-v1.md) operates on pinned stored clips. Two backend additions support further experiments while retaining the original motion and scene contract.

## Explicit storage-aware seed construction

`scripts/native_unapproved_storage_anchor.py` accepts an original stored-pair Job, a numeric control array, explicit absolute storage corrections and every edited actor's actual GLB:

```sh
python scripts/native_unapproved_storage_anchor.py --job reports/input/job.json --controls reports/input/controls.npz --corrections reports/input/choices.json --actor A=reports/input/A.glb --actor B=reports/input/B.glb --out reports/new-internal-seed
```

Use only the edited actors; frozen actors stay bound to their original files. The optional `--array` names the control array and defaults to `controls`. The output directory must be fresh and outside immutable input studies. Original external role paths must be absolute.

The correction JSON is a list of the original storage policy's actor, node, key index, component and signed step records. Corrections are absolute choices relative to the original authoring payload. They retain the original selected keys, authoring digest, component-step envelope and maximum correction count. The constructor audits the exact stored payload using those choices before decoding it against the original problem. Every original scalar/vector/contact/rate/reference bound must pass, along with the original control and trust box.

A genuine change in either controls or storage choices is required. A storage-only change can have zero continuous step. Reordering an identical set of choices does not manufacture a change. Changed controls with explicitly unchanged corrections are also supported. The older unchanged-storage constructor remains available.

Only the Job's anchor changes. Source/reference scenes, edit permissions, static reference tracks, rate caps, contacts, geometry policy and numerical settings remain exact. Reopening the new Job must reproduce every saved control, decoded world, scalar/vector norm and reference observation. Input and implementation mutation reject. Outputs preserve raw input snapshots, expected hashes, method snapshots, actual exports, observations and distinct complete/failed terminal states.

Construction does not scan geometry, reuse derivatives, append a clip or select a library asset. A geometry failure remains attached to research results. Fresh derivatives are required when controls or stored payloads change.

## Uniform control-increment variant

The multi-time command additionally accepts `uniform-control-increment` in `families`. It can be requested alone with an empty `event_times_s`, or compared with the original-norm and event-preserving variants. Explicit events are required exactly when `event-key-preserved` is requested. Each family is a separate proposal; these equalities are not silently combined.

`scripts/native_uniform_control_increment.py` groups every original normalized control exactly once by actor and native translation/rotation track. For each component, it adds one homogeneous row comparing each later control knot's increment with the first knot's increment. No original norm, clock, cap or control column is removed. A single-knot track contributes zero rows. Oversized or malformed complete populations reject rather than returning a subset; the existing maximum of 96 parameter rows applies.

The complete grouping is saved as `uniform-support.json`, and `system.npz` records `uniform_parameter_rows`. The solver retains its existing parameter-equality proposal tolerance. This is a numerical proposal constraint: protected/boundary basis weights, rotations, descendants, skinning and storage can produce nonuniform world effects. All actual stored exports still receive the original strict decoded motion/contact/reference tests. Only the declared eligible selection receives full scene geometry.

No scientific improvement is claimed for this variant yet. The next measured comparison must create fresh complete differences at the verified changed seed, retain every requested export and independently replay the full model and observations.

## Verified generated-fixture seed

The explicit constructor has reopened the previously measured 53-choice candidate as a genuine new internal Job, preserving all original non-anchor fields. It retains 90 controls, 30,450 original norm rows and 1,707 native samples. All original decoded scalar/vector/contact/static/reference bounds pass, with normalized vector-norm maximum excess -0.00000108017126599.

A separate original-context manual decoder parses the new Job without importing the constructor or Job implementation. It reproduces the full controls, stored payloads, worlds and original observations and validates every absolute storage choice. Its exports are byte-identical to the already measured candidate, so the known complete geometry failure remains bound to those bytes: 5.102497259 mm partner depth, 28,904 proper triangle crossings and 1,527 failing sampled checks. Shared geometry predicates verify archive transport; collision arithmetic is not independently reimplemented.

The new Job SHA256 is `dbf7c10c644920388efa68b3a7e1690320dfa07302a9a16d916424c3dc093af3`. Its separate decoder result SHA256 is recorded in the local publication proof. Bulky generated files remain under ignored `reports/`; the public repository publishes source, methodology and concise findings.

These results concern generated fixtures and existing-clip backend edits. They establish no arbitrary-action, production-anatomy, continuous-physics, engine, human-quality or release approval. Original assets remain selected, all fourteen release evidence arrays remain empty and the single full-project goal stays active.

## Local verification

89 distinct focused tests pass with zero skips: 23 storage-aware anchor cases, 12 existing anchor cases, 14 uniform-group cases, 25 multi-time command cases and 15 existing single-guide cases. The two new command cases use a real three-knot editable track: the actual solver receives all six uniform rows over nine controls, while a separately controlled zero proposal exercises actual stored export and stable full-scan selection. Controlled directions are orchestration tests, not scientific optimizer evidence. Earlier failing reports remain retained. A test corrected its expected descendant mask and then used an operand-scaled Float64 roundoff bound for coordinate subtraction; original motion, contact and geometry acceptance tolerances remain unchanged. Both new suites are registered once in Linux/Windows CI; hosted success remains unverified.
