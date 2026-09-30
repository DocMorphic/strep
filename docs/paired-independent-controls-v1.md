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
The next comparison keeps its exact six-key clock, original 120 Hz support and
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


The real worker is now in optimization. The verified warm-start replay has
exactly zero error for both actors; expanded-support motion and guide checks
pass. All 86 directional source queries were verified and reused. Both starts
have 84 controls, and imported method hashes match the working source. The
request hash is `8e63f4948ebd1e3038869a5ba3f4bb34c3f5d9f4995dde933f19e643f86352b7`.
Fresh selected geometry and final exported-motion checks remain pending.
