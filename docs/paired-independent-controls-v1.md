# Independent wrist controls for two-character edits

The existing hand experiments share a wrist displacement vector: actor A moves
by that vector and actor B moves by its negative. This fixes the wrist midpoint
and couples each actor's permitted adjustment to the other. General interaction
editing needs the option to move either actor alone or move both in a common
direction while still preserving the final contact pose.

`independent_hand_motion.py` adds a separate native-key control representation.
Each editable key has 14 values: A's scene wrist XYZ displacement, B's scene
wrist XYZ displacement, A/B elbow swivels, and A/B scene hand rotation vectors.
Displacements are metres; angles and rotation vectors are degrees. The adapter
uses the existing validated oriented editor for each actor and leaves endpoint
keys frozen. Scale and margin helpers retain each actor's original displacement,
swivel, hand-vector and adjacent guide-rate limits; the connected optimizer
enforces those margins. Decoded joint-motion constraints remain a separate
requirement for that solve; guide limits alone do not prove them.

`from_symmetric()` converts previous eleven-value keys without resampling or
changing their intended motion. Under oblique scene placements, tests verify
each independent wrist position and hand orientation in actual exported GLBs,
unchanged motion for the other actor, exact stored frozen keys and unchanged
shared sampler channels. Converting a symmetric candidate produces byte-for-byte
identical GLBs for both actors. Common-direction wrist movement is representable,
and the guide check rejects diagonal displacement exceeding either actor's
Euclidean budget.

The original standalone control suite passed 32 tests and the minimal public
Python suite passed 678 tests. The module is now connected to the numerical
optimizer and completed-return diagnostic; Studio does not yet expose it.

## Layout and replay contract

`--hand-orientation --independent-wrists` selects the persisted layout
`independent-wrists-v1`; oriented searches without the new flag use
`symmetric-wrist-v1`. Prior oriented requests without a layout field retain the
symmetric interpretation. Unknown layouts are rejected. The independent option
requires oriented controls. Both the request and result record the layout.

Warm-start loading binds the donor's files, original input identity and control
methods. Eleven-value keys can be converted exactly to fourteen-value keys;
existing independent keys can be embedded at the same native timestamps without
resampling. Independent donors additionally bind the independent editor method.
A downgrade that would drop actor B's wrist values is rejected. The driver
compares the resulting motion with actual donor GLBs and rechecks guide/native/
original motion limits before optimization. Fresh geometry and actual exported
motion remain required after the solve.

The solver supports up to twelve keys in either oriented layout. At six keys,
84 controls give each actor its own wrist XYZ vector. Tests exercise the final
component of an actual 84-variable solve, full finite-difference cache retention,
legacy conversion and independent reuse, rejected unknown layouts and
method changes, and byte-identical GLBs when extending asymmetric trajectories.
The focused control/reuse/geometry suite passes 58 tests; the complete minimal
public Python suite passes 685 tests.

## Bounded real comparison

The completed symmetric six-key experiment selected its prior warm start
unchanged. It still has 17 failing hand times out of 43 and a 20.932848 mm peak.
The independent comparison keeps its exact six-key clock, original 120 Hz support and
motion bins, individual guide budgets, 45-degree native limit and final contact
pose. Zero controls and the converted verified candidate are the two starts,
with at most 100 iterations each. All 86 source directional queries can be
reused only after their source bindings and geometry methods are verified.
Selected geometry must be measured fresh and compared in both directions at
all 43 matching times. Earlier whole-body defects still need separate work.

With the local bound studies and assets present, use a fresh output directory:

```powershell
.venv/Scripts/python.exe -u scripts/fit_continuous_terminal_hand.py reports/scene-pair-terminal-hand-search-v1 reports/scene-pair-independent-hand-v1 --hand-orientation --independent-wrists --editable-keys 6 --witness-study reports/scene-pair-extended-hand-v1 --warm-start-study reports/scene-pair-extended-hand-v1
```

No independent-wrist quality outcome, whole-body clearance or engine approval
is claimed from representation tests. All 14 release capabilities remain
unapproved. See [the completed symmetric audit](paired-extended-hand-v1.md).


The real worker entered optimization after verifying its inputs. The verified warm-start replay has
exactly zero error for both actors; expanded-support motion and guide checks
pass. All 86 directional source queries were verified and reused. Both starts
have 84 controls, and imported method hashes match the working source. The
request hash is `8e63f4948ebd1e3038869a5ba3f4bb34c3f5d9f4995dde933f19e643f86352b7`.
The completed solve, exported-motion and fresh geometry results follow.


