# Paired corrections in Studio

The scene workspace now has a **Correct partner overlap** panel. It loads the saved scene revision, lists editable joints separately for each actor, accepts a range in seconds and an original-relative rotation budget, and exposes the exact authored contact intervals as protected poses. The user selects one to eight joints per actor. Five explicit control knots span the chosen range; action names do not determine the controls.

Drafts belong to the scene revision. Submission rejects unsaved placement changes and invalid ranges or selections. A stored job ID is observed after reload; missing jobs and polling failures never automatically launch replacements. A completed job selects the candidate only when the worker reports an accepted local step. Otherwise, it opens the retained source and states that no correction passed.

## Worker and review

`scene_pair_job.py` snapshots both actor GLBs, native review metadata, exact events/contact windows, licensing and worker implementations. Its mutable processing state is separate from the immutable prepared request. It acquires the existing local worker lock, runs fitting, independently replays the exports, checks Godot import and then publishes a before/after collection. Confirmed worker exits become terminal failures. Studio also observes standalone `study_scene_pair_fit.py` processes from this workspace so another heavy request cannot overlap them.

`publish_scene_pair_fit.py` requires matching fit, replay and engine evidence. It checks export identities, the source geometry index and samples, candidate geometry and the selected trial's replay. Source actor IDs are preserved. Exact GLBs are copied into the collection; editable native motion is reconstructed and compared against the actual GLB skin at every native frame. Contact predictions are inherited, not relabeled as detected contacts. Exact event files remain alongside each version for subsequent timing edits.

Collections appear under the existing `scene-region-jobs` discovery mechanism. Original and failed files stay in the paired job folder. The publication does not grant release approval and does not yet add a new portable shared-playback ZIP. Imported GLBs, editable scene bundles and the recorded original/candidate contact timing remain available.

A finished standalone study can enter the same review pipeline without rerunning fitting:

```powershell
.venv\Scripts\python.exe scripts/scene_pair_job.py reports/paired-edit-jobs/curve-controls-trimmed-v1 --completed-study reports/scene-pair-fit-v2 --label "Paired scene correction"
```

This requires the exact original prepared request and unchanged inputs, a terminal completed study and a fresh destination. Independent replay, engine import and publication still run. It is not a way to bypass those checks.

## Verification and running study

Eighteen focused Python tests pass for request snapshots, exact event metadata, direct local-handler routes, origin and busy checks, worker dispatch, failed-worker preservation, completed-study identity checks, publication evidence gates, standalone process identity and reproducible desktop builds. Five offline Node checks pass for the paired controls and existing fractional preview, trim, region and feedback workflows. The new pure publication/activity checks and paired editor check join model-free CI. A label-shadowing regression found during refactoring was fixed before publication.

The service was restarted on its existing loopback port with the new controls. Port ownership, source routes and the reproducible build were checked. No browser rendering is claimed. `reports/scene-pair-studio-setup-v1.json` retains the local setup evidence.

The first real study completed all 126 source geometry samples and solved 4,287 surface rows, but stopped before export because a logging statement supplied `status` twice. That failed run is preserved as `scene-pair-fit-v1`. `scene-pair-fit-v2` repairs the log and reuses geometry only after checking the exact input hashes, all dependency snapshots, the unchanged extraction function and the complete time population. Every recomputed linearization array and proposed control value matches the first run exactly.

The full step fails exported motion checks. The half step subsequently completed local mesh validation, independent replay, engine checks and real Studio publication; see the [completed review](scene-pair-fit-review-v1.md). Its tiny penetration improvement leaves 37 of 126 sampled times above 5 mm. The UI/worker tests do not establish visual quality. All 14 release capabilities remain unapproved.
