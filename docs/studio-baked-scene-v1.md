# Studio saved-scene export

Studio now connects a completed prop animation bake to the finite
[saved actor/prop scene player](baked-scene-runtime-v1.md). In Character Studio,
choose a completed bake, open **Export saved scene**, bind that selection, and
choose **Export & verify saved scene**. Refresh exports and review the completed
job to download its standalone Godot project and verification report.

This is a separate job. The original selected motion and completed bake remain
unchanged. The exporter reuses saved prop tracks, original actor resources,
embedded root motion, scene placement and original event/contact references.
It does not run prop physics again or generate new motion. Actors hold their
original end pose when the baked clock ends on a later physics boundary.

## Source binding and worker

The request contains exactly a completed bake job ID and its result SHA256.
The server validates the full upstream bake before preparation. Preparation
copies the complete baked ZIP and archives all exporter and upstream method
hashes. Request, selected result, ZIP, original decisions and archived methods
are checked before and after packaging and the headless audit. An interrupted
or failed stage preserves the input and failure state; it exposes no completed
download. A second run cannot reuse an already started job.

The worker uses the existing pinned console Godot binary and shared worker
lock for its headless audit. The loopback server's origin, content-type,
body-size and active-worker checks also apply. There are no dependency changes,
model downloads, sampling or training. The exported package remains a finite
saved animation scene, with the integration limits documented by its player.

## Verification and downloads

Completed serving verifies original ZIP bytes, complete package and artifact
populations, archived SDK hashes, recomputed runtime configuration, exact audit
request, original Float64 clocks and every recorded actor/bone/prop/root/event
observation. Mutable completion receipts alone cannot approve a changed file:
rehashed changes to assets, helpers, runtime choices, observations, clocks or
conditions still reject. Serving reads saved evidence; it does not launch an
engine or query production skin geometry.

Only these five completed downloads are exposed:

- `runtime/baked-runtime.zip`: standalone source-preserving Godot project.
- `runtime/result.json`: package scope and file/method hashes.
- `audit/result.json`: saved playback and startup verification.
- `request.json`: original selected bake and result binding.
- `result.json`: Studio job result and original bake conditions.

Source snapshots, archived implementations and raw engine observations remain
private local report files. The UI rejects stale bind/review replies, prevents
duplicate submissions and checks the exact download population and paths
before showing links. Binding or exporting another source does not replace
the developer's current character clip.

## Evidence and limits

The review presents saved playback separately from the original scene/root,
physical timing, sampled grip/floor and default 30 FPS import results. Existing
failures remain failures after a successful export. No live prop physics,
animation-quality approval or release approval is inferred from these checks.

Offline Python tests use explicit upstream-job and engine doubles; Node tests
use a DOM/API double. Actual generated saved-scene engine evidence is recorded
separately. No live HTTP/browser, rendered/GPU evidence, production skin or
anatomical query, new model sampling/training, human ratings/cleanup or held-out
release approval is created. Studio visual behavior and motion quality remain
unverified under those tests. All full-project release gates stay open.


Final frozen validation passes **61 Python tests**, including **29 new
saved-scene job contracts**, and four offline Node suites. The generated Studio
page matches its editable sources, source/copy hashes remain unchanged, and
the new Python/Node suites are the only changes to the parsed CI workflow.

A generated moving-root/non-grid worker fixture uses actual native resources
and the pinned headless engine. It completes **495 pose-query frames**, **24
confirmed callback observations** and twelve malformed binding rejections;
exported startup binds and all five completed downloads verify. Its upstream
Studio selection/manifest boundary is explicitly doubled, while the original
source bake and actual saved-scene audit remain real immutable local evidence.
The original actor end hold is `0.007333405812581351` seconds. Actor/root and
prop component errors are `2.593656560634372e-7` and
`2.2721984693774289e-7`, below the unchanged `3e-5` limit. The owned engine
process exits zero with a clean log; all owned commands are terminal and the
worker lock is free afterward.

Original exact physical timing still fails by **6.25 ms**; default 30 FPS import
still fails. The fixture's sampled grip/floor screens pass only their stated
software bounds. No realistic grasp, partner response, continuous collision,
production-rig generalization or release acceptance is inferred. The earlier
completed player study and existing source regressions remain historical
evidence and are not overwritten by this follow-up.

Local immutable SHA256 receipts:

- Final workflow/engine study: `7dbaa4386882b10791a9a37e9bfd43013719691de7f8d67b1b304eeb12c35450`.
- Frozen source checks: `b5ff5fe1cf369a63a4047ebd170614f48ebe8183c59c3e9bf6fe5cc52c9c1979`.
- Parsed workflow proof: `e77209904998593afee2dcefcdcc596c3b61e2c22bc480b46ff039399ed03f07`.

Hosted CI for the preceding saved-player commit is queued at the recorded
snapshot; hosted success for this update is not claimed.
