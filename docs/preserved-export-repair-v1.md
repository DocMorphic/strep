# Preserved-pose export correction: two passes and one retained regression

This isolated three-case development experiment combines exact held-pose restoration with [geometry-limited export headroom](contact-breadth-wave-v1.md#geometry-limited-headroom-both-waving-seeds-pass). It tests both waving seeds and crawl seed 22. It preserves the original eight-case study and does not change Studio defaults or approve release quality.

## Why restore held poses first

The original crawl-22 repair stopped on a locally constant global-speed constraint at **frames 8–8.25**, outside its edit window of 10–109. Its normalized native slack was -7.1882070e-8. Restoring the original source pose arrays at locked keys makes this row exactly zero, matching the source. The small violation came from reconstruction drift in a region the local solver could not edit.

The source's decoded global acceleration maximum is at frames 10.75–11.25, inside the editable interval. Wholly held acceleration stencils reach only 84.684698 m/s², below the 113.579188 ceiling. Therefore this diagnosis does **not** establish an unavoidable exported acceleration conflict with the held source. Representation differences remain relevant, but this case's acceleration error occurs in editable motion.

The read-only diagnosis is retained in `reports/contact-breadth-v1/crawl-22-locked-rate-diagnosis.json`, binding its implementation, source/seed motion and GLBs, preservation helper and original solver record. No replacement motion was written by that diagnosis.

## Combined method

The subsequent experiment restores source pose arrays at all locked keys, retains free fitted keys exactly, exports that restored seed, then measures its actual point-phase and global-rate failures. Only those failed groups receive additional search headroom, bounded by horizontal motion. The source still defines all original limits and edit budgets. Every proposed root step checks all original nonlinear constraints and preserves previously passing native rows. Serialization and decoded export are audited independently.

This source restoration is appropriate for these original, non-warm-start local fits. Production integration must use the correct held seed when a warm start is supplied; it must not erase intentional edits from an earlier clip.

| Case | Original exported contact screen | Outside-window decoded pose/skin difference | Actual Godot observations |
| --- | --- | --- | ---: |
| Wave seed 11 alternative | Pass | Exactly zero at all 80 observations | 284, pass |
| Wave seed 22 alternative | Pass | Exactly zero at all 80 observations | 284, pass |
| Crawl seed 22 alternative | Fail: new release-acceleration excess | Exactly zero at all 80 observations | 284, pass |

Both waving repairs retain their prior passing pin, floor, point/global rate results while removing the outside-window drift. All three variants have zero floor penetration/added depth, passing pin samples and empty body-regression flags. These checks do not establish naturalness or force support.

## Crawling failure stays visible

The restored crawl seed still exceeds the approach/global acceleration limits. Two accepted root proposals, with maximum root change **1.330169e-6 m**, lower approach acceleration to **107.758434 m/s²** (cap 107.769558) and global acceleration to **113.567845 m/s²** (cap 113.579188). Pin error remains within 5 mm, at 4.760806 mm maximum.

However, release acceleration rises to **89.81728132688808 m/s²**, above its original 89.81727971614012 ceiling by **1.610748e-6 m/s²**. Release was passing before this correction. The unrounded nonlinear calculation preserves original rows, but the serialized full proxy has minimum normalized slack -4.105334e-10 and the actual GLB fails. The result is rejected; fixing two groups does not justify moving the failure to another group. No acceptance tolerance is added.

The third proposal attempt cannot improve the residual strengthened search target. That search target is separate from the original acceptance limits. The next method needs export revalidation between correction steps and accumulated protection for previously passing exported groups, rather than relying exclusively on native-row preservation or a single final export.

## Retained evidence

`reports/contact-breadth-v1/preserved-export-repair-v1.py` and `preserved-export-repair-v1/` retain the declared three-case protocol, restored seeds, all solver trials, final alternatives, full audits and engine records. All **852 additional actual Godot observations** pass, including requested boundary events, callback protections, forward/reverse playback and unload. Native BVH/GLB and eight-weight skin checks pass. Motion-quality approval remains false for every variant.

The original study and source files remain unchanged. Both batch workers subsequently completed successfully; their frozen results are reported separately. No new unit-test run, human review or cleanup time is claimed. Exact held-pose preservation is supported by the earlier 17 isolated tests and the actual export checks here; production integration and broader joint-pose correction are still pending.
