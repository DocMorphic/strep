# Conditional contact-force and palm-patch assessment

Strep now checks whether declared rigid-object contacts can supply the force and torque required by an existing object trajectory. This is a physics component for object handling and future capacity-aware correction; it does not change the generated character or certify realistic animation.

`scripts/contact_force_balance.py` accepts a world force, torque about the center of mass, and up to sixteen explicit contacts. Each contact supplies a COM-relative world lever, unit inward normal, Coulomb friction coefficient and maximum **total force magnitude** in newtons. Normal force is nonnegative; tangential force lies in the circular friction cone. A point contact supplies no independent twisting moment. These contact/wrench conventions follow [Modern Robotics, friction and wrench cones](https://modernrobotics.northwestern.edu/nu-gm-book-resource/12-2-1-friction/).

The bounded Clarabel 0.11.1 solve proposes forces in normalized coordinates; all forces are remeasured in original newton/newton-metre units. Acceptance requires every original normal, friction and capacity condition and all six force/torque components. Solver status alone cannot pass. Separate analytic necessary bounds test each wrench axis and complete wrench projections, including coupled moment limitations. Solver dual directions can propose a projection, but exclusion requires independently checking that projection against the original capped contact cones. Passing separate axis bounds is insufficient. Tolerances are explicit numerical accuracies, not calibrated animation-release thresholds. Inputs and operations are bounded; nonfinite or overflowing witnesses cannot pass.

`scripts/audit_object_contact_forces.py` freezes a world COM trajectory, local contact schedule, physical assumptions, support phases, masses and method sources into a fresh ignored output. It uses the existing rigid-object inverse dynamics and original sample clock without smoothing. Unknown support phases and cross-phase derivative stencils remain in the output but unassessed; endpoints have no estimate. Contact levers/normals follow the original object orientation. Free flight cannot overlap a declared support contact, including at an unestimated endpoint. Missing contacts during a known supported phase are assessed rather than skipped. Uniform solid-box COM/inertia assumptions are required explicitly; they are not measured from a character.

## Matched development experiment

Two already exposed failed box-attachment tracks, seeds 11 and 22, each contain 180 keys at 30 fps. Grasp is frame 60 and release frame 121. Assess all 59 supported interior samples, frames 61–119, for each of three hypothetical masses: 1, 5 and 20 kg. Preserve all 119 unassessed derivative samples and both endpoints per case. Neither this study nor the mass values are held out or measured human-strength data.

Compare two declared contact models on **identical positions, rotations, clock, complete required wrenches, masses, uniform-box inertia, gravity, friction and support phases**:

- Original point model: each original scene grip target on the box's ±X faces supplies one inward-normal point contact, friction 0.5 and a hypothetical 100 N total-force cap per hand.
- Finite-span approximation: two points per hand, ±2 cm along local box Z around that same target. Each point has a 50 N cap, retaining the original 100 N summed force-magnitude budget per hand. This fixed budget partition is a specific hypothetical model; it does not discover an actual skinned palm patch or permit unrestricted redistribution of the hand budget.

| Track | Mass | Original point-model feasible samples | Finite-span model feasible samples |
|---|---:|---:|---:|
| Seed 11 | 1 kg | 0/59 | 59/59 |
| Seed 11 | 5 kg | 0/59 | 18/59 |
| Seed 11 | 20 kg | 0/59 | 0/59 |
| Seed 22 | 1 kg | 0/59 | 59/59 |
| Seed 22 | 5 kg | 0/59 | 21/59 |
| Seed 22 | 20 kg | 0/59 | 0/59 |

All 354 original point-model assessments are excluded: 236 by complete wrench projections and 118 by axis bounds. The finite-span model has **157 independently verified conditional force witnesses**, 79 projection exclusions and 118 axis exclusions. The 1/5 kg differences demonstrate a moment limitation of the chosen contact model. The 20 kg cases exceed a necessary force bound under the stated friction/caps. These are conclusions about declared models, not general claims about what a human can lift. No character pose, object trajectory or learned checkpoint changes.

Three fresh Torch-free audit phases bind 67 immutable source/artifact files, reconstruct both complete populations with separate translation differences, body/world inertia calculations and angular friction-support formulas, check all feasible force witnesses/exclusions, and verify matched clocks/wrenches/contact centers and unchanged hand budgets. Force reconstruction differs by at most 1.002e−12 N and torque by 8.882e−15 Nm. Historical method snapshots are checked independently of current producer files so future source changes do not invalidate the original raw study. Earlier audits remain immutable. A subsequent zero-contact JSON handling fix does not change either studied nonempty contact branch.

The point-model worker completes in 5.203 guard seconds (sampled peak 75,370,496 bytes; seven resource observations). The finite-span worker completes in 6.266 seconds (78,725,120 bytes; eight observations). The final three-phase audit completes in 7.360 seconds (105,631,744 bytes; nine observations). Every resource record independently replays. These bounded, at-most-48-force-variable jobs use a separate 512 MiB estimate plus the unchanged 600 MiB reserve. They do not reduce the full native/affine contact-study estimate of 2 GiB plus reserve.

## Validation and use

**82 focused tests pass in 2.95 seconds** across force feasibility, the immutable object-force workflow, existing rigid dynamics and geometry. Coverage includes normal/friction/total-force limits, coupled moment infeasibility, finite-span twisting with unchanged budgets, false solver success, overflow, malformed assumptions, unknown/boundary accounting, contradictory free flight, JSON zero-contact replay, mutation detection, fresh-output protection and close-but-distinct mass filenames. All nine final test resource observations replay. CI now declares 427 Python test modules and 41 Node suites, adding the two new suites and the two previously unlisted dynamics/geometry suites. Hosted CI for these new changes is separate from earlier successful runs.

Use pre-acquired local dependencies; this is not a bundled offline installer. Save an explicit `strep-object-contact-force-spec-v1` specification and a world COM track, then run through the owned supervisor:

```powershell
.venv/Scripts/python.exe scripts/run_guarded_job.py --worker scripts/audit_object_contact_forces.py --output reports/my-force-guard --expected-rss-mib 512 --stable-seconds 3 --admission-seconds 600 --max-seconds 600 -- reports/my-object-track.json reports/my-force-spec.json reports/my-force-assessment
```

The specification requires `masses_kg`, `gravity_m_s2`, complete `phases`, explicit `contacts`, provenance in `assumption_notes`, force/torque tolerances and a per-sample solve budget. Contacts specify `point_from_com_local_m`, `normal_into_body_local`, friction, total-force cap and start/end frames. The implementation and its tests provide complete examples. A fresh output is required; interrupted/failed outputs remain separate.

The next physical step is to connect **verified actual hand patches and calibrated capacity profiles** to correction, then add character reaction/whole-body and joint dynamics. Slipping/impact contacts need their own models. Do not map these hypothetical caps to a gameplay strength score, train on these conditional positives as clean human motion, or call them release-approved lifting. Force balance, per-joint dynamics, style and transition release gates remain unfrozen. Existing native contact passes remain 0/62, the 0.03 continuation/schedule stays current, all fourteen capabilities remain unapproved, and real review/cleanup data are still absent. Continue the full project-wide goal.

Private receipt digests:

- Point-model study: `ca77860cb488d54ec9d31a9f0d4a930866493b2f52fe76261a4a3db675cf99a5`.
- Point-model independent replay: `972e41a42585c49678f06601619e8a8891ee2676c1de7ad2e60493640abaf25f`.
- Finite-span study: `b4f2fc16b7980f5ba3595d1fc06fea4c3696f34c41b39f392701909c9d3e53b8`.
- Finite-span independent replay: `b225629169a9b59ae7ce5c9671019037b9cabc58b109626528d8fd641434a433`.
- Independent matched-model comparison: `1aa236c5cce188cb73957b771e96a8693647f470652fe052e4d5bff3cdcd03cf`.
- Three-process audit execution: `7b526e0a3055650e937f52e5e55d86833a0cc7de42b831d82cffc11359161c29`.
