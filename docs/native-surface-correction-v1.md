# Full-mesh-guided native scene correction

The optional `surface-vector` mode in `scripts/native_scene_fit.py` connects
partner-surface constraints to the native motion solver. It requires an explicit
geometry policy and a starting clip that already passes every original native
motion/contact condition. It retains the original source epoch and edit
permissions, including when resuming a completed fit. It does not reset rate
caps using an edited animation.

```powershell
.venv\Scripts\python.exe scripts/native_scene_fit.py contacts.json permissions.json reports/surface-fit --proposal-model surface-vector --geometry-policy policy.json --resume-from reports/completed-fit --iterations 2 --restoration-steps 3
```

The existing 1–16 iteration limit and maximum normalized trust of 0.02 apply.
The optional restoration loop has at most four extra proposal solves. Explicit
geometry clocks are inserted into pose sampling without changing the original
uniform rate clock, bins, tolerance or cap arrays. Object primitives are
explicitly rejected by this mode; object correction remains outstanding.

`scripts/native_surface_model.py` rebuilds complete partner triangle and
containment queries at each retained step. Local fixed-axis/barycentric rows are
converted to vector norms inside the current affine trust box. All original
motion **and contact** norms are hard conditions in the proposal solve. Continuous
finite differences propose changes; independently exported/decoded clips decide
acceptance. Each candidate, including rejected candidates, receives a complete
sampled mesh audit.

Actual acceptance requires every original decoded native condition to pass and
the complete geometry score to improve. That score compares maximum penetration
normalized by the unchanged policy limit first, then crossing-record count,
vertices over the penetration tolerance and failed geometry-condition count.
A depth regression cannot be exchanged for fewer crossings. A depth improvement
can retain more crossing records, which must remain visible; the score is an
optimization policy, not a realism or release criterion. Complete collision
conditions must still pass before any collision-free claim.

An optional `--surface-contact-policy` additionally enables
[contact-normal guidance](native-contact-guidance-v1.md). In that mode acceptance
requires the geometry score and the aggregate surface-contact error to avoid
regression, with at least one objective improving. This aggregate rule can still
trade individual contact errors against each other; the later retained result
shows a small opposition-angle regression and remains a failure.

The proposal's base vectors use decoded scalar-sampler poses. Batched continuous
poses provide derivatives only. A first real-case attempt exposed a normalized
rate-row mismatch up to 0.000003656 between the batch proxy and decoded exports
and stopped without producing a result. Decoded anchoring removes that proxy
base mismatch while retaining exactly the original caps/scales. No acceptance
tolerance was loosened. Measured underprediction can tighten proposal margins;
actual decoded limits remain unchanged.

## Retained high-five development result

Two surface-guided steps resume the prior 33-iteration point-contact fit against
the exact original actors and permissions, giving 35 cumulative primary
iterations. The source has two 18,056-vertex, 36,108-triangle actors. The policy
retains times 0, 2.5 and 4.9666666984558105 seconds, the fixed Y=0 plane, 5 mm
penetration tolerance and original surface tolerance. This experiment uses the
original scene placements; it does not apply the separate 15 mm stage rise.

| Measurement | Start | After two accepted steps |
| --- | ---: | ---: |
| Palm point separation | 29.9995 mm | 25.9743 mm |
| Maximum partner containment depth | 21.4951 mm | 20.7519 mm |
| Proper surface crossings | 451 | 478 |
| Vertices deeper than 5 mm | 364 | 396 |
| Failed sampled geometry conditions | 7 | 7 |

Both accepted steps pass all unchanged native/contact conditions. Their initial
unrestored proposals fail decoded conditions and remain rejected. The first
step needs two restoration solves, the second one. Surface guidance includes
6,588 and 6,718 rows respectively, including the original floor violations.
All geometry remains a failure; increasing crossing/containment populations
make this a mixed development result. No candidate is selected for release.

The next correction needs a better balance of contact-region orientation and
complete surface separation. Further proposals must preserve the original epoch
and explicit permission bounds, and full mesh checks must continue to expose
regressions. This work does not train or change a checkpoint, prove continuous
collision freedom, establish GPU/runtime playback, or replace developer and
animator review.

Independent replay re-exports all seven saved control vectors and fourteen GLBs
byte-for-byte, checks exact original rate-cap arrays, and recomputes complete
geometry through decoded poses and the source skin-point callback. It confirms
both accepted steps and every unsafe rejection. Sampling and mesh classifiers
are shared with the audit code; this does not independently prove continuous
or renderer behavior.

Local failed/completed studies are retained under
`reports/native-surface-fit-development-v1/` and
`reports/native-surface-fit-development-v2/`. Regressions cover original-cap
preservation when adding clocks, full witness/norm integration, decoded
anchoring, actual acceptance versus unsafe decoded proposals, invalid settings,
and public fitting lifecycle behavior. Public CI includes the new suite on
Linux and Windows. All 395 focused model-free regressions pass, including
15 new surface-model/integration cases. Generated scenes and study payloads remain excluded from
the public repository.
