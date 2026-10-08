# Longer lift: first completed contact fit

The longer lift fit completed after two retained memory-guard failures. The
unchanged Kimodo output remains the source; this experiment fits contacts around
that clip rather than training the checkpoint. The complete source and candidate
retain their six-second clocks and the explicitly authored anatomical grip
points on a 40 cm box. This source setup differs from the earlier wrist/palm
baseline and must not be presented as an unchanged replay of its contact errors.

V17 uses the existing sparse skin operator, 32-frame object playback checkpoints,
six outer optimization stages and unchanged populations/bounds. It completed in
765.812 seconds, peaking at 1,028,493,312 bytes of process-tree RSS under the
one-hour / 7 GiB tree / 600 MiB available-memory guard. Native results report
approximately 21.8/21.9 mm maximum grip error. That meets the authored 30 mm
contact tolerance but **does not meet the solver's approximately 5 mm working
target**. A finished optimization is not proof that all requested bounds hold.

## Independent imported playback

Actual Godot 4.7.2 reimport sampled each complete clip at 240 Hz plus its exact
exported keys: 1,601 poses per actor and object, including 537 contact samples
per hand over the authored 2–4 second interval. All 18,056 vertices, 36,108
triangles and eight skin influences were retained and identity checked.

| Measurement | Anatomical source | Fitted candidate |
| --- | --- | --- |
| Left grip maximum error | 390.057 mm | 21.797 mm |
| Right grip maximum error | 401.340 mm | 21.931 mm |
| Failed 30 mm samples per hand | 537 / 537 | 0 / 537 |
| Floor maximum vertex depth | 8.997 mm | 0 mm |
| Floor samples above 5 mm | 1,294 / 1,601 | 0 / 1,601 |
| Box maximum vertex depth | 0 mm | 1.369 mm |

Both candidate contacts first meet their tolerance at the exact authored start,
2 seconds. Provisional normal diagnostics measure 14.270° and 13.786° maxima
against a 15° diagnostic screen; this is not anatomical grip approval. Imported
skin displacement stays below 100 µm on both clips without applying the optional
precision derivative. Point and vertex measurements do not measure triangle
interiors or establish that the box center lies outside the character volume.

The engine producer and independent input/method replay completed. A private
post-run summary writer then failed because it requested `scene_id` where the
row field is `id`. That wrapper failure remains intact; a separate verified
summary references the completed producer. The expensive engine study was not
rerun or relabeled to hide the wrapper error.

## Remaining failures

The fitted candidate has up to **615.699 mm joint displacement** from the raw
motion and 24.613° local rotation change. Review flags include
`pose_change_above_22cm` and `LeftHand_surface_slide_regression`; the latter is an
estimated surface support statistic, not an authored support contact. The fit
also adds up to 1.212 m/s joint velocity and 10.001 m/s² acceleration. These
measurements prevent a claim that meeting grip points made the action realistic.

The first full imported triangle/volume/floor audit stopped after 509 of 1,601
source samples when system available RAM fell below the unchanged 600 MiB guard.
Its partial output remains a failure. A fresh retry preserves the complete source
and candidate clocks, populations and geometry limits; its eventual outcome must
be recorded explicitly. Natural motion, attachment,
force balance, independent animator review, held-out performance and all fourteen
release capabilities remain unapproved. The next correction needs to address
the missed tighter grip target and excessive motion distortion without relaxing
the current contact or geometry limits.