## Completed solve and geometry audit

Both starts reached the 100-iteration limit (status 9). The recorded population
contains 17,809 evaluations, including finite differences, and 93 feasible
observations. The selected observation is 8,968, a finite-difference perturbation
of the verified warm start: actor A wrist X changes by 0.000006 m at native time
1.991499066 seconds. Other controls are unchanged. The fixed-witness peak changes
from 20.927519 to 20.927482 mm, about 0.000037 mm. This is not a meaningful
clearance or animation-quality result by itself.

The first optimizer return has minimum normalized motion/domain margin
-0.222723; its 1% backoff is feasible but worse than the warm start. The second
return has margin -0.464938; its 10% backoff is also feasible but worse. Neither
returned proposal is accepted by relaxing the constraints. The completed bound
return diagnostic attributes the exact violations below.

The selected exported GLBs independently replay with zero batch error for both
actors. All 148 original-clock poses have zero positional, angular-speed and
angular-acceleration violations under the existing comparison tolerances.
Actor B is byte-identical to the donor; actor A has changed:

- A: `50394eb7d02ba969fe08bf3a69451928541f8cb64e3dbba8ad2bbca5e595d8ce`
- B: `13adf945e5fe0537898c394106cabf94be21cfd0e0c409e61247c67ad9db2b5b`

The worker and bound return diagnostic both completed. All 43 matching hand
sample times were checked in both directions against the six-key donor. The
same 17 times fail: 42, 43 and 69 through 83. Peak penetration is 20.932823 mm,
only 0.000024541 mm below the donor. Three directional observations worsen;
the largest regression is 0.001667287 mm. No new failing time is introduced.
This is effectively unchanged collision quality, despite the extra controls.

The first returned proposal has 16 positional-acceleration, two angular-speed
and two angular-acceleration violations on the full original clock. Its worst
positional acceleration is actor A's left forearm at 1.991667 seconds:
8.395963 m/s^2 versus the original 6.866606 m/s^2 cap. The second return has two
positional-acceleration violations; actor B's left forearm reaches
16.139893 m/s^2 at 2.041667 seconds versus an 11.017452 m/s^2 cap. Other
motion categories pass for that return. These are actual decoded GLB results.

The selected peak vertices retain predominantly hand-joint skin weights
(94.17% for A's vertex 776 and 81.01% for B's vertex 6871). Skin weights do not
establish an anatomical diagnosis. Failure of this finite search does not
prove that contact correction is impossible.

The unchanged Studio candidate remains published with quality approval false.
This hand study has no full-body clearance, engine or human quality approval.

Bound local evidence:

- Main result: `reports/scene-pair-independent-hand-v1/result.json`.
- Fresh geometry SHA-256: `c8d27bcc5c27dbc920e5f23aadf3e072d9aeb13e17904b1f6c3f0247fcc8c400`.
- Diagnostic: `reports/scene-pair-independent-hand-diagnosis-v1/result.json`.
- Return audit SHA-256: `f03cc8c7a2b3469e30ed1d802f3b1a09dd49bace1db5620a6f755b64b553ac14`.
- Donor comparison SHA-256: `8b2d100b2199d6cd177526d03e793d35546cfb8a9c0fdf82d6f29e945ff630c7`.

## Numerical derivative audit

Before another optimization run, `audit_hand_derivatives.py` measured local
finite differences at unchanged and selected controls. It verifies bound study
methods and inputs, reproduces the saved selected objective and minimum margin,
and preserves its own method snapshot. Each point received 513 evaluations:
84 coordinate directions with positive/negative steps 1e-5, 1e-4 and 1e-3,
plus four deterministic multidimensional directions at radii 1e-4 and 5e-4.
No controls were selected or published by this audit.

At the selected controls and the solver's existing 1e-4 step, the maximum
forward prediction residual for depth/0.02 is 0.000677743, compared with a
maximum actual probe change of 0.000710417. In depth units these are about
0.013555 mm residual and 0.014208 mm change. Central differencing does not fix
this: its maximum residual is 0.000707924. The corresponding forward/central
coordinate derivative discrepancy reaches 1.624658. At zero controls, maximum
forward depth residual at that step is only 0.000001801358 (0.000036027 mm).
These are local probes of a fixed-witness surrogate, not fresh mesh results.

The audit also reports each original motion family, native and guide limits
separately. At zero controls the existing forward positional-acceleration
linearization misses two negative rows across the eight probes; central misses
none. This does not establish a universally better step or feasibility. Curvature,
nonsmooth norms/maxima and float32 quantization can all cause discrepancies.
No numerical tolerance has changed. Fifteen model-free diagnostic tests cover
affine predictions, quantization hiding a negative margin, nonsmooth norms,
invalid configurations and changing output populations.

