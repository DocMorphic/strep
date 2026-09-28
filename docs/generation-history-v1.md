# Generation history travels with joined and edited assets

New Studio packages now include `generation-sources.json`, a verified index of retained source generation history. A transition can retain several donors, and a regenerated section can retain another raw model result. The existing primary-source link alone did not expose that full bundled history.

`motion_origin_inventory.py` indexes canonical source motions under `source/`, `input/`, `following/` and `generation/`, including their nested history. It verifies saved origin manifests and direct generation records against the local motion bytes. Duplicate copies share a record while keeping every relative location. Identical motion bytes with different generation records stay separate. Missing legacy metadata is explicitly unavailable; damaged existing metadata is rejected. Historical absolute paths in records are never followed.

The index applies to retained source snapshots. It does not assign an ancestor's style or capability profile to a joined, retimed or regenerated result, and it is not a contributor timeline or a complete external lineage. Original request/profile files remain available through relative references and hashes. New result metadata exposes the index URL and counts; the ZIP includes it and explains its scope. Existing packages are unchanged.

Thirty-five focused origin/inventory/character tests pass in13.20 seconds, with four existing Torch deprecation warnings. The real workflow in `reports/generation-history-export-v2` submits three Studio jobs through the local API:

| Job | Result | Distinct source records | Retained locations |
|---|---|---:|---:|
| 20260928-031759-06eb04ce | Low-profile source transfer | 1 | 1 |
| 20260928-031815-5d1de71d | Transition from high-profile to low-profile source | 2 | 3 |
| 20260928-031826-b8ebef83 | Trimmed and retimed transition | 2 | 2 |

Downloaded indexes, source/metadata bytes and ZIP contents match their recorded hashes. Both donor records survive the descendant edit. Godot verifies all455 poses across the original source, new source,134-frame transition and81-frame descendant. This verifies provenance/export behaviour, not transition quality or profile-following motion. The first harness attempt omitted the API's required local Origin header and received403 before creating a job; that failure remains in `generation-history-export-v1`. The corrected client uses the existing API contract; no server restriction changed.

A separate read-only compatibility check, `reports/generation-history-legacy-v1.json`, accepts all six completed older prompt-edit jobs. Each retains one verifiable raw generation record and one or two explicitly unavailable source records. No legacy archive was rewritten and no new model inference was run.

The backend changes use the new inventory module and `rig_studio_job.py`. New worker processes pick up the change without restarting Studio. The separate portable installation has not yet been rebuilt with this addition. Every animation-quality and release gate remains open.

## Studio history panel

The Characters workspace now includes a Source generation history disclosure below the result and mapping area. Each distinct source has its original prompt sequence, requested durations, seed, resolved movement profile/rules and retained-copy count. Direct links open the original generation record, movement brief, source files and combined index. The two-source example displays mobility100 and mobility0 side by side; it does not label the current joined motion with either profile. Older packages explicitly identify incomplete history and expose primary-source links when present. Imported reference poses hide the panel.

The browser checks the index and displayed metadata against their stored SHA256 hashes, restricts paths to the selected package, and uses text nodes for record contents. Switching results aborts old requests and invalidates late responses. A damaged source displays an error without substituting another source's details.

`reports/generation-history-ui-v1/verification.json` records seven passing Node regression checks, syntax checks for both bundled scripts,340 unique HTML IDs, and real browser checks of the joined clip, retimed descendant, older primary-only package and reference pose. Keyboard disclosure and navigation were verified; pointer automation did not activate the controls, so pointer behavior is not certified by that session. No browser errors were captured. `studio-history.png` retains the inspected two-column view.

Before rebuilding, the canonical character fragments were reconciled with the live page's existing hand-posture controls. The reconciled build matched the previous live HTML exactly; the new build retains those controls and reproduces the deployed page. The new panel is bundled inline and requires no service restart. The initial Node harness stalled because its delayed-fetch mock also delayed metadata requests; it was stopped and corrected before the final seven-test pass.
