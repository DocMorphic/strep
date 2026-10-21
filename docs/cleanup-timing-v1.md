# Source-bound cleanup timing in reviewer packets

The review form previously accepted typed active editing seconds without a timing trace. Newly built packets now include an optional local cleanup stopwatch. The reviewer starts it only while editing the downloaded clip, pauses for breaks and playback, attaches the edited GLB before finishing when applicable, and exports the timing trace separately from the ratings. The timer never fills an outcome, operations, ratings or human attestation. Legacy manual-time reviews remain compatible.

Each session binds the packet and manifest hash, exact neutral clip and GLB hash, reviewer identifier and developer/independent role. A positive optional time limit is selected before Start and locked for the session. Only explicitly opened and closed intervals contribute to active seconds; pauses do not. Switching clips closes the current interval and keeps separate drafts. Resume retains fractional seconds and the original policy. Finish freezes the timer, and **Use measured time in review** copies only the seconds and optional limit.

Reloading a page while its timer is running cannot establish when editing stopped. The restored session records that interval as interrupted with unknown duration. It excludes the unknown interval from its partial total, permits a diagnostic export, and prevents that total from replacing a complete review duration. An edited file is fingerprinted locally; its binary is not uploaded. The reviewer must retain the file for later verification. Use one timer tab per reviewer and clip. The timer measures reviewer-designated intervals, not editor activity; identity, actual editing and independence remain human attestations.

`audit_cleanup_timing.py` independently replays the closed intervals and rejects nonfinite/reversed/overlapping clocks, missing or duplicate fields, changed sources, inconsistent sums and false completeness or approval claims. It binds and rechecks all input files. With a saved review, it requires the same reviewer, role, clip, complete active duration and limit. A completed cleanup also requires the actual edited, self-contained GLB matching the saved hash and byte count. Abandoned and time-limited attempts remain eligible evidence; overrun is reported rather than hidden. The auditor verifies bindings and timing arithmetic, not animation quality, that edits occurred, or that a reviewer reached the rubric.

```powershell
reports/model-free-ci-v1/env/Scripts/python.exe scripts/audit_cleanup_timing.py path/to/reviewer-packet path/to/cleanup-timing.json --review path/to/saved-review.json --edited-glb path/to/edited.glb --output reports/new-cleanup-replay.json
```

Omit `--edited-glb` for an attempt with no saved edited artifact. Omit `--review` to inspect a trace without matching it to ratings. Existing output reports are preserved. The example uses the locally available environment without Torch; normal setup still follows the repository's dependency instructions.

## Verified delivery

Sixty-six Python checks pass in the checkout and an asset-free fixture without Torch. Seven Node stopwatch checks exercise real control callbacks with synthetic clocks, pauses, clip switching, finished sessions and interrupted recovery. The existing actual packet-form regression still passes role separation, save/reload/export, N/A and manual cleanup behavior. Synthetic checks are not human evidence. The model-free inventory is 411 Python modules and 41 Node suites; CI workflow fields, dependencies and permissions are unchanged.

A fresh developer packet preserves **all 65 clips and contexts** from the existing first-round independent packet. The original packet and condition key remain untouched. All 580 packaged files and ZIP members match their saved hashes; HTTP verifies all 65 GLBs and seven viewer/runtime files, including the new timer. The live browser renders the grey character and timing controls without console errors. Playback and clip switching with no timing session leave zero active seconds, **Not performed**, no human attestation and **0/65** saved reviews. No ratings or cleanup trials were created.

The packet and ZIP remain ignored under `reports/cleanup-timing-v1`, with source, transport and browser evidence. Open the locally running developer packet at `http://127.0.0.1:8770/viewer.html`. This is a development review packet covering its supplied 65 clips, not the entire broader population or held-out release evidence. This change generates no new animation and changes no existing motion or solver result. All fourteen release capabilities remain unapproved and the project-wide goal remains active.

## Restored-timer validation (2026-10-21)

The browser previously accepted some invalid saved sessions that the importer
would reject, including a finished timer without closed intervals. It now checks
exact interval/interruption fields, a finite total, portable artifact filenames,
and closed intervals before allowing finished timing to be exported or copied
into a review. A restored open interval cannot overlap earlier intervals on the
same page; clocks on distinct pages remain separate. A new session cannot contain
earlier activity. Invalid storage is left untouched when restoration fails and
cannot supply measured review time.

Five new regression checks fail against the previous source. All twelve timer
checks now pass, along with the existing packet-form and role/identity suites
(14 Node test entries total). A synthetic trace exported by the actual JavaScript
module independently replays through the Python auditor as 1.25 active seconds.
This checks timing interoperability; the fixture is not an animation or human
review. Local evidence is `reports/cleanup-timer-restore-v1/`.

A fresh crawl packet is available at
`C:\wassup\strep\reports\crawl-native-developer-review-timer-v1\crawl-developer-review.zip`.
Its 520 archived members were checked against their hashes. Only the timer module
and package integrity record differ from the launcher edition: both original
clips, manifest, review identity, viewer and remaining runtime files are exact.
The earlier packet is preserved. Extract all files and use **Start Review.cmd**;
use the same browser profile and port to retain ratings. No server or browser was
started for this verification, and live rendering was not rechecked. No human
ratings, cleanup evidence or motion-quality approval were created. The ongoing
numerical worker's bound producer files remained unchanged.
