# Offline material-contact scene packages

`scripts/material_scene_package.py` connects explicitly authored skin regions to the native scene-authoring job. Preparation creates a complete package that can move without its original draft, character or material-bundle paths. Execution is a separate step requiring an explicit local engine executable and an idle production worker.

## Prepare and verify

Start with a local `strep-studio-native-scene-v1` draft and a [material revision specification](material-patch-authoring-v1.md). The draft supplies animated GLB actors, scene placements, objects, contacts, declared geometry and any existing object edit. The specification pins the draft and patch-bundle results and explicitly orders the selected material vertices. Studio-served URLs must be resolved to local files before this CLI workflow; preparation performs no network request.

```powershell
python scripts/material_scene_package.py prepare ORIGINAL_DRAFT.json MATERIAL_SPECIFICATION.json FRESH_PACKAGE
python scripts/material_scene_package.py verify FRESH_PACKAGE --expected-result-sha256 PACKAGE_RESULT_SHA256
```

Preparation checks the complete existing material revision before copying anything. It keeps exact source draft/specification bytes and copies every actor plus each complete referenced material bundle, including all transfer parents and archived methods. Original actors, animation indices, placements, contact timing/limits, objects and declared geometry are retained. It transports only actor/bundle paths and the hashes of newly serialized JSON files. The native revision validator still checks the complete transported baseline and explicit material edits.

The package includes `baseline.json`, `selection.json`, `draft.json`, `material-proof.json`, `contacts.json`, `geometry-policy.json`, copied inputs, method receipts and a bound result. An existing object edit is also bound to the newly serialized contacts. Actor bytes, complete patch selections, vertex order and reduction are preserved. The original files remain untouched and are not replaced with the transported versions.

Each actor is bounded by the existing 128 MiB asset limit. The default complete prepared-payload budget is 512 MiB; `--maximum-payload-bytes` can explicitly raise it up to 8 GiB. This includes copied actors, complete material parents, methods and derived payloads. Distinct declared material-bundle references are copied once; alternative spellings may count separately. Oversized populations fail rather than being truncated. Failed partial outputs are retained with their failure record, and output folders must be fresh.

Verification regenerates the transported draft, material revision, proof and native scene policies from the exact copied original intent. It replays every material bundle, checks full populations and source/method hashes, rejects changed protected fields even when JSON hashes are rebound, and requires exact JSON types for result flags/counts. It rejects path escapes and extra files. A moved package still requires matching current implementations; archived Python is never executed.

## Execute the authoring job

```powershell
python scripts/material_scene_package.py run PACKAGE FRESH_EXECUTION_OUTPUT PATH_TO_GODOT_CONSOLE_EXE
```

The execution folder receives an immutable copy of the verified authoring package, a source-bound recipe and the complete existing native authoring job. For actor-only scenes, this includes native point contacts, actual actor import/full-skin/geometry and saved-data replay. For object scenes, it additionally includes object export, common-clock preparation, actual saved object-resource import and combined imported actor/object geometry. Existing optional object edits retain their original explicit bounds.

Completion and numerical acceptance remain separate. A completed job may contain failed contacts or geometry; the wrapper retains those decisions, the original scene selection and the complete material lineage. It does not change animation clips automatically, revise limits, admit training data or approve motion quality. The authored normal/side policy is separate and still needs the [imported surface-contact audit](native-imported-surface-contacts-v1.md); successful point matching does not imply correct palm orientation.

This workflow has no action whitelist and no inferred point correspondence. It makes explicit target authoring reproducible; choosing useful regions, anatomical review, motion correction, root/event integration, real-time engine playback, GPU appearance and human cleanup review remain separate requirements. Studio has no newly wired material-selection UI in this change.

## Source checks

`tests/test_material_scene_package.py` covers complete raw-source/parent preservation, explicitly ordered partner and object regions, optional bounded object edits, replay after moving without original file reads, protected-field tampering despite rebound hashes, path escapes, extra/missing files, JSON types, current-method changes, worker/output exclusion and failed partial-copy retention. Its native authoring integration uses actual tiny animated GLB decoding, imported skin correspondence, contact/geometry APIs and replay; only the engine subprocess is mocked. Numerical geometry failures remain failures in the completed diagnostic job.

The checks copy public source and required test fixtures into an isolated folder, without models, downloaded characters or vendor code. They establish source behavior and portable authoring intent; they are not a generated-action study or proof that an anatomical region was chosen correctly. Windows and Linux CI run the package tests separately from the longer geometry suite.

The fresh isolated run passes **70 checks**: **29 package tests and 41 existing native authoring-job regressions**, in 668.19 seconds. Original and copied source hashes remain unchanged. Result receipt SHA256: `3a12875db30b4333f186f6958212d0b944adf62d059d403a3c3795540896e8a4`. An earlier expanded run was stopped after two new fixture points inside a sphere were correctly rejected; its original snapshot and partial log are preserved without claiming a completed population. The fresh run places those points on the unchanged declared surface. No actual engine, model generation or production motion replay occurs in this source check.
