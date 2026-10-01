# Native contact review inside Studio

Studio now discovers completed native contact comparisons in a separate review
panel inside its Scenes window. Each comparison keeps its own seconds clock and
exact fractional contact event, and provides asset-bound developer observations.
The existing frame-based scene editor and selection state remain separate.

## Use

Start Studio with the local environment:

```powershell
.venv/Scripts/python.exe scripts/action_studio_server.py --port 8768
```

Open `http://127.0.0.1:8768/studio`, open Scenes, expand **Native contact
comparisons**, choose **checkpoint contact v2**, and click **Open comparison**.
Compare the three versions at the same seconds time. **Contact** seeks exactly
2.0917225950783 seconds; **Hands** frames the meeting hands. The full native clip
duration is 3.6666667461395264 seconds. Closing the panel unloads its viewer;
hiding the Scenes window pauses playback.

Rate failure counts, recorded floor penetration and discrete mesh-check limits
stay visible. This is the authored palm-region development fixture. It does not
approve the original fixed-point benchmark, general interactions or realism.

Under **Developer observations**, enter a reviewer name and notes, select an
interval in seconds or use the exact playhead, and download the JSON observation.
Drafts are isolated by comparison/build/manifest/result hashes, version, both
actor assets and placements. Loading or switching a version invalidates the
active review until both actor hashes have been checked. Notes remain local;
no review is submitted automatically. Exports explicitly retain
`independent_human: false`, `cleanup_test_performed: false` and
`quality_approved: false`.

## Publication and evidence

`publish_native_contact_review.py` copies a completed, bound comparison into a
fresh `reports/native-contact-reviews/<name>` folder. It rehashes source evidence,
preserves GLBs and the manifest, adapts only the viewer's dependency URLs for
Studio, and archives four publication/viewer implementations. It does not rerun
a solver, modify previous studies or change a release gate.

```powershell
.venv/Scripts/python.exe scripts/publish_native_contact_review.py reports/checkpoint-contact-review-v1 new-native-review
node scripts/verify_native_contact_review.mjs reports/native-contact-reviews/new-native-review reports/new-native-review-loader.json
```

Use a fresh name and verification output. Acquisition of the local viewer
runtime and licensed character/model files remains a separate setup requirement.

`/api/native-contact-reviews` lists valid packages and reports rejected ones.
Serving checks the entire package's allowed output hashes and method archives;
unbound files, traversal, changed actors and promoted scope flags are rejected.
The separate namespace permits only the packaged HTML, modules, GLBs, audit
JSON and license text. It does not enable HTML serving throughout `reports/`.
The notes module works offline and makes no external requests.

The completed `checkpoint-contact-v2` publication verifies 4,822 bound input
files, 18 served outputs and four archived methods. Offline glTF/Three.js checks
pass for all six original eight-weight SOMA actor clips with zero errors and
warnings, including forward and backward seeks at zero, event and full duration.
The embedded viewer module passes Node syntax validation. All 1,143 Python source
tests and the workflow's JavaScript checks pass. Synthetic API/DOM/notes tests
are test fixtures, not human review records.

| Record | SHA-256 |
| --- | --- |
| Published build | `4c96dc68aec92035efc31e368cdb367d9ed4635798d656257b35f97d05920c3d` |
| Unchanged comparison manifest | `c8510a88527e375e450d963b239d4285740a452d7e52ac9c0d44c7e0fc1ebf8e` |

## Remaining work

Browser rendering is unverified for this integration. Loader, syntax, HTTP unit
checks and actual earlier Godot GPU observations have different scopes. No
human observation or timed cleanup test has been performed by this work.

The original speed/acceleration/angular rate failures, about 6.003 mm sampled
floor penetration, continuous collision uncertainty and runtime event semantics
remain open. The next motion work must reduce these measured defects and extend
the native authoring path beyond this A/B fixture. No new model was trained,
no held-out prompts were consumed and all 14 release capabilities remain
unapproved. The full project goal remains active.
