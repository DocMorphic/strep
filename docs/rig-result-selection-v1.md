# Studio correction selection

Studio previously opened the corrected version whenever a contact candidate existed, including candidates whose numerical audit had rejected them. Joint-target jobs likewise opened the edited candidate when their explicit screen status was rejected. This could make a subsequent edit start from a known failed result without the developer choosing it.

The character workspace now opens the retained input for failed contact and joint-target candidates. Failed candidates and their repeated cycles remain selectable, with `Failed checks` in the version menu and preview label. The notice identifies what is currently displayed. An explicit user selection is respected; candidates remain editable for cleanup. The original input is not presented as approved.

Candidates marked `provisional_pass` or `numerical_screens_met` still open as before, with a `Numerical screens met` label and an explicit remaining-review notice. Missing or unknown correction decisions do not automatically select the correction. Event-only descendants retain their inherited rejection on both finite and repeated views; no clean source is invented when none exists. Returning to the reference pose clears the selection notice.

The pure presentation policy lives in `scripts/rig-result-selection.js` and is bundled by `build_desktop.py` into the served desktop. Canonical character sources were edited and the generated desktop rebuilt. No backend restart, solver changes, saved-result mutation or GLB rewrite was required.

Six focused Node cases pass, covering failure, numerical pass, joint edits, event inheritance, missing decisions and ordinary edits/cycles. The desktop source/build reproducibility test also passes. Browser checks on four existing jobs confirmed the actual options, defaults, labels and input-bound editing panel. Ten existing animation files retained their hashes. The screenshots, job snapshots, test record, final source hashes and frozen-background-worker check are retained in `reports/rig-result-selection-v1`.

This change handles explicit contact/joint decisions and inherited correction status. It does not infer a new acceptance decision from unrelated diagnostics, implement a universal quality score, or certify the selected source. Broad geometry, action, animator and held-out release checks remain open.
