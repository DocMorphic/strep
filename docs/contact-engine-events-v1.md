# Authored contact events in engine studies

The shared engine helper in `study_export_feedback.py` previously created two fixed probe markers at frames 50 and 70 and assumed a 120-frame clip. Those markers happened to match the kick and several other requests, but do not represent the jump/landing request at frames 85 and 100. Historical playback results using this helper prove playback of the supplied probe events, not correct mapping of every contact request. The original evidence is retained.

The helper now requires the bound contact specification, reads the actual frame count from the motion, and derives start/end markers for every explicit region and segment. Markers retain region and segment identity, use the source 30 fps clock, and are ordered by frame. Inferred or disabled contacts create no authored markers. Invalid clocks, out-of-range, overlapping or reversed intervals fail before engine packaging. This event mapping consumes an already geometry-validated specification; it does not infer that contact actually occurred.

All three tracked callers pass their checked specification. Nine regression tests cover the landing boundaries, single-frame contacts, short clips, multiple regions/segments, empty authored contacts and malformed timing. The model-free CI suite includes these tests (57 Python tests total). An additional 23 support-objective/export-repair tests pass locally, for 80 distinct Python tests across the two runs.

Actual Godot playback with the corrected helper passes for both the retained landing candidate (markers 85/100) and the newly repaired kick (50/70). Each has 284 passing pose observations, correct event order in both directions, automatic playback, callback-mutation rejection and unload. Source motion, GLB and request hashes remain unchanged. Local verification is retained in `reports/contact-engine-events-v1/verification.json`.

This fixes study metadata and strengthens subsequent engine evidence. It does not repair the landing candidate's known pin/rate failures, validate physical contact from event notifications, or approve either animation's visual quality.
