# Contact timing across animation edits

Saved per-interval contact clocks now survive finite clip trims, speed changes,
local pose adjustments and event edits. Joins, loop extraction and motion
mirroring retain those clocks with review targets. Neither path establishes
anatomical correctness, successful contact or animation quality.

## Using the saved conditions

In Studio, reopen **Contact targets** on a trimmed or marked clip to recover
its surviving intervals and saved fitting options. **Saved contact timing**
links to the record for the selected version. These files are included in the
animation package, together with the immutable input and implementation archive.

Each active version has a local `contact-spec.json` and a
`strep-mesh-contact-timing-v1` record in `contact-timing.json`. The record binds
the actual GLB, complete local draft and separate fitting options. It also
records the operation, immediate parent hashes and surviving source-interval
indices. Both `requires_review: true` and `quality_approved: false` are mandatory.
Source selection verifies the published record hash; deleting or changing it
rejects selection rather than resetting its clocks. Prepared workers bind and
verify their timing records and any review-target files before exporting.

| Edit | Timing and target treatment |
| --- | --- |
| Trim, speed or local pose | Retain fixed world targets; map half-open intervals to the resampled frame clock; drop empty intervals and remap explicit override indices. |
| Event markers | Preserve GLB bytes, intervals and options; marker confirmation remains separate from contact quality. |
| Transition | Retain source interval, clock and provenance; multiply source-target contributions by the new blend weights and align the second clip's world targets. |
| Loop | Retain clocks, provenance and weighted targets separately for each contributing cycle placement in both the single and repeated outputs. |
| Mirror | Retain original target, patch identity and clock; add a proposed reflected point and require anatomical patch remapping. |

Explicit choices that equal the default still survive. Empty trims retain an
explicit empty override map. Chained edits use each immediately selected
version's records, not an older job-wide draft. Original files remain unchanged.

Retimed intervals use the exported discrete frame clock. This can change a
hold's start or end by resampling and does not prove continuous contact.
World targets may become incompatible with a pose or speed change and must be
inspected and fitted again under the selected timing conditions.

Blended, cycled and mirrored targets are **review records**, not executable
fixed-target conditions. The output does not receive an active timing/draft
pair solely from those records. In particular, a source left-palm vertex set
cannot become a right-palm patch merely by reflecting a point. Review and
re-author the correspondence, geometry and schedule before fitting. The
finite playback fitter still rejects periodic clips; this change does not
add mixed-clock periodic fitting or moving contact targets.

## Evidence and limits

A portable synthetic weighted-skin fixture has forty frames and three fixed
proxy targets: authored keys, a held interval, and an explicit authored-key
override. Nine actual Studio jobs completed: authored contact conditions
without fitting; trim/speed; a second trim/speed; an empty trim; event markers;
marked-clip trim; transition; joined-clip loop; and motion mirror. Every saved
active variant reopens with the exact options. Weighted transition intent is
checked against the independently enumerated source-frame contributions;
cyclic and reflected targets remain review-only. All original source files
stay unchanged, and every ZIP entry except the added README matches its local
source bytes with passing CRC checks.

All 739 packaged files pass those byte checks. The final model-free workflow
passes 1,625 Python checks and fourteen explicit JavaScript suites, following
51 focused checks and 37 existing asset-dependent clip/transition/loop/event
checks. A preceding 1,624-check run passed before the deleted-record regression
was collected; that observation retains its earlier scope.

The final observation is retained locally under
`reports/mesh-contact-edit-evidence-v2/`. The earlier v1 remains an immutable
observation before the deleted-record guard and common clock-module archive
addition. These are software propagation checks on a synthetic fixture, not
new motion-generation or real-character contact experiments.

Portable tests cover chained retiming, dropped intervals, markers followed by
trimming, weighted joined-loop targets, actual mirror export, changed prepared
geometry/drafts/timing/reviews, missing worker bindings, changed published
records, attempted approval and deleted-record rejection. Existing editor
DOM/source checks remain separate from browser/GPU verification.

No new inference, training, seed, formal held-out use, engine import, rendered
preview, submitted human review or timed cleanup result is supplied here.
Earlier crawl failures remain unchanged. General action, scene/partner,
style, rig transfer, engine and release review requirements remain open.
