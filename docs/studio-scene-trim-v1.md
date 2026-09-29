# Shared scene trimming in Studio

Scene interactions now has a **Trim shared scene** panel with first/last frames, playhead shortcuts and a saved draft name. It creates a separate result containing every actor and prop. The original scene remains selectable. Completion opens the trimmed candidate with its animation ZIP, event file and prior-event/contact context available as downloads.

The new immutable trim worker snapshots native motions, actor/prop exports, events, license and implementation. It checks revisions before preparation and input hashes before running. Point/region contact measurements and actor/prop vertex diagnostics are recomputed for the new clock instead of copying old whole-clip metrics. Partner collision, dynamics and naturalness remain explicitly unapproved. Re-trimming uses the result's preserved event file rather than replacing it with generated contact markers.

Paired scenes without props are supported through an explicit source-reader option. Object-release jobs retain their existing requirement for an object. The server keeps its existing one-request-at-a-time policy; a running numerical job causes a trim submission to return a busy response. Drafts and exact job identifiers survive reload, unavailable jobs are not silently restarted, and unsaved scene-placement edits are rejected.

## Retained execution evidence

The actual metadata, preparation, worker, contact evaluation and package functions ran on two saved scenes, independently of HTTP:

| Source | Trim | Actors / props | Retained events | Verified snapshot files | Godot pose observations |
| --- | --- | --- | ---: | ---: | ---: |
| Existing seed-11 high-five | 20–100 | 2 / 0 | 6 | 24 | 211 |
| Existing seed-11 object release | 90–150 | 1 / 1 | 1 | 23 | 160 |

Both preserve exact native array slices and actor placement. Five bundle/download routes per result pass local path checks. The release's earlier grasp is retained as context and not replayed. The event-file identity is checked when loading each result as a new trim source.

All **371 Godot pose observations**, seven authored events, fourteen callback-mutation rejections, shared-clock playback, reverse event ordering and unload checks pass. Maximum actor matrix discrepancy is below 7.47e-7 and object discrepancy below 1.93e-7. This confirms package playback, not interaction quality. Exact methods, checks and hashes are retained under `reports/studio-scene-trim-v1`; the review collections are `scene-trim-jobs/studio-trim-paired-v1` and `scene-trim-jobs/studio-trim-release-v1`.

Twelve Python tests cover source restrictions, revision/range validation, tampered snapshots, a real pair worker, repeat-trim event binding, allowed paths and desktop build preservation. Two Node component checks cover the new trim editor and existing contact editor, including busy responses, range validation, playhead controls, draft recovery, unavailable storage and unsaved-placement rejection. The generated desktop page matches its source templates.

The local server was safely refreshed and its listening socket verified while the independent expanded-window solver remained live. No HTTP dispatch, live browser interaction or visual layout check was performed. Native-SOMA and complete baked-clock limitations from the [trim implementation](scene-trim-v1.md) remain; speed changes and human quality review are still open. All fourteen release capabilities remain unapproved.
