# Contact-preserving approach and departure rate fitting

This experiment starts from the [native wrist retraction](native-wrist-retraction-v1.md)
that passes all 53 sampled inter-actor mesh checks but has sharp velocity changes
near contact. It releases the contact-adjacent key endpoints while retaining the
pose at the authored fractional time.

## Parameterization and constraints

Each of the three arm joints receives three whole-window rotation correction
knots and a contact angular-step vector: 36 scalar controls per actor. The five
time knots are the window start, halfway to contact, contact, halfway to the end,
and the window end. Original native clocks and protected interpolation support
remain unchanged. Outside the contact bracket, interpolate correction vectors
onto editable keys and compose them with the source local rotations.

For the two keys bracketing contact, instead use
`R_lower = R_contact exp(-fraction * omega)` and
`R_upper = R_contact exp((1-fraction) * omega)`.
The contact fraction follows the decoder's float32 key-clock subtraction.
Changing `omega` allows the approach/departure rate to change without changing
the mathematical contact rotation. Ambiguous shortest arcs are rejected.
Float32 export is measured separately; exact algebra alone does not prove that
the serialized pose or skin is preserved.

Use SLSQP for at most 120 iterations per actor, with each correction component
bounded to +/-0.15 radians. Hard proposal constraints keep the original 45-degree
arm key-angle budgets and selected-hand surfaces at least 0.45 mm behind their
respective midpoint planes at the inherited 102 declared times. These include
quarter native intervals and the unchanged 53 full-mesh guard times.

The **0.45 mm auxiliary clearance** differs explicitly from the preceding
0.5 mm half-gap surrogate. It leaves a positive 0.9 mm combined hand separation
while providing 0.05 mm per-hand numerical room for serialized optimization.
It does not change the authored 1 mm contact target, its tolerances, the original
full-mesh collision tolerance, or the original rate acceptance caps. The stricter
0.5 mm plane result is also reported rather than silently relabeled as passing.

The objective sums mean squared positive excesses of the four unchanged
original-reference rate caps. Scaling constants are 1 m/s, 10 m/s², 3 rad/s and
100 rad/s², with a 1e-6 squared-control regularizer. These are objective weights,
not realism thresholds. Initial rate feasibility is not assumed; a lower
objective may still fail every rate-cap group or worsen individual rows.

Skin projection uses every supplied weight and bind-space point, including the
second set of four influences. It combines those coefficients into a fixed-axis
projection matrix. A test compares this with direct full-weight skinning under
multiple nontrivial joint transforms.

## Serialized selection and independent audit

Try the fitted controls at full strength and eight halved strengths. Retain the
first whose float32 pose still passes proposal clearance and original angle
constraints, preserves contact matrices within 1e-6, and improves the unregularized
rate objective. Otherwise retain the source clip unchanged. This is a candidate
selection rule, not release acceptance.

Export and independently decode the selected GLBs. Check all original arm/finger
key budgets, native clocks, unselected channels, protected/outside-window poses,
actual contact surface points/normals, full inter-actor geometry at all 53 guard
times, floor depth and every original rate-cap group. No Studio promotion or
human-quality approval is inferred from optimization convergence or successful
export. Discrete geometry checks do not certify continuous collision freedom.

## Reproduction

```powershell
.venv/Scripts/python.exe scripts/study_contact_rate_path.py reports/native-wrist-retraction-v1 reports/<fresh-rate-fit>
```

This requires separately acquired character payloads and the completed local
provenance chain; the public repository contains no model weights or raw study
outputs. Reserved held-out prompts and the unchanged checkpoint are untouched.


## Completed results

Both fits converge (76 and 101 iterations) and their full-strength serialized
candidates pass the proposal constraints. Actor A's unregularized rate objective
falls from 0.160622859 to 0.081553251 (49.23%); actor B's falls from 0.217168004 to
0.077616053 (64.26%). Eight and eleven control components respectively reach
within 0.001 radians of the experimental +/-0.15-radian limit. This is bounded
local optimization, not a global optimality or infeasibility result.

All 53 independently decoded full inter-actor mesh samples pass with zero
detected crossings or vertex penetration. Contact gap is 1.000026 mm, anchor
errors below 0.000033 mm, and normal errors 1.002626/0.414840 degrees. Contact
matrix drifts are 4.802802e-8 and 4.453994e-8; bitwise contact identity is not
claimed. Original arm/finger budgets, clocks, unselected channels and
protected/outside-window poses pass. The auxiliary 0.45 mm plane checks pass;
the separate 0.5 mm half-gap comparison remains false. Floor penetration remains
6.003415 mm.

| Original rate cap | Failing rows before / after | Maximum excess before / after |
| --- | ---: | ---: |
| Position speed | 144 / 143 | 0.805754 / 0.416948 m/s |
| Position acceleration | 244 / 278 | 100.564291 / 65.514376 m/s² |
| Angular speed | 934 / 1,336 | 2.206688 / 2.206840 rad/s |
| Angular acceleration | 232 / 228 | 266.141848 / 229.029390 rad/s² |

All four cap groups still fail. More positional-acceleration and angular-speed
rows fail, and the angular-speed peak excess increases slightly. A lower scalar
objective therefore does not establish an overall quality pass.

The separate read-only turnaround diagnosis reproduces all rate counts and
maxima. The finite-difference marker velocity jumps at native key 42 fall from
0.816608 to 0.349037 m/s (A) and from 0.943106 to 0.449183 m/s (B). The largest
positional acceleration excess now occurs at the earlier approach, around
1.591667 s, on actor B's hand: measured 80.968954 m/s² against a 15.454567 m/s²
original cap. The largest angular-acceleration excess is also near 1.591667 s.
No failing rate rows occur outside the edited arm subtrees.

Next test a bounded continuation or enlarged proposal domain while retaining
the same original reference, angle caps, contact intent and full mesh audit.
The saturated experimental controls and the earlier remaining peaks justify
that test; they do not justify increasing the actual rate acceptance limits.
Keep individual rate regressions visible, not just the scalar objective.

## Evidence and validation

The fit binds 4,321 inputs, 93 methods and 60 outputs. The turnaround diagnosis
binds 4,475 inputs, 94 methods and two outputs. All inputs, outputs and archived
and current methods were rehashed without mismatches. Result SHA-256 values:

- Fit: `43f347bd15b49a94bdf1880c01117a747abf4ebfb36a9fcc8858d7415c726b9a`
- Diagnosis: `8e217ef7f5fda0d6bcf6f80d7df79415cca6a73e7f75e321a83853dcccd4b591`

Run the diagnostic with:

```powershell
.venv/Scripts/python.exe scripts/diagnose_native_contact_turnaround.py reports/<completed-rate-fit> reports/<fresh-diagnosis>
```

All 1,059 model-free source tests pass. New checks cover contact-preserving
endpoint freedom, serialized decoding, unchanged frozen keys, exact zero
controls, rejected ambiguous arcs and full eight-weight skin projection.
No model training, reserved held-out prompts, Studio promotion or release-gate
approval occurred. Human review remains outstanding.
