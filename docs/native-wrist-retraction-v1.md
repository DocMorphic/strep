# Native wrist clearance and remaining contact turn-around

This continues the [contact-preserving native path](contact-locked-path-v1.md).
That export retained the authored contact but collided at three of 53 guard
times. The present export passes all 53 inter-actor geometry samples. Motion-rate
checks still fail, so this is a geometric correction, not an accepted animation.

## Correction protocol

Freeze the two native keys bracketing the fractional contact instant, in addition
to existing protected spans and outside-window support. Only edit common-clock
upper-arm, forearm and wrist rotation keys. At each editable key, move the wrist
along the fixed outward retraction direction while retaining its orientation,
rigid bone lengths, local translations and finger transforms. Check the original
45-degree arm budgets, without resetting their reference.

Use all original guard times plus quarter native intervals: 102 plane samples
per actor. For a violated hand half-space, distribute the required extra wrist
translation to the influencing editable keys, with a 0.1 mm proposal reserve.
Limit cumulative additional translation to 20 mm and refresh actual interpolated
skin using float32 quaternion keys. Backtrack unreachable, over-budget or
non-improving steps; stop after at most eight updates. This is a bounded local
correction, not a smoothness optimizer or a proof of feasibility.

Every sample with editable support must pass its unchanged half-space test.
Frozen samples are reported separately, never relabeled as passing. Independently
decode both exported GLBs and check all original arm/finger budgets, contact,
clocks, unselected channels, protected/outside poses, the full mesh guard set,
floor penetration and all original motion-rate caps.

## Completed result

Actor A needs one refreshed step and at most 3.640390 mm additional retraction;
actor B needs two steps and at most 6.720503 mm. All 85 editable plane samples per
actor pass. Of 17 frozen samples, actor A retains two plane excesses of about
120 and 31 nanometres, and actor B retains one of about 100 nanometres. The strict
whole-plane result remains **false**. Full inter-actor meshes nevertheless pass
all 53 original guard samples, with zero detected crossing pairs or contained
vertex depth. Sampling does not certify continuous collision freedom.

Contact is bitwise unchanged from the source native export: 0.999987 mm gap,
anchor errors below 0.000045 mm, and normal errors 1.002628/0.414843 degrees.
All original arm/finger native-key budgets pass. Native clocks, unselected
channels, protected spans and outside-window poses remain exact. Maximum floor
penetration remains 6.003415 mm.

| Original-reference cap | Failing rows | Maximum excess |
| --- | ---: | ---: |
| Position speed | 144 | 0.805754 m/s |
| Position acceleration | 244 | 100.564291 m/s² |
| Angular speed | 934 | 2.206688 rad/s |
| Angular acceleration | 232 | 266.141848 rad/s² |

Several rate excesses worsen compared with the source. No Studio promotion,
human-quality approval, self-collision certificate or engine validation follows
from the mesh result. All release capability gates remain unapproved.

## Why smoothing must include contact-adjacent keys

A separate read-only diagnosis reproduces the saved rate counts and maxima.
All failing rows are within the edited arm subtrees. The largest positional
acceleration is actor B's forearm at 2.091667 s: 111.581754 m/s² against the original
11.017452 m/s² cap. This locates the current worst spike near contact.

One-sided finite differences, using a 10 microsecond step around native key 42
at 2.091722488 s, estimate the selected marker's outward-normal velocity:

| Actor | Before key (m/s) | After key (m/s) | Full velocity jump (m/s) |
| --- | ---: | ---: | ---: |
| A | 0.000066 | -0.806012 | 0.816608 |
| B | -0.023728 | -0.908968 | 0.943106 |

The native key lies about 0.107 microseconds before the authored contact time.
These are finite-difference diagnostics of this clip, not analytic derivatives
or a proof that no feasible smooth path exists. Freezing both contact-bracketing
keys preserves the pose but also freezes the post-contact segment. The next
experiment should permit those endpoints to change through the existing
contact-preserving rotation parameterization and constrain approach/departure
rates alongside actual skin clearance. Do not simply smooth the clear poses
and assume the resulting interpolation remains clear.

## Reproduction

```powershell
.venv/Scripts/python.exe scripts/study_native_wrist_retraction.py reports/contact-locked-path-v1 reports/<fresh-retraction>
.venv/Scripts/python.exe scripts/diagnose_native_contact_turnaround.py reports/<completed-retraction> reports/<fresh-diagnosis>
```

These require the local completed studies and separately acquired character
payloads. Large raw outputs remain ignored. The correction binds 4,169 inputs,
91 methods and 60 outputs, all rehashed without mismatch. Its result SHA-256 is
`6608918219231de171a4aaff367abcb23012d79f6e11e45f94daaf8ea827aadd`.

All 1,056 model-free source tests pass, including exact contact retention,
native-clock sampling, isolated shared samplers, nonlinear refresh, proposal
caps and rejection of unreachable/over-budget corrections. No model training
or reserved held-out prompts were used.

The separate turnaround diagnosis binds 4,321 inputs, 92 methods and 2 outputs. All hashes were checked; result SHA-256: `0ba046ac4e428e5516728a9e3bfae77bfc276accb40eade493fe2949a5fb42e1`. It modifies no animations.
