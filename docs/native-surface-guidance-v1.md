# Explicit surface guidance for native pose proposals

`surface_separation_planes.planes` projects every supplied vertex onto an explicit
unit world axis, keeps the original extremal witnesses, and returns two fixed
halfspaces about the original projected midpoint. The caller supplies clearance.
No vertices are sampled, removed or chosen by the function. A strictly positive
projection gap is sufficient for separation of triangles whose vertices are all
included in exact arithmetic. Overlapping projections do not establish a
collision; zero clearance can allow touching. Ordinary Float64 projections are
not certified arithmetic or an anatomical contact model.

`KeyPose` retains its default of applying every guidance plane to every
triangle-referenced skin vertex. Its optional `plane_vertices` argument can
instead name an explicit population for each guidance plane. Names must match
the planes exactly; every population must be a nonempty list of distinct,
existing triangle-referenced canonical vertex indices. Invalid or missing
populations fail. Caller mutation does not change the stored population.
Complete skin evaluation, all original joint displacement and rotation bounds,
and active point-contact rows remain present. The optional region changes
proposal guidance only. It does not change the original scene policy, source
motion caps, full-mesh acceptance or any exported asset automatically.

The full-mesh acceptance operation must still query both complete actor surfaces,
all declared partners/objects and original floor planes. A region-guide pose pass
cannot stand in for that check, the complete animation clock, native curve/rate
validation, engine playback or human review. Native-key authoring commands keep
their existing complete-plane default; no automatic region selection was added
to those commands or Studio.

## Local regression evidence

All **69** affected checks pass in **73.03 seconds**, covering both new modules,
the existing affine pose solver and native-key initializer. The unchanged
default and an explicit complete selection have exactly identical rows,
derivatives, worlds and skins. Region tests check original vertex ordering,
unchanged non-plane rows and complete skin output, finite-difference derivatives,
caller mutation and invalid populations. Projection tests include rigid
coordinate changes, retained outliers, full box triangle queries, touching,
overlapping projections without collision, and malformed/nonfinite inputs.

The 512 MiB CPU guard completes in **89.203 seconds**, peak **144,596,992 bytes**;
all **90** resource observations replay. These are generated numerical fixtures,
not evidence that a realistic humanoid animation or a release capability passes.
The source inventories now declare **518 Python modules / 45 Node suites** and
the contact/rig subset **82 Python modules / five Node suites**. Hosted checks
remain separate from this local result.

## Retained real high-five experiment

The first finite trial uses the native motion of the existing weight-conditioned
high-five export at the previously measured early-collision time
**1.1395833333333334 seconds**. Original non-weight asset data is verified
unchanged. An explicit world-Z guide attempts whole-character separation with
1 mm clearance and a further 0.5 mm proposal reserve per side. Only the four
existing right shoulder/arm/forearm/hand rotations may change, each by at most
10 degrees, with every skin joint limited to 50 mm displacement and roots fixed.
The source floor and scene acceptance policies are unchanged.

The complete source projections overlap by **155.101199 mm** along that axis;
this is not a penetration-depth measurement. Actor A reaches its 40-iteration
limit and B stops with a positive line-search directional derivative after 22
iterations. Both proposals fail their inequalities and retain the original.
No curve is constructed or adopted. This failure concerns this finite guide
and solver run; it does not prove the original collision is unrepairable.
The 768 MiB CPU guard completes in **70.047 seconds**, peak **224,411,648 bytes**;
all **71** resource observations replay. Local records remain under ignored
`reports/high-five-separation-proposal-v1`.

A separate declared hand-region trial takes every incident triangle
of vertices carrying at least 0.5 total skin weight from the named RightHand
subtree, then includes every vertex of those triangles. It evaluates the fixed
three world axes, orders the actor patches by their original mean projection,
and chooses the largest original projection gap, with listed-axis tie order.
This is proposal guidance, not a verified palm normal or semantic contact patch.
Its complete actor meshes must still be checked after the pose proposal. If
both poses fit, exactly one predefined compact-quintic native-curve construction
is tested against unchanged original motion rates, floor and point contacts.
Neither trial relaxes acceptance or automatically selects a new clip.

