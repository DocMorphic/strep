# Developer observations in the motion viewer

Characters → Review corrected motions → Your review notes now accepts a name or alias, an inclusive frame range, and a written observation. “Use current frame” sets both ends of the range to the displayed frame. “Export feedback” produces a local JSON file. Empty names, empty observations and invalid ranges cannot be exported.

Drafts are stored locally in this browser, separately for each catalog, case, variant and animation hash. Switching versions disables feedback during loading, then restores only that version's draft. Changing a saved animation or review catalog produces a different binding. Browser storage failures are reported; the file export remains available. No note is sent to a server automatically.

The file is a non-blind developer observation, not an independent animator rating or a measured cleanup study. No scores are prefilled. Its metadata explicitly records no independent review, no cleanup timing and no quality approval. Written claims remain the reviewer's observations; validation verifies provenance and format, not their truth.

To preserve a returned feedback file with validation, run:

```powershell
.venv\Scripts\python.exe scripts/developer_feedback.py <local-review-catalog.json> <feedback-file.json> <new-output-directory>
```

The importer requires the exact immutable catalog, case, variant, prompt, seed, clock and animation hash. It rechecks the actual packaged GLB and confines its path to that review package. Altered sources, invalid ranges, independent-review claims and attempts to overwrite an earlier import are rejected. The existing blind-review workflow remains separate.

Validation includes synthetic JavaScript tests for the output flags, source binding and invalid ranges; 11 Python tests for import and rejection; and the desktop bundle reproducibility test. All12 Python tests pass. Browser checks cover blank fields, disabled export, drafting, disabled controls during a version change, isolation of raw-version notes, restoration of the selected-version draft, and an actual downloaded file accepted by the importer. The clearly marked synthetic test file is retained in `reports/developer-feedback-ui-v1/synthetic-import`; it is not human-review evidence. Its draft was cleared afterward. No real developer ratings or independent animator reviews were collected.
