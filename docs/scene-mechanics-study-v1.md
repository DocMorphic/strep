# Source-humanoid scene mechanics and compatible-grip comparison

Development study, 2026-10-10. This separately exposed scene uses a real supplied skinned humanoid with **18,056 vertices and 36,108 triangles**, plus two spheres. The object named `box` in the original scene is actually a **0.25 m radius sphere**; its name does not establish rectangular-box coverage. The second sphere has radius 0.2 m. Keep the original character, object tracks, ten surface correspondences, grip intervals and acceptance limits unchanged in the failed baseline.

Assume a uniform 1 kg solid sphere with centered COM, inertia `0.025 I` kg mÂ², Y gravity âˆ’9.81 m/sÂ², Coulomb friction 0.5 and a 20 N total-force cap per correspondence. Each hand has five points, giving a declared summed 100 N budget. These are hypothetical mechanics, not measured material properties or human strength. The added 180-sample uniform differentiation clock preserves exact clip endpoints. Of 178 interior derivative samples, 59 belong to the complete supported stencil, 119 are unassessed unknown/cross-phase samples, and two endpoints have no estimate.

| Check | Original exposed scene |
|---|---:|
| Conditional object-force witnesses | 0/59 |
| Necessary axis exclusions | 49/59 |
| Complete wrench-projection exclusions | 10/59 |
| Actual complete supported grip stencils passing | 0/59 |
| Combined sampled scene/force consistency | 0/59 |
| Full sampled actor/object geometry | Pass |
| Original complete surface contact audit | Fail |

The full geometry clock contains **2,379 times**, preserving every original geometry/contact time and the added force times. It checks all 36,108 faces against both objects: **171,801,864 triangle/object queries**. Separate numeric replay checks all 14,275 archived arrays, 6,872,093,592 logical bytes, triangle plane/edge distances and witnesses, closed directed-edge topology, positive volume and independent center-ray parity using up to three directions. Reconstructed depth brackets agree exactly; witness positions differ by at most 1.111eâˆ’16 m. Contact replay separately checks 10,330 original-clock point/normal observations, 1,800 force-clock observations and all position/speed/normal/side/stencil predicates. Archived RigAsset, sampler and scene interpolation are shared and explicitly outside numerical independence.

The producer completes in 2,687.469 supervisor seconds, including 86.969 seconds of admission, with 2534 independently replayed resource records and a sampled 273,256,448-byte peak. Numeric replay completes in 722.828 supervisor seconds, including 390.093 admission seconds, with 699 replayed records and a 1,389,875,200-byte peak. Both retain the full 2 GiB estimate plus 600 MiB reserve. A failed first contact replay expected absent point arrays in a normals-only archive. It remains immutable; the corrected verifier reconstructs points and checks the actual normal arrays without reducing clocks or changing physical acceptance limits.

## Separately authored force-compatible targets

The original centered grips lie at local `(Â±0.2236068, 0.1118034, 0)` m, whose outward normals have Y component about 0.4472. With friction 0.5, the centered inward cones provide essentially no upward support. This is a property of the authored model, not a generator training failure.

Create a distinct development scene by rotating each entire hand target patch about object-local Z by âˆ“26.565Â° so its centered point lies at `(Â±0.25, 0, 0)` m. Preserve every skin correspondence, interval, position/speed limit, original object trajectory, mass/inertia/gravity, friction and 20 N point cap. Do not replace the failed baseline. The full force/torque demand remains identical.

| Complete hypothetical force model | Conditional witnesses |
|---|---:|
| Original upper-side target patches | 0/59 |
| Separate equatorial target patches | 59/59 |

Independent force-only replay reconstructs both original rigid demands and every rotated target, then checks all **118 samples with ten contacts each**, complete force/torque balance, unilateral/friction/cap constraints and exclusions. Producer/auditor sampled peaks are 72,343,552/96,616,448 bytes; seven resource records each replay. These bounded force-only jobs use the separate 512 MiB estimate plus 600 MiB reserve. The first comparison replay rejected sub-ulp normal renormalization using dict equality; its failed output remains preserved. The corrected replay retains exact IDs/scalars and independently reconstructs both vector declarations at its existing numerical accuracy. Force/torque/cone/cap acceptance limits remain unchanged.

**59/59 conditional witnesses do not establish an animation.** The character has not yet moved to these targets, and actual hand contact, orientation, geometry, support balance, joint loads, anatomical validity, generation, rig transfer and engine/human review remain unverified for the new scene. Neither study is held out or admitted as clean human training data. Quality, release and training approval remain false. Follow the [model decision sequence](scene-model-next-steps-v1.md): compare physically compatible authored targets and existing checkpoint controls before selecting a learned editor.

Local immutable final receipts: original-scene audit SHA-256 `c945e28908dc426cac5facb93f95a2e5eb56ce03db99d4fdb8267a9d93fc570a`; matched-force audit `f799eeb9bba64998023190b98e7f5c7ddbb5fb1a322001bd19ffe90dbecd4e01`. Bulky raw outputs, source character payload and machine reports stay outside Git. Provisioned local acquisition and study inputs are still required; the public [scene-force workflow](scene-contact-forces-v1.md) and synthetic tests establish the reusable implementation, not a fully bundled experiment or installer.
