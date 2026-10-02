# Studio developer correction review

The Scene window now contains **Developer correction review**. It loads the
existing native target-review packet, displays its original grey reference
character and lets a developer record segment decisions, explicit foot-contact
labels, measured cleanup time and correction-specific permission evidence.
Saving a review never starts training or approves release quality.

## Review workflow

1. Expand the panel, choose a saved packet and load it. Select a segment.
   Playback and scrubbing use the original motion's native 30 fps clock.
2. If you authored a correction externally, select its existing native NPZ
   within `reports/` and enter the matching window's starting frame. It must
   contain SOMA77 FP32 rotations and root positions at the original 30 fps;
   no rig conversion or resampling is performed. Candidates are limited to
   32 MiB and segments to 2–300 frames.
3. Inspect an edited candidate in its authoring tool. **The canvas always shows
   the original reference**, even when a different candidate is selected.
   It is not a preview of the edited candidate.
4. Mark planted and free intervals for each foot/toe channel. All channels
   begin unknown. Frame indices are local to the segment and interval ends
   are exclusive. Packing requires complete explicit on/off coverage.
5. Choose accept corrected or exclude for every segment. Acceptance requires
   a packed current annotation, development split, three completed human
   checks, actual measured active cleanup seconds and review notes. Changing
   a candidate clears its contact labels and claims; changing labels
   invalidates its saved pack. Enter zero explicitly only when no cleanup
   was needed.
6. For each accepted correction, provide the responsible rights attester,
   explicit permission, retained evidence paths, obligations and the basis
   for permission. Evidence must exist within project reports or be the
   acquired Kimodo checkpoint's exact `LICENSE` file. A model license alone
   does not establish rights to somebody else's character or correction.
7. Enter your reviewer name or alias and save all decisions. Packs are stored
   under `reports/native-correction-packs/`; separate submissions and receipts
   are stored under `reports/native-correction-submissions/`. Failures are
   retained. Reloading a packet resets the unsaved in-memory draft; this
   version does not restore an earlier submission into the editor.

An all-exclusion review is a valid record. The corpus preparer and reader
still require at least one reviewed training correction. A record-only
validation option changes that population requirement and preserves every
other provenance, contact, rights and reservation check. Human fields are
never filled from elapsed playback or model predictions. Attestations are
human declarations; file checks establish neither legal rights nor identity.

## Verification and limits

The focused CPU selection passes 139 tests, including 21 new offline backend
and handler tests. The new DOM suite checks markup bindings, unknown contacts,
explicit intervals, segment state, changed-candidate resets, required human
fields, all-exclusion saving and stale responses without a browser. HTTP
handlers are called in memory; no live Studio request is used for these checks.

The broader model-free regression also passes all 1,648 Python tests and 15
JavaScript suites, including the reproducible desktop build.

A local API packing canary checks all nine original packet segments, totaling
1,020 frames. Their original GLBs have compatible clocks. Packed rotations and
roots match the selected native windows exactly, and four deliberately constant
alternating contact channels round-trip exactly. These contact labels are
**numerical fixtures**, not reviewed labels. No real human submission, rights
attestation, training admission, optimizer update, new generation or formal
held-out trial was produced. Inputs and run methods are hashed and archived.

The grey reference player preserves the native eight skin weights, uses the
existing grey material override and frames the selected segment. It pauses
when its panel/window is hidden and the tab is hidden. Browser appearance and
GPU rendering have not been verified in this change; offline checks do not
establish that visual result. The existing GPU/model acquisition and native
source prerequisites still apply.

The previous published commit `7404513` passed all four Windows/Linux jobs in
hosted run `37014089567`. This change adds the backend suite to separate CPU
CI and the DOM suite to the model-free UI job. Generated review outputs,
credentials, model weights and character payloads remain local and ignored.

The full project goal remains active. All 14 release capabilities remain
unapproved. Actual reviewed licensed corrections, an evaluated trainer,
learning curves, fresh-process resume, improvement/forgetting comparisons,
broader scene/partner/finger support, rig transfer and human cleanup evidence
remain necessary.
