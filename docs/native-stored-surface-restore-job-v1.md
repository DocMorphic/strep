# Pinned saved-model surface correction command

`scripts/native_stored_surface_restore_job.py` makes the [depth-reserve experiment](native-depth-reserve-study-v1.md) reproducible through an explicit offline request. It operates on a completed, independently replayed stored-pair model. It does not run or train a motion-generation model, rebuild a Jacobian, or automatically select an animation.

## Request and execution

The request schema is `strep-native-stored-surface-restore-job-v1`. All three input paths resolve relative to the request file and require exact SHA256 pins. Use the original stored-pair job request, its completed study result, and its complete independent model replay result. The original study must still match its current and archived producer implementation, original inputs, complete artifacts and native-feasible anchor. A changed implementation or asset requires a new explicitly bound study.

```json
{
  "schema": "strep-native-stored-surface-restore-job-v1",
  "job": {"path": "original-job.json", "sha256": "<64 hexadecimal characters>"},
  "study": {"path": "original-study/result.json", "sha256": "<64 hexadecimal characters>"},
  "independent_replay": {"path": "model-replay/result.json", "sha256": "<64 hexadecimal characters>"},
  "settings": {
    "depth_reserve_m": 0.00002,
    "iterations": 32,
    "append_native_passing": true
  },
  "label": "Unapproved diagnostic correction"
}
```

Replace the example paths and placeholder hashes with the actual retained inputs. `depth_reserve_m` is a finite number from zero through 0.0001 metres and cannot exceed the original depth limit. `iterations` is an integer from 1 through 64; `append_native_passing` is a boolean; the label is nonblank and at most 160 characters. Extra request fields are rejected. The required Python dependencies are the existing model-free CPU environment, including NumPy, SciPy, threadpoolctl, trimesh/rtree and Clarabel.

```powershell
python scripts/native_stored_surface_restore_job.py --request restore.json --output reports/new-surface-restore
```

The output directory must be fresh. Preflight rejection creates no study output. After successful preflight, the command archives its implementation and input records, checkpoints each returned solver phase, and retains a failure record if execution raises. Requests, assets, saved matrices and implementation bytes are checked again before successful completion. Existing studies and source clips are never rewritten.

The replay receipt is a pinned development-provenance contract, not a signature or a substitute for performing the independent replay. The unit tests deliberately use synthetic receiver receipts; genuine retained-model evidence is measured separately below.

## Guidance, selection and actual acceptance

Only the copied local guidance policy receives the depth reserve. Original native/contact/rate/reference/control bounds and external geometry acceptance remain unchanged. The original depth/surface phase implementation runs through a private recorder; its global solver factory is not modified. `solver.json` separates `source_result` from the final `delta` and `direction_source`.

Bounded affine restoration is attempted only when the primary phase passes with a strictly nonpositive complete native excess and the secondary phase is rejected solely for native conditions. Other phase errors retain the original decision. An accepted original minimum-norm phase is not overridden. The helper measures the complete native norms, surface rows and depth witnesses along the projected endpoint segment at zero native tolerance; improvement remains local guidance. Every requested fraction then receives an actual stored export, authoring audit, complete decoded native observations, original reference bounds and complete original sampled geometry audit, including failed fractions.

When requested, native- and reference-passing fractions get separate appended diagnostic clips. **Geometry can still fail.** Appending preserves the full original animation library, binary prefix and scene metadata, and checks every appended native world against the raw export. Every record remains unretained and unapproved for quality and release; the original selected asset remains selected. These outputs are not ready-to-use collision-safe game animations.

## Complete retained-model validation

The public command repeats the already pinned sixty-control model without rebuilding it: 29870 native norms, 276815 scalar surface rows and 2873 depth witnesses. With 20 micrometres of reserve, guidance uses 4.98 mm while external acceptance stays at 5 mm. Both solver phases return `Solved`, but the surface phase exceeds the unchanged native tolerance. The bounded segment retains fraction **0.9999973045196384**, reproducing affine surface excess **2.454209507160 → 2.333154686449**.

All four requested fractions retain every 1707 native and 1673 geometry sample:

| Fraction | Stored native failures | Centered auxiliary failures | Contact failures | Depth, mm | Triangle records | Failed geometry samples | Appended clips |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1.0 | 8 | 4 | 0 | 4.978978 | 30113 | 1605 | 0 |
| 0.5 | 0 | 0 | 0 | 4.989988 | 30271 | 1603 | 2 |
| 0.25 | 0 | 0 | 0 | 4.995283 | 30382 | 1603 | 2 |
| 0.125 | 3 | 0 | 0 | 4.998034 | 30419 | 1603 | 0 |

All original reference bounds pass; contained-vertex counts are zero. The half and quarter steps pass native/contact/reference/depth checks. Persistent triangle crossings make every complete geometry fail. Both passing motion fractions append index6 diagnostic clips for the two actors, each retaining all six original source clips. No selected production animation changes.

Fifty-five focused CPU tests pass in 146.76 seconds, with zero skips. They cover real tiny v1/v2 saved-model exports, request and provenance rejection, strict proof counts, immutable outputs, phase-selection behavior, solver-failure recording, frozen-partner preservation and library/native-world fidelity. Two v1/v2 end-to-end tests pass in a further 17.74 seconds after adding explicit input-role and request metadata. The GitHub workflow includes the new suite; hosted success is not claimed.

The separate retained-model consumer reconstructs every segment probe, bisection decision and selected direction without importing the command, restoration, solver, model, storage or centered-proxy implementations. It constructs the existing `ExportReplay` with the legitimate pinned original completed study, recomputes original rate arrays and static references, and replays all raw payloads, controls, decoded worlds, native observations and reference bounds. It also verifies all four appended source libraries, binary prefixes, scene metadata and complete native worlds. Collision observations are verified as saved transport; collision predicates and producer auxiliary centered observations are not independently reimplemented.

Generated cube-skin fixtures supply software and numerical development evidence only. They do not supply production humanoid realism, arbitrary-action success, new inference/training, engine, physics, human review or cleanup-time evidence. All fourteen release evidence arrays remain empty. The next work is collision reachability and broader action/rig/object/partner validation under the existing full-project goal.

Immutable ignored local receipt SHA256 identities:

- Request: `033c0c3c71995b59bc9e19887757172ffc2d078cab9727b4b53d8331e3a2dfc2`.
- Completed command: `98f17ad16e5dd681bacb69961e13f289ad9ade99f27079d589e1cf5eccb803fb`.
- Separate segment/export/library replay: `5eef8cb26a83e440a57fa04927f0eac19f4a7ab37473ac90a6c38544ffa08a11`.
