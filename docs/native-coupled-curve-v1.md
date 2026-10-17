# Native-key coupled motion development

The [coupled contact study](native-self-separation-cuts-v1.md) finds a strict
single-pose candidate at 2 s. The next work is a native animation curve,
decoded validation and complete motion evidence. A passing isolated pose
does not establish an animation or transfer its approval to an exported file.

## Native-key save/reload probe

A diagnostic appends one animation per original actor GLB and edits only the
existing 2-s key (key 60 of 120). A has 22 controlled rotation tracks and B
23. It retains original translations/scales, mesh/skin/node declarations,
original animation objects, every native timestamp, the entire original
binary prefix and all other key values exactly. Source animation index 1
remains intact; the diagnostic uses appended index 2. This deliberately
abrupt neighboring motion is a codec probe, not a motion proposal.

Directly decoded worlds and all eight skin influences are checked against
the source pose. Maximum world-matrix element differences are 3.639636e-8
for A and 5.321447e-8 for B; maximum vertex differences are 5.655724e-9 m
and 1.986715e-8 m. Both root worlds remain exactly unchanged. All 6,131
contact/edit/support pose rows pass after decoding. One of the 171 search
guide rows fails, with minimum normalized value -1.048254e-7. This remains
recorded: the exported file does not pass the original all-row condition.

The decoded contact-frame gap/opposition/tangent errors are 4.997487 mm /
2.950925 degrees / 14.750262 degrees against unchanged 5-mm / 5-degree /
15-degree limits. Actual partner geometry and localized hand checks pass.
Complete 36,108-triangle-per-actor self scans retain A 131 / B 70 original
pairs, remove A 101 / B 65 and introduce zero. Inherited source defects
remain. Only one of the planned 2,017 geometry times is checked; rates,
complete-clock geometry, engine and human quality are unapproved.

The guarded diagnostic completes in 154.281 s at 182,845,440 sampled bytes;
all 152 resource observations replay independently. The saved raw source,
single-key outputs, numerical guide failure and guard traces remain separate.

## Native-clock control taper

`scripts/native_key_control_taper.py` weights explicit original-relative
rotation-vector controls on a supplied unchanged native clock. Its start,
peak and end must be existing keys. A quintic envelope uses seconds,
including nonuniform clocks, with exact zero controls outside/boundaries
and exact anchor controls at the peak. Weights stay between zero and one,
so normalized angular edit balls remain bounded at the supplied keys.

Input bounds are 3–4,096 increasing finite native times and 1–32 complete
finite three-component control vectors in their unit balls. The maximum
returned control array is 3,145,728 bytes. The helper preserves its inputs;
it does not recenter a reference or infer an anatomical range.

The underlying scalar envelope is C2. Encoded glTF uses its native
interpolation, so quaternion/world smoothness, subkey angular bounds,
displacement, motion rates, contacts and collisions still need separate
decoded checks. A tapered initializer is a proposal, not a physical result.

Twenty-four local tests cover exact peak/outside controls, readonly inputs,
nonuniform-time analytical values, clock subdivision, quaternion edit angles,
boundary behavior, the complete allocation bound and invalid inputs. The
guard completes in 18.281 s at 96,088,064 bytes; all 20 observations replay.
Inventories now contain 553 Python/45 Node suites, with 117/five in the
contact subset. These counts are not full-inventory passes.

Every moving proposal must retain original root tracks, endpoint keys and
timestamps, record full source-relative angular/displacement/rate results,
and include known geometry failure times before claiming broader success.
Original assets remain selected; this work changes no release criterion.
