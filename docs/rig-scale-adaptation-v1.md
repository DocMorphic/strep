# Explicit static-rig scale adaptation

`scripts/rig_scale_adaptation.py` creates a separate rigid-transform derivative
of a static, self-contained rigged GLB. The original rig importer keeps its unit
scale checks. Original source bytes are copied beside the derivative; failures
retain their source and failure receipt. Existing animation is rejected rather
than discarded or claimed preserved.

The adapter keeps default joint origins in world space and obtains a proper
rotation from each positive, nonsingular world basis. It rebuilds rigid local
transforms along the original hierarchy. For joint `j`, the derivative inverse
bind is `inverse(new_world_j) @ old_world_j @ old_inverse_bind_j`. This preserves
the default skin matrix before float32 serialization. Unskinned instances get
separate derived meshes, including transformed normals/tangents. Original mesh
records, material metadata, accessor/view records and binary prefixes remain.

This changes the deformation representation. Default shape preservation does
not prove equivalence under arbitrary future rotations. Animated rigs, morphs,
reflections, local shear and unsupported encodings remain rejected. Positive
nonuniform parent/child TRS and resulting world shear are handled at the default
reference pose. Inputs are bounded to 32 MiB, 512 nodes, 256 skin joints,
64 instance primitives and 250,000 instance vertices.

Use an environment with Strep's CPU dependencies:

```powershell
python scripts/rig_scale_adaptation.py your-character.glb --output reports/your-character-adapted
```

The output folder must be new. It contains `source.glb`, `character.glb` and
`result.json`. Default geometry must remain within the explicit 10-micrometre
preservation bound. This is an adaptation check, not a calibrated motion-quality
or release limit. The generated derivative can then be imported through the
existing rigid GLB path with a reviewed anatomical profile.

Twenty-three generated-fixture checks pass, covering uniform/nonuniform scale,
world shear, nontrivial bind shape, eight influences, missing inverse binds,
static mesh instances, surface bases, metadata/payload retention, unsupported
inputs and failure retention. The completed resource trace replays 19 samples.

The actual Kenney development derivative passes strict intake with 45 skin
joints and 1,029 mesh vertices. Production reference error is
2.0465024928613146e-7 m. Separate quaternion/hierarchy evaluation and blended
skin-matrix arithmetic reproduce 2.046502492693834e-7 m; maximum joint-origin
error is 1.9121672753218598e-15 m. Original geometry and hierarchy remain bound.
Both adaptation resource traces replay 19 observations. This verifies the
converted GLB's default shape, not the original FBX conversion's equivalence.

Seven unchanged seed-77 development motions then transfer with one fixed profile.
Complete replay covers all 1,020 keys and 1,029 vertices per key, preserved target
payloads, root sidecars and floor diagnostics. Maximum serialization vertex
error is about 0.545 micrometres. Producer/replay resource traces reproduce
51/24 observations. There is no new generation, per-motion fitting, automatic
floor lift, engine playback or human-quality approval.

| Motion | Keys | Peak serialization error (micrometres) | Maximum mesh depth below Y=0 (mm) |
| --- | ---: | ---: | ---: |
| Jump/land | 120 | 0.192 | 0 |
| Crawl | 120 | 0.280 | 263.015 |
| Dance | 150 | 0.140 | 0 |
| Wave | 120 | 0.139 | 0 |
| Kick | 120 | 0.129 | 49.728 |
| Get-up | 180 | 0.223 | 662.041 |
| Run/roll/stand | 210 | 0.545 | 978.276 |

Successful transfer and replay coexist with substantial ground failures.
Zero floor depth does not establish planted feet, correct action, good timing or
realism. These are reused development clips, not held-out release trials.
The next step is to compare source and target ground behavior, identify the
transfer contribution, and correct contact using actual mesh geometry and
explicit support constraints. Preserve the baseline; a blanket vertical lift
would not prove a usable motion. All release capabilities remain unapproved.
