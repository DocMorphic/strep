# Protected-joint acceleration direction

The original fixed direction failed its local-rotation guard at left leg joint 9, step ending at frame 108. This follow-up retains that joint's entire held correction track and tests the same eight fixed fractions for all other root and leg parameters. It does not change an acceptance tolerance, add optimizer sweeps, or adapt the tested fractions. The original trial, its independent audit, and all inputs are hash-bound in the new request.

All eight candidates retain their decoded hard edit bounds and transform preservation. Fractions 1/64 and 1/32 pass the limited direction guards. None passes the original full development comparison. An independent audit freshly decodes 1,200 integer poses and 1,192 half-frame skins, checks the exact parameter interpolation, and confirms that the protected joint's local rotation remains unchanged.

| Fraction | Acceleration excess energy | Floor (mm) | Root peak (m/s²) | Guarded improvement |
| --- | ---: | ---: | ---: | --- |
| 0 |225.4282|2.349|4.479|no: baseline|
| 1/64 |219.0377|2.785|4.547|yes|
| 1/32 |218.1992|3.251|4.615|yes|
| 1/16 |246.8181|6.438|4.754|no|
| 1/8 |476.6175|12.787|5.037|no|
| 1/4 |1747.2390|25.140|5.622|no|
| 1/2 |8042.7115|48.330|6.840|no|
| 1 |37677.6599|90.371|13.074|no|

Every candidate's decoded local-rotation peak remains 19.959218898 degrees at the protected step. Protecting one joint changes the direction substantially: large fractions now worsen acceleration energy too. This is evidence from one previously inspected development clip, not a held-out or general correction result.

## Engine verification and individual release failures

The minimum-energy guarded candidate (1/32) was selected only for engine verification. `reports/support-acceleration-protected-engine-v1` binds the selection, completed trial and independent audit before import. Raw, held and guarded clips all match Godot's decoded transforms across 450 actor-frames; maximum position error is below 5e-7 m and matrix-element error below 6.3e-7. Mesh surfaces survive import. This does not establish perceptual quality or approve the correction.

Fresh release-window decoding in `reports/support-acceleration-protected-releases-v1.json` verifies all 11 original releases for held and both guarded fractions. The held clip has three failing right releases. At 1/64, one right failure resolves but one new left failure appears. At 1/32, one right failure resolves but three new left failures appear: total failures rise from three to five despite the 3.21% aggregate energy reduction.

| Side / release frame | Frozen acceleration limit (m/s²) | Held | Guarded 1/32 | Guarded excess |
| --- | ---: | ---: | ---: | ---: |
| Left / 32 |30.011170|29.446807|30.051053|0.039883|
| Left / 99 |31.802878|31.791883|33.153044|1.350166|
| Left / 129 |14.547833|14.536834|14.559181|0.011348|
| Right / 19 |3.468900|7.445875|7.200862|3.731962|
| Right / 109 |26.043930|26.046359|26.053607|0.009676|

The largest remaining excess is around right-foot release 19, peaking at acceleration center 18. The largest newly introduced excess is around left release 99, peaking at center 100. These are decoded mesh-centroid measurements around drafted support intervals, not confirmed physical contact or perceptual verdicts.

The next correction must protect individual release windows alongside floor, root, rotation and edit limits. An aggregate foot-acceleration objective alone can exchange errors between feet and times. Keep the raw/prior/held variants and all failed proposals; do not promote the engine-verified blend or turn these diagnostic guards into a quality certificate. Independent animator ratings, cleanup time and held-out validation remain missing.
