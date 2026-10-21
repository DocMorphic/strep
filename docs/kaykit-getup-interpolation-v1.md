# Getting up interpolation constrained fitting

Both previously unresolved hand-contact windows now pass the declared sampled
floor, contact and correction-step limits, including actual Godot authoring
capture. The fitter constrains interpolated poses as well as native keys.
The four hand-contact windows studied so far therefore have locally passing
candidates across this and the [prior boundary study](kaykit-getup-boundary-feasibility-v1.md).
They are separate diagnostic clips; the complete getting-up animation and its
other boundaries remain unapproved.

## Interpolation and constraints

`surface_pose_interpolation.py` maps endpoint rotation edits to the pose produced
by native LINEAR quaternion interpolation. It uses shortest-arc interpolation,
the viewer's normalized linear branch for tiny angles, and analytic derivatives
through quaternion normalization and local rotation coordinates. The derivative
then composes with the existing complete-skin pose derivatives. Root translation
interpolates linearly in the checked parent basis.

The mapper requires matching same-rig edit layouts, rigid edited local rotation
bases, an unchanged root-parent basis at the declared samples, and source poses
consistent with native LINEAR interpolation. It rejects ambiguous half-turn
branches and sampled edits at the principal-log branch boundary. These explicit
restrictions avoid silently treating unsupported interpolation as equivalent.
Unedited hierarchy matrices, raw skin weights and homogeneous inverse binds
remain in the complete geometry calculation.

`SampledPoseWindow` composes the existing coupled key constraints with explicit
interior pose constraints. Floor optimizer rows may grow between calls, while
candidate ranking and acceptance retain every vertex. The study starts with
quarter, half and three-quarter samples. Its driver can add failed dense-clock
samples after a solve; neither successful window needed that recovery path.
No continuous-time or anatomical guarantee follows from the sample set.

## Verification before fitting

Eighteen focused tests pass. They compare complete skin geometry with independent
native quaternion interpolation and finite differences at interior fractions and
both endpoints. Coverage includes zero/tiny angles, antipodal quaternion signs,
the combined constraint Jacobian, duplicate samples, invalid parameter
populations and explicit rejection of unsupported bases/interpolation.

On the actual 4,858-vertex character, eight independent directional checks at
each of three interior samples in each of two windows provide 48 comparisons.
Maximum derivative disagreement is 5.695e-10. Complete geometry agrees with
separate native interpolation within 1.356e-15 m. These checks precede fitting;
they are not inferred from optimizer convergence.

## Saved outcomes

The original contact phases, material points, targets, 5 mm floor tolerance,
20 mm point-contact tolerance, root/rotation edit budgets and 25 mm/5 degree
correction-step limits remain unchanged. Small interior fitting reserves remain
separate from acceptance. The starting controls are the prior coupled proposals,
not a changed target set or newly generated motion.

| Native keys | Previous sampled floor peak | New sampled floor peak | New contact peak | Root correction step | Rotation correction step |
|---|---:|---:|---:|---:|---:|
| 67–68 | 7.910124 mm | 4.007711 mm | 19.000007 mm | 8.220681 mm | 4.999429 degrees |
| 124–125 | 11.183870 mm | 4.507066 mm | 19.000032 mm | 13.385635 mm | 4.999430 degrees |

Each window succeeds in its first optimizer call: 46 and 30 iterations,
respectively, with successful optimizer status. The validation clock combines
eighth-interval samples with a uniform 960 Hz clock inside each native interval,
yielding 39 and 41 observations. Decoded GLBs independently pass every declared
pose and endpoint-step limit. Maximum whole-mesh serialization disagreement is
5.407e-8 m. Only the specified two keys change in each full source clip;
all other channel values, native clocks, mesh, skin and original binary prefix
remain unchanged. Outside-window boundaries have not been approved.

Independent replay reproduces the saved floor/contact measurements. Actual
Godot 4.7.2 native-authoring capture includes the union clock plus zero and the
exact clip endpoint: 82 times and 164 actor observations. Both windows pass
floor/contact checks in Godot. Pose and skin agreement pass, with maximum skin
disagreement 0.028041 mm. This verifies the authoring-resource path, not ordinary
playback, physics, GPU skinning or human-rated realism.

## Evidence and next work

Local reports are `reports/kaykit-interpolation-derivatives-v1`,
`kaykit-getup-interpolated-fit-v1` and `kaykit-getup-interpolated-engine-v1`.
All three resource traces replay, covering 124 observations; peak observed
worker-tree memory is 167,628,800 bytes. The existing memory guard is unchanged.
Both CI inventories include the new test file. The full suite was not rerun.

The derivative result SHA-256 is
`0a19326866811c2997c389b1a35817986d3e05860a6066bbaf1afab2d819efcf`.
The fitted result SHA-256 is
`e16a000b9ae491fd0da63a5c1321bac25ebb734b46dd283737e0393db81e3e70`.
The actual engine result SHA-256 is
`04aac670e42fe688263f16d3d1098f08dc506e116a85c8231f2abbc912c54eeb`.

Next, extend correction across the full clip while preserving already validated
incoming intervals. A local solve must include its changed boundary geometry;
independently successful windows cannot simply be stitched together and called
a passing animation. Retain checkpoints and failures, then validate every
native interval and the full engine export. Self-collision, anatomical support,
semantic correctness, visual review and cleanup time remain separate release
requirements. The broad project goal stays active across all motion families,
rigs, object/partner actions, style and editing controls.