That trial selects world X and fits B in eight iterations / A in ten. Both
explicit hand regions have a **2 mm** positive projection gap at the fitted
pose. The subsequent complete-mesh query still fails:

| Native-source diagnostic at 1.1395833333333334 s | Surface outcomes | A inside B maximum | B inside A maximum |
| --- | ---: | ---: | ---: |
| Original | 301 | 7.143428 mm | 21.138767 mm |
| Fitted pose | 92 | 5.965841 mm | 6.044843 mm |
| Exported native curve | 92 | 5.978984 mm | 6.056315 mm |

These are native-source evaluations of the conditioned export, distinct from
the earlier imported-engine measurements. The fitted regions are separated;
the complete actors are not. Floor depths at the pose remain 7.285620 mm and
6.336010 mm, exceeding the unchanged 5 mm screen.

The single predefined curve uses a 0.5 s approach half-width on both actors and
reuses the prior A meeting-pose seed with a separate 0.2 s half-width. Each
quintic falloff modifies existing native keys only. Root matrices and all
endpoint matrices remain exactly unchanged; all original caps/scales are kept.
Both actors' full 2,017-time floor clocks still fail at every time, without
worsening. Actor A has **15 rotation/joint-bound rows and 215 original-rate
rows** failing; B has **192 and 109**, respectively. Combined point contacts
pass at 2 s, with a **29.500027 mm** hand-to-hand gap inside the original
30 mm limit. Full geometry at that time has **666 surface outcomes** and
10.679468 / 13.498281 mm maximum inside depths. The clip remains rejected.
Only two selected geometry times were queried for the exported curve; no
complete-clock geometry or engine pass is inferred.

The trial guard completes in **274.125 seconds**, peak **359,026,688 bytes**;
all **272** resource observations replay. Records remain under ignored
`reports/high-five-hand-region-proposal-v1`. This demonstrates why region
guidance and point-contact success are not motion acceptance.

A read-only follow-up attributes every recorded surface outcome through the
unchanged canonical skin weights. All 92 residual early outcomes are proper
crossings between A's named RightForeArm region and B's RightHand/Pinky regions
(72 Pinky1, 13 Pinky2, seven Hand). The selected hand/hand regions therefore
cannot cover the whole failure. These are weighted mesh labels, not reviewed
anatomical ground truth. The same follow-up recomputes every stored motion
residual and verifies every original rate-cap array plus its unchanged 1e-5
tolerance. All bound failures are joint-displacement rows, and the complete
source/candidate floor-gap arrays are exactly identical for both actors.
This scalar replay does not independently reconstruct the decoded motion;
fresh time/track attribution is still required before another curve proposal.

The first follow-up stops on an incorrect assumption that only two contact
rows are stored per actor. The interval model retains all three, including the
unchanged other actor's row. That failed attempt is preserved. The corrected
fresh follow-up completes in **35.485 seconds**, peak **141,750,272 bytes**;
all **37** resource observations replay under its 512 MiB CPU guard. Records
remain under ignored `reports/high-five-hand-region-diagnostic-v1` and `-v2`.

The focused hosted workflows at `fadd579d6e790ea888ac8172894c96506fb641be`
pass all **31 new checks per OS**: [projection checks](https://github.com/DocMorphic/strep/actions/runs/38696567039)
report 18 passed in 0.59 s on Ubuntu / 0.99 s on Windows, and
[region checks](https://github.com/DocMorphic/strep/actions/runs/38696570288)
report 13 passed in 1.20 s / 3.39 s. These runs do not establish a complete
518-module suite, engine or human-quality pass.

All release capabilities and human/held-out calibration gates remain unapproved.
