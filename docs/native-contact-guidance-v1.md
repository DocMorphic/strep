# Authored contact-normal guidance

`scripts/native_contact_norms.py` supplies orientation and facing-side proposal
rows to `surface-vector` native fitting when an explicit surface policy is
present. Existing authored vertices, contact clocks, scene placements, source
motion caps and edit permissions remain unchanged. The separately decoded
surface-contact audit and complete sampled mesh audit decide final acceptance.

```powershell
.venv\Scripts\python.exe scripts/native_scene_fit.py contacts.json permissions.json reports/guided-fit --proposal-model surface-vector --geometry-policy geometry-policy.json --surface-contact-policy surface-policy.json --resume-from reports/completed-fit --iterations 2 --restoration-steps 3
```

The starting clip must pass all original point/motion conditions. It may fail
the added surface policy. Missing or unreliable incident-face normals reject
guidance rather than substituting an inferred anatomical direction. Complete
pose and row populations are required; exceeding either explicit budget rejects
the operation without returning a subset. The initial guidance study predated primitive geometry integration. Current
`surface-vector` fitting supports declared boxes, spheres and cylinders through
[whole-triangle and enclosure guides](native-object-guides-v1.md), with object
poses fixed while permitted actor tracks change. Transformed normal rows alone
do not establish a working grasp or a complete object-correction workflow.

## Proposal and acceptance

For unit surface normals `nA` and `nB`, the orientation row uses vector `nA+nB`
with cap `2*sin(maximum_opposition_error/2)`. This expresses the authored normal
opposition condition without an angle derivative. Two signed side gaps use
`dot(nA, pB-pA)` and `dot(nB, pA-pB)`, each shifted by the exact authored backface
allowance. Their affine conversion uses the existing bounded scalar-to-norm
lift. Normals include every incident posed triangle; centroid groups count the
union of faces once. Winding-derived normals are not anatomical annotations.

The base rows are anchored to decoded poses. Continuous finite differences only
guide local proposals. Original point and motion rows remain hard conditions;
restoration margins never loosen their final decoded limits. Every tested
control vector, including rejected backoffs and restoration attempts, receives
saved exports, a complete mesh audit and a surface-contact audit.

Actual step acceptance requires all original decoded point/motion conditions to
pass, the existing lexicographic geometry score not to regress, and both surface
error aggregates not to increase: maximum positive normalized residual and sum
of squared positive residuals. At least one objective must improve. Current
fitting also protects every individual contact condition: a passing row stays
passing, and a failed row cannot increase its excess. Separate duplicated
proposal bounds guide this requirement without changing the authored caps or
final audit. See [individual contact protection](native-contact-guards-v1.md).
Geometry count tradeoffs remain possible under the existing depth-first score.
The final native acceptance flag still requires the complete authored surface
policy to pass.

## Retained high-five experiment

This initial experiment used aggregate contact acceptance, before individual
protection was added. It resumes the prior 35-primary-iteration clip against the exact
original source and policy bytes. It attempts two further primary iterations
with three restoration solves available per iteration. It accepts one half-step
in the second iteration. The first iteration's proposals either exceed unchanged
source limits or increase maximum penetration. No floor rise, weight-conditioned
mesh, new generated seed or training is applied.

| Measurement | Start | Retained half-step |
| --- | ---: | ---: |
| Contact point separation | 25.9743 mm | 25.3787 mm |
| Maximum partner containment depth | 20.7519 mm | 20.4773 mm |
| Proper surface crossings | 478 | 488 |
| Vertices deeper than 5 mm | 396 | 395 |
| Failed sampled geometry conditions | 7 | 7 |
| Normal opposition error | 39.1619 degrees | 39.2352 degrees |
| Source facing-side projection | -25.5183 mm | -24.6960 mm |
| Target facing-side projection | -21.0228 mm | -20.8870 mm |
| Maximum positive surface residual | 5.00366 | 4.83920 |
| Squared positive surface residual sum | 44.34132 | 42.51492 |

All original point/motion conditions pass. Added surface conditions and complete
sampled geometry still fail; originals remain selected. The 15-degree opposition
limit and 0.5 mm backface allowance are explicit prototype authoring choices,
not frozen release targets. Increased crossing count and opposition error stay
visible. Cumulative primary iteration count is 37 attempted iterations, not 37
accepted steps.

Replay checks all 20 saved control vectors and 40 byte-exact exports, unchanged
original cap arrays, complete decoded geometry and contact-error aggregates,
and all acceptance/rejection decisions. Pose samplers, incident-normal helpers
and geometry classifiers remain shared; replay does not independently prove
continuous collision freedom, anatomical meaning, GPU or runtime behavior.

Local evidence is retained under
`reports/native-oriented-surface-fit-development-v1/high-five/verification-v1/`
and `reports/native-contact-guidance-validation-v1/`. Generated characters,
study payloads, credentials and models remain excluded from GitHub. Public CI
includes guidance regressions on Linux and Windows. All 440 focused model-free
regressions pass, including 17 new guidance cases. No checkpoint is trained or
changed, no formal held-out trial is consumed, and no quality/release approval
is inferred. Next work must address individual error tradeoffs and reviewed
contact semantics before broad interaction quality claims.
