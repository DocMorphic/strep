# Previous-key preference inside the original pose bounds

`KeyPose.solve(..., reference_controls=...)` optionally starts from an explicit
normalized edit vector and minimizes squared distance from that vector. This
allows successive pose proposals to prefer the preceding key's edit instead
of independently preferring zero at every key.

Each new `KeyPose` still measures rotation and joint-displacement inequalities
against its **original source pose at the current time**. A preceding key is
an objective preference, never a new source epoch, pose budget or motion-rate
reference. All current guidance planes, selected vertices and active point
contacts remain. Omitting the option retains the zero-reference behavior;
the native-key command and Studio do not automatically enable it.

References require a complete finite real vector inside the existing component
box. Invalid shapes, nonnumeric/nonfinite values and components outside that
box reject rather than being clipped or normalized. A feasible reference is
retained exactly, with independent returned storage. An infeasible reference
is optimized under the current original inequalities. A failed finite proposal
retains the original zero edits, not the preceding key's edits. Deadline
failures retain the existing exception behavior. Reference-conditioned records
include the supplied reference for provenance.

This is proposal guidance only. It does not enforce continuity, an anatomical
pose prior, original motion rates or geometry between keys. A complete decoded
curve must still pass every original motion, scene, engine and human-quality
condition before adoption. No accumulated source-relative edit or automatic
animation acceptance is introduced.

## Validation

The first affected selection reports **62 passed / one failed in 103.03 s**.
The failure is an invalid new fixture assumption: all its surface vertices are
influenced by the edited node, so it has no completely fixed surface vertex.
Production conditions are unchanged. The corrected failure test addresses one
real vertex with two contradictory unit-plane bounds and checks that a failed
reference-conditioned fit preserves the original rather than the reference.
That initial failure and method/test snapshots remain intact.

All **12 new reference cases** then pass in **4.61 s**, including the corrected
fixture, feasible-reference retention, infeasible-reference projection, exact
zero-reference/default equality for active and inactive guidance, caller
mutation, malformed inputs and failed-proposal retention. The **51 existing
affine/initializer/region cases** already passed in the original selection,
with the exact same production code. This is **63 distinct affected checks
passing across the recorded runs**, not one reported 63-pass invocation.

The original combined finalization/test guard completes with test-failure
status in **332.187 s**, peak **216,887,296 bytes**; all **327** resource
observations replay. Its geometry assembly independently succeeds and remains
saved. It is not rerun for the fixture correction. The corrected module's
512 MiB CPU guard completes in **21.235 s**, peak **124,948,480 bytes**; all
**23** resource observations replay. Records remain under ignored
`reports/high-five-imported-geometry-finalize-v1` and
`reports/native-pose-reference-tests-v1`.

The source inventories now declare **519 Python modules / 45 Node suites**;
contact/rig contains **83 Python modules / five Node suites**. This does not
establish a full source-inventory, model, animation, engine or release pass.

The [focused hosted run](https://github.com/DocMorphic/strep/actions/runs/38706794907)
at `ee9874c` passes all **12 new reference cases on each OS**: Ubuntu **1.41 s**,
Windows **2.62 s**. This module result is separate from the existing 51 cases
in the local affected selection and does not establish a full-inventory pass.
