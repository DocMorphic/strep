# Native support fitting across complete character skins

Native support smoothing, joint-rate search and final serialized checks now
use every primitive of the validated single skin. The complete-surface helper
is archived with each fitting job. Original native clocks, root motion,
untouched branches, inverse binds and mesh payloads remain preserved.
Default authoring and source-relative acceptance limits are unchanged.

Five new loaded-GLB tests cover three actual primitives, mixed four/eight
influence slots, a lower foot surface that changes the required lift,
independent decoded geometry, mesh/binary/channel preservation, four-trial
default and orientation jobs, helper archives, and strict warm repair selection.
These fixtures are CPU tests, separate from the real engine results below.

## Explicit near-unit input preparation

The existing Quaternius files contain static scale values within 4.769e-7 of
one. Accumulation through their 65-bone hierarchies violates stricter rigid
solver checks. The original female study preserves four rejected trials;
the male run rejects during rate preparation. Those inputs and diagnostics
remain immutable, rather than relaxing the rigid checks.

`native_support_rigid_input.py` creates a separate version for static TRS
roundoff at most 5e-7. It rejects larger scales, scaled/sheared matrices,
non-unit animated scales and geometry changes above 1e-5 m. At the original
reference pose and every 120 Hz/native-key/midpoint audit time, it compares
every vertex and bone transform against the preserved input. Mesh data,
inverse binds and animation bytes are unchanged; only declared static scales
become one. Input/method hashes and the full comparison are archived. This
is an explicit conversion with a numerical change budget, not an automatic
Studio operation, a motion-quality gate or support for general scaling.

```powershell
.venv/Scripts/python.exe scripts/native_support_rigid_input.py `
  path/to/clip.glb reports/fresh-rigid-input
```

Use the reported `prepared.glb` hash in a separately versioned support draft.
Existing drafts stay bound to their original clips. Then run the documented
[support fitting](native-support-intervals-v1.md) and
[engine/skin audits](native-support-engine-v1.md).

The two development conversions change 29/36 static nodes. Across 701 sampled
poses plus the reference, maximum vertex distances are 1.1597e-7/1.2747e-7 m
(0.116/0.128 micrometres). Seven preparation tests check explicit provenance,
preserved payloads, source immutability, rigid output, unsupported scales,
geometry-budget rejection, existing-output protection and method binding
before sampling. Original scale values remain in the saved comparison.

## Same-objective convergence repair

The first prepared male study rejects trial 2 after L-BFGS reports relative
objective convergence but the projected-gradient residual remains
1.1068054642e-7, above the unchanged 1e-7 threshold. Its other three proposals
are complete and remain saved; the four-completed-trial auditor correctly
rejects that incomplete population.

The smoother now has a bounded least-squares fallback for unsuccessful or
insufficiently stationary L-BFGS results. It uses the same integrated velocity,
acceleration and reference quadratic on the same irregular physical clock,
eliminates fixed columns, and preserves every hard box. It must succeed,
meet the original stationarity check and not increase the numerical objective
beyond floating-point roundoff. Five tests independently verify convex KKT
conditions, physical objective equality, fixed endpoints and rejection of
bad box, stationarity or success results.

A matched fresh male study completes all four trials. Only trial 2's right
stance needs polishing: 24 active-set iterations reduce residual to
1.5543122345e-15 and decrease the numerical objective from 6.5352181465e-6 to
6.5352177636e-6. Earlier studies and archived implementations remain unchanged.

## Actual development fitting and imports

Three previously examined height-calibrated wave clips are used: CesiumMan and
Quaternius female/male, three assets across two rig families. The new drafts
explicitly use ground zero, both stances at 1.6–2.4 seconds, edit keys 15–105,
0.25 mm clearance, 5 mm maximum gap, 30 mm displacement and 45-degree local
angle bounds. Four smoothing settings per asset are optimizer variants, not
new model seeds or held-out evidence. Wave is this study's measurement case,
not a motion whitelist.

All 12 final proposals pass sampled support and preservation checks at 701
times and 142 stance samples per foot. **Every proposal fails the unchanged
source-relative rate selection. Every fitter retains its exact input.** The
prepared assets use their explicitly versioned input as the rate reference.

| Asset | Failed speed/acceleration/angular speed/angular acceleration rows, trials 0–3 |
| --- | --- |
| CesiumMan | 463/23/85/21; 471/27/111/17; 501/21/109/21; 499/24/98/17 |
| Quaternius female | 351/35/60/18; 378/40/90/16; 352/32/68/20; 370/33/59/17 |
| Quaternius male, fresh study | 327/30/60/21; 342/37/54/18; 326/29/60/19; 355/33/58/15 |

Actual headless Godot 4.7.2 imports each input and all four proposals, saves and
reloads native LINEAR resources, and verifies 10,515 poses. Maximum bone
position error is 5.539e-7 m and basis element error 8.513e-7. All pose/clock
checks pass. Original-skin and actual imported-skin height checks preserve the
input penetration failures and all 12 proposals' sampled support passes.

Every imported surface participates: one for CesiumMan, three each for the
Quaternius assets, with 3,273/8,844/8,483 source vertices respectively. Actual
rest/bind/weight correspondence passes under existing limits. Raw imported
weights remain unrenormalized. Across 72,203,000 reconstructed vertex
observations, the maximum vertex difference is 9.2973e-5 m (0.09298 mm).
This measures imported CPU skin reconstruction, not GPU rendering.

All 540 bound input, preparation, study, method, resource, observation and
failure files rehash. Receipt:
`f16e174594477c08b4b638df2e6f3f4d40b9b7786b4fa4ce0f7f53d979ff26bc`.

Final fit / actual skin result hashes:

- Cesium: `0e866ba05707318e9f21f107d16e1f39a0008e274a748b96e5443ece48e76414` /
  `c22cb44934cc1263d75bb1e4a4e4adf16a818e24139ea0f34335dea2a4c513a8`.
- Female: `d6e60e58eb3bf5713e6f886e2bfab4978e212be6a16b3d68f001c1c4ae23e30e` /
  `18a918d6a68ec5b481161dc7b32ca6e824ab60de9a94200d1435cf8c67c9cf4b`.
- Male: `e13653afd8216ce50e72f836e0efd1e1f2aa3bd644585f5d49d6411added6874` /
  `aeb08b13691c6c8264875a082d21c12b41f9971cdd8e624fb99d8fda4bb2b96e`.

The 1,398-test model-free Python suite and 14 JavaScript suites pass; two
subsequent provenance/strict-repair tests pass with their full 12-test focused
group, totaling 1,400 Python checks. All new suites enter Windows/Linux CI.
Previous commit `8d0f892` passed hosted run 36958817859 on both platforms.

No proposal is promoted to Studio or release approval. Foot-height success
does not establish planted sole patches, reduced sliding, continuous collision,
force/balance, engine derivative preservation or human usability. Other actions,
scenes, held-out rigs and timed cleanup remain open. These studies do not train
or run a new model. All 14 release capabilities remain unapproved and the
full-project goal stays active. The subsequent
[action-family diagnostics](native-support-action-breadth-v1.md) and
[explicit Studio preparation](studio-support-preparation-v1.md) record that
follow-up, including retained failures and measured scope.
