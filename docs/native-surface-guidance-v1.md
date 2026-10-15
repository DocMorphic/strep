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

A separate declared hand-region trial follows. It takes every incident triangle
of vertices carrying at least 0.5 total skin weight from the named RightHand
subtree, then includes every vertex of those triangles. It evaluates the fixed
three world axes, orders the actor patches by their original mean projection,
and chooses the largest original projection gap, with listed-axis tie order.
This is proposal guidance, not a verified palm normal or semantic contact patch.
Its complete actor meshes must still be checked after the pose proposal. If
both poses fit, exactly one predefined compact-quintic native-curve construction
is tested against unchanged original motion rates, floor and point contacts.
Neither trial relaxes acceptance or automatically selects a new clip.

All release capabilities and human/held-out calibration gates remain unapproved.
