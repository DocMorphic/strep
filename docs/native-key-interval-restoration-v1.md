# Coupled correction across native animation keys

The [native-key initializer](native-key-contact-initializer-v1.md) substantially improves spatial clearance, but its independently solved keys create temporal failures. A new `KeyIntervalModel` couples a declared contiguous interval of existing keys while preserving the original clip, physical edit limits, contact intent and motion-rate reference. Its first actual step repairs two rate rows and twelve floor samples without new failures. The clip still fails acceptance and remains unapproved.

## Model and authoring scope

`scripts/native_key_interval_model.py` accepts a bound initializer output, trusted result and original-request digests, and explicit active key indices. It validates original inputs/method snapshots, reconstructs initial key quaternions exactly, and retains every inactive/frozen key. A complete interval may contain up to 768 control components; exceeding this limit rejects rather than discarding variables. This is a general Python proposal API, currently exercised through guarded study drivers; no new Studio selector or complete release workflow is claimed.

```python
from native_key_interval_model import KeyIntervalModel
from native_scene_conic import direction

problem = KeyIntervalModel(producer, result_digest, request_digest, active_keys)
value = problem.initial.copy()
worlds = problem.initial_world  # Independently loaded initial animation.
system, jacobian, identity = problem.linearize(value, worlds, .02, step=.001)
delta, report = direction(system, jacobian, value,
    problem.lower, problem.upper, .02, hard_rows=identity['hard_rows'])
# Export/decode each candidate and fully audit it before any retention.
```

Cached original local transforms and batched native SLERP make larger coupled intervals practical. The actual native decoder still determines candidate observations. Every complete sampled local-rotation and joint-displacement row is retained, along with outgoing/incoming world/object/partner point conditions and hold-speed populations. The four original rate arrays retain the same 120-Hz source clock, four bins and `1e-5` tolerance. An already repaired clip never becomes a replacement rate reference; deliberate cap mutation rejects.

Full triangle-referenced minima are computed at every original geometry time. Moving minimum vertices guide the local proposal, and are rebuilt after a candidate changes. Sparse continuous finite differences keep exact zero entries implicit, preserve all rows, and reject a declared nonzero-capacity overflow. Decoded vectors and floor gaps anchor the affine model. Sparse witnesses and affine solver success cannot establish geometry or animation feasibility.

Every original rate and floor condition receives a separate hard no-worsening bound. Passing rows keep their original limit; failed rows cannot exceed their own decoded starting norm. Original caps remain in the soft minimax suffix. This does not average failures together or exchange a new violation for an improvement elsewhere. Complete independently exported/decoded observations decide retention. Original assets remain selected, and no quality or training approval follows from retaining a numerically improved research proposal.

## Actual interval and failures

A read-only decomposition first reproduces all 85,590 saved original rate rows. Of 58 failures, 56 involve positional speed/acceleration and two involve hip angular acceleration. The affected nodes are named LeftToes, LeftFoot and LeftLeg; these names are diagnostics, not anatomical annotations. All failures lie from 0.60 through 1.075 seconds. None has a zero source cap, and maximum normalized excess is 2.899634. All 32 floor failures are also retained. This identifies substantive trajectory failures rather than merely stored-key rounding. The diagnostic takes 1.031 seconds/19 resource observations, with its trace replayed.

The actual coupled trial edits original key indices 12–42: 31 keys, four previously permitted left-leg rotation tracks and 372 scalar controls. It retains 30-degree/22-cm limits, fixed root, original endpoints, the separately authored raised-right-foot position target, Y=0/5-mm floor and the original source epoch. That target remains a position-preservation example, not inferred planted-foot support.

The complete affine system contains 274,048 norm rows, including a 186,441-row hard prefix, all 85,590 original rate rows, and all 2,017 original floor times. It has 331,346 sparse nonzeros. The solver retains 1,636 active cones; fixed-passing and conservatively bounded affine-box-passing conditions are accounted for separately. No actual audit condition or variable is discarded. The primary solve reports `Solved`; its optional smaller-norm phase is rejected because independent affine checking finds a hard-row violation.

| Returned proposal | Original rate failures | Failed floor times | Peak floor depth (mm) | Retained step? |
| --- | ---: | ---: | ---: | --- |
| Start | 58 | 32 | 6.509660 | Initial proposal |
| Full step | 32 | 101 | 11.216430 | No |
| Half step | 39 | 91 | 7.820327 | No |
| Quarter step | 48 | 73 | 6.133326 | No |
| One-eighth step | 55 | 63 | 6.261723 | No |
| One-sixteenth step | 56 | 20 | 6.385824 | Yes, research proposal only |

The full step's improved rate count cannot excuse new ground failures. The selected smaller step repairs two original rate rows and twelve floor times, introduces no new rate/floor failures and does not increase any individual positive violation. Edit/contact conditions pass and the root remains exact. Fifty-six rate failures and twenty floor failures still reject the clip. Geometry covers every 1,029 triangle-referenced vertices and 1,604 faces at all 2,017 times.

The trial takes 175.890 seconds/192 resource observations. A fresh replay reconstructs exact bytes and complete controls/worlds/vectors/caps/scales/residuals/floor witnesses for all seven returned exports, plus the final full geometry and contact populations. It confirms every rowwise nonregression and repair count without running the optimizer or rebuilding the Jacobian. All four original cap arrays additionally match the initializer epoch in shape, dtype and logical element bytes. Their first two NPY members use different recorded Fortran/C storage orders, which the separate byte checker honors; raw serialized-member equality is not claimed. Replay takes 72.828 seconds/90 observations; both resource traces replay. Reader, curve and skin methods are shared; this is not independent physics or human review.

All 45 selected software checks pass, including nine new interval cases and existing native-norm/rotation suites. They verify native/intermediate-time preview versus actual exported matrices, retained inactive/frozen keys, complete protected/soft populations, sparse capacity rejection and original-cap mutation rejection. Validation takes 91.938 seconds/109 resource observations with its trace replayed. An initial missing-suite preparation error is retained and rejects before a numerical worker starts; corrected validation uses checked existing suite paths.

Private evidence stays under ignored `reports/native-key-temporal-failures-v1`, `reports/native-key-interval-model-validation-v1`, `reports/kenney-key-interval-restoration-v1` and `reports/kenney-key-interval-replay-v1`. Source snapshots and failed candidates remain local; character payloads and bulky reports are not published.

The preceding [focused hosted workflow at 05503f0](https://github.com/DocMorphic/strep/actions/runs/38608356131) passes all eight Windows/Linux jobs; this new source still needs its own hosted outcome. All fourteen release capabilities and calibration gates remain unchanged and unapproved. No generation, training, reserved cases, engine execution, new human ratings or cleanup measurements occur here. Continue coupled clearance/rate correction and integrate the general workflow, then broaden action/rig/scene/partner/style/runtime/held-out and developer-review evaluation under the same entire-project goal.
