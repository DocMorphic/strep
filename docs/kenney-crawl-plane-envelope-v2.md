# Crawl plane-envelope correction attempt

The first actual [minimum-envelope](plane-envelope-guidance-v1.md) crawl trial
cleared the previous surface-row capacity failure. It retained the complete
2,017-time ground clock and all 1,029 triangle-referenced vertices. The same
63 controls permitted root translation and six arm/forearm/hand rotation tracks,
including explicitly editable clip boundaries. Joint movement remained bounded
at 22 cm, rotations at 30 degrees, and ground penetration at 5 mm.

The worker stopped at the unchanged 900-second execution limit: 900.406 seconds
recorded, peak process-tree RSS 1,770,913,792 bytes. All 899 sampled resource
observations and archived worker/method bindings replay. This is an interrupted
attempt, not a completed optimizer or a corrected asset. Its final fit result
does not exist; saved processing receipts are historical, not live-job status.
The terminal guard record governs that status. Original motion remains selected.

Two primary iterations finished without an accepted step. The trial retained
29 fully exported and geometry-audited probes: its original start and 28 changed
proposals, including probes from the interrupted third iteration. Every probe
still failed all 2,017 ground times. The strongest changed probe reduced peak
penetration from **263.015 mm to 242.172 mm**, but failed the original motion caps
and was rejected. Improvement alone did not authorize selection.

A separate diagnostic reconstructed all 5,138,655 native conditions and
2,482,110 source-rate conditions across the 29 exports. It matched the recorded
merit values without changing the original cap population or tolerance. The
original start alone passed native constraints. All 28 changed proposals failed
rate conditions: 942 position-acceleration, 213 angular-acceleration, six
position-speed and three angular-speed failures across the exports. These are
repeated per-probe observations, not unique joints or causes. The maximum
normalized excess was about 0.0000249; small excesses still fail unchanged caps.

The diagnostic uses separate vector arithmetic but shares the source sampler,
edit layout and original cap builder. It is not independent motion validation.
Its geometry figures summarize producer receipts rather than independently
recomputing mesh decisions. The diagnostic's first version failed on array
indexing; its failed worker and resource record are retained. The corrected
version completes, with all 125 resource observations replayed.

The next controlled attempt enables three existing measured decoded-restoration
steps. The previous attempt used zero. This changes proposal repair, not motion
caps, acceptance limits, rig geometry, clock population or selected asset. It
does not establish that quantization alone caused the failures. Contact intent,
balance, transitions, engine playback and human cleanup remain unverified.

Local evidence: `reports/kenney-crawl-floor-fit-v2`,
`reports/kenney-crawl-proposal-diagnostics-v3` and associated guard/resource
records under `reports/central-hand-physical-v1`. Failed and interrupted raw
results remain local and immutable. No release capability is approved.