Audit: `reports/scene-pair-hand-derivative-audit-v1/result.json`;
request SHA-256 `41fcec96bb3fc41a2dff45482feb7bb3f5883b3b5cea1f8d8385b3ea8346adb4`;
selected report SHA-256 `06231c50acb64711f5f17758186767c6baf289ff1712e3ad10dd8c95a3cf6856`.

## Individual witness epigraph

The prior solver constrained one scalar maximum across all signed witness
depths. Its next comparison uses `--individual-witnesses`: one inequality per
signed witness against a common nonnegative epigraph variable. This is the
same maximum-depth objective and feasible set, but finite differences no longer
operate on the maximum across witnesses. Negative signed depths remain allowed;
separated surfaces are not forced back into contact. The scalar measured peak
still ranks candidates and every original motion/domain constraint is retained.

The mode is persisted as `individual-signed-depths-v1` in the request. Legacy
runs retain their scalar mode. A changing witness population, nonfinite depths
or a scalar peak inconsistent with the individual depths is rejected. Tests
verify all rows, signed separation, competing witnesses under a physical limit,
and malformed populations. This does not remove all nonsmoothness or prove that
the next numerical search will converge.

The comparison keeps six native keys, 84 independent controls, zero and verified
warm starts, 100 iterations each, the same 43-time collision audit and all
original motion limits. Actual GLBs and fresh mesh queries remain the acceptance
evidence. No failed candidate may replace Studio or approve a release gate.


The connected comparison is running at
`reports/scene-pair-witness-epigraph-v1`. Both warm-start GLB replays are exact,
expanded support and guide checks pass, and all 86 original directional queries
were verified and reused. Request SHA-256:
`d4fcf8f23beada9d1e1a2d7f068067925fd82b0186681ed3cb0eb4c6c7d26f47`.
No final candidate result is available yet. The focused new/affected suite has
47 passing tests; the full minimal public Python suite has 721 passing tests.

```powershell
.venv/Scripts/python.exe -u scripts/fit_continuous_terminal_hand.py reports/scene-pair-terminal-hand-search-v1 reports/scene-pair-witness-epigraph-v1 --hand-orientation --independent-wrists --individual-witnesses --editable-keys 6 --witness-study reports/scene-pair-independent-hand-v1 --warm-start-study reports/scene-pair-independent-hand-v1
```

The derivative audit preceded the solver change and retains its original method
snapshot. Its strict replay requires those bound method versions; a later source
checkout is intentionally rejected when its methods differ.


## Individual-witness solve outcome; fresh geometry pending

Both 100-iteration starts reached status 9. The search recorded 17,637
observations, including finite differences, of which 90 passed the motion/domain
checks. Selected observation 8,867 changes only actor A's wrist X by another
6 micrometres at native time 1.991499066 seconds relative to the bound independent
warm start. Its fixed-witness peak is 20.927446 mm versus the donor's
20.927482 mm: about 0.000036 mm difference, not a useful clearance result.

The final proposals from the two starts reach lower fixed-witness peaks of
20.737698 and 20.737694 mm, but their minimum normalized margins are negative
(-0.000779853 and -0.000217156). Neither has a feasible tested backoff. They
remain rejected. The completed-return diagnostic must attribute the actual
motion violations after this worker finishes; optimizer margin alone does not
identify the joints or physical excesses.

The selected GLBs replay exactly for both actors, retain all frozen native keys,
and have zero positional/angular-speed/angular-acceleration violations over the
original 148-pose clock. Actor B is unchanged from the donor:

- A: `c180497b9e4a6e849dfb437fd0b6e81ec71495ab4af0bd3d86dbba6ef66626a1`.
- B: `13adf945e5fe0537898c394106cabf94be21cfd0e0c409e61247c67ad9db2b5b`.
- Selected record: `52782804487b3dbd4bf5e8bdd0dff668c73c8499ebbad05e27755262d86ed42a`.
- Solver returns: `e0f66624d24becab2e70479976137c040a29f231cb1f42e39e6921c36d97b4db`.
- Export audit: `c6cca0262345c9fab43ebffe2e32c2841b8a4994e985c0af6bc1867cb8cc5e8e`.

The existing worker is auditing all 43 hand times against fresh full partner
meshes. Its first two times still exceed the 5 mm threshold. Keep its loaded
methods unchanged until completion. No Studio replacement, full-body clearance,
engine acceptance or release approval follows from these partial results.
