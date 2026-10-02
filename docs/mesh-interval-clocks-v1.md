# Individual mesh-contact interval timing

Finite-clip mesh-contact jobs can now combine authored-key targets and full-frame
holds in one clip. For example, a chosen foot target can hold while a chosen hand
target applies at specific keys. These are authoring conditions, not inferred
contact truth. This removes the single-clock limitation of the initial
[Studio playback fitting integration](studio-mesh-playback-v1.md).

## Authoring and saved meaning

In Studio's mesh-contact editor, choose **Interval timing** before adding or
updating an interval. **Use default timing** follows the job's default; the other
choices explicitly request authored frames or a hold through each frame. The
interval list displays the effective timing. Change an existing interval with
its **Edit** button and save it with **Update interval**.

The held interval remains half-open: from the start-frame timestamp to the next
frame after the last selected frame, intersected with the animation's available
duration. Keys, channel midpoints and 120 Hz samples are checked. This does not
establish contact at every instant, rigid patch orientation, surface coverage,
forces, balance or anatomical correctness.

The contact draft's geometry and schema are unchanged. The separate
`strep-mesh-playback-fit-v1` options may include `contact_clock_overrides`, a map
from canonical zero-based interval-index strings to `authored-keys` or
`frame-hold`. Unlisted intervals follow `contact_clock`. Options bind to the
exact input and complete saved draft before launch; unknown indices and clocks
are rejected. The original five-field options remain accepted.

Browser preferences also record the contact list. Reopening a changed contact
list cannot apply stale index choices; deletion remaps surviving indices, and
deleting a patch removes its interval choices. Choices remain separate from the
geometry draft. The legacy frame/cycle method cannot apply individual timing
choices: submission requires explicitly clearing them to default or selecting
the across-clip fitter. Periodic clips still reject across-clip fitting rather
than losing cycle closure.

Reopening the input or candidate of the completed contact job restores its
hash-bound saved options even in a fresh browser. A subsequent
[editing integration](mesh-contact-timing-edits-v1.md) preserves active choices
through trim, speed, pose and event edits. Transitions, loops and mirrors retain
clocks with review targets; they do not turn those targets into fitted contact
conditions. The original job remains retained, and anatomical/timing review is
still required.

CLI callers may pass `--contact-clock-overrides timings.json`, for example:

```json
{"0": "frame-hold", "2": "authored-keys"}
```

Those indices must exist in the supplied contact draft. Individual choices
require `--feasibility --guarded-trials --playback-guards`, and are saved in the
request, both trial phases and final solver summary. Each decoded contact row
reports its own effective clock. Sampling, frozen input-passing protection and
the final exported contact gate all use the same saved choices. A passing raw
key or optimistic solver status cannot override a failed held-contact export.

## Evidence

An actual synthetic seven-frame Studio worker completed with two patch targets,
default authored frames and a frame-hold choice for the second interval. Under
the declared floor/contact budgets 3/8, the contact optimizer exhausted its
budget. Sampled geometry passed but selection remained rejected, with the exact
input retained and quality unapproved. All 125 ZIP entries excluding the added
README match their source bytes, and CRC passes.
Both exported variants also reopen with the exact saved options.

An independent observer inspected three unchanged development crawl inputs and
their original wrist/shin proxy drafts. Only the left-shin interval explicitly
uses frame-hold; the other three keep authored keys. These are different timing
conditions, not an equal-task comparison or a revision of the earlier studies.
The observer enumerates clocks without calling the fitter's layout helper and
reconstructs full-mesh centroids from decoded poses.

| Existing asset | Left-shin hold error | Other three key errors | Failed intervals |
| --- | --- | --- | --- |
| CesiumMan | 15.502 mm | 40.684 / 140.697 / 102.596 mm | 3/4 |
| Quaternius female | 31.561 mm | 47.586 / 187.503 / 147.937 mm | 4/4 |
| Quaternius male | 35.356 mm | 48.851 / 184.040 / 148.640 mm | 4/4 |

Each hold has 18 samples; each other interval has three keys. The independent
81 contact-pose observations cover 556,200 reconstructed vertices with zero
reported centroid disagreement. Separate 701-sample-per-clip floor checks still
fail: maxima 7.957 / 48.343 / 88.755 mm, with 236 / 701 / 701 failed samples.
No real-character correction was run or relabeled as solved.

Portable checks cover strict index validation, mixed half-open timing, full-mesh
value and derivative parity, interval-specific protection, phase propagation,
actual export rejection, source retention, read-only Studio inspection and
option/archive binding. DOM checks cover individual edits, deletion/remapping,
reopening, stale contact lists and explicit legacy rejection. They do not render
a browser or certify animation quality.

All 116 focused Python checks pass, followed by the final model-free workflow:
1,612 Python checks and fourteen explicit JavaScript suites. A preceding
1,611-check run passed before the saved-choice reopening fix; it retains that
earlier scope.

Final local immutable evidence is under `reports/mesh-interval-clocks-evidence-v2/`.
The initial implementation observation remains separately under `...-v1/`.
No new inference, training, seed, formal held-out use, engine/GPU rendering,
submitted human review or cleanup timing was added. Reviewed anatomy and intended
timing remain necessary, along with the full project-wide action, scene/partner,
style/edit, rig, loop/transition and engine-release requirements.
