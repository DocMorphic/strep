# Foot-support fitting from native review candidates

The developer correction review panel now uses the existing foot-support
fitter directly on a checked native candidate. A transfer to a separate test
character is no longer required before fitting. Successful conversion produces
a native SOMA77 NPZ that can be selected, previewed, annotated and packed in the
same review workflow. This connects existing components; it does not claim a
new learned model or release-quality contacts.

## Workflow

1. Load a native review packet and segment. Build its candidate preview, or save
   a [timed native edit](native-timed-authoring-v1.md), which builds one.
2. In **Native foot supports**, choose **Use selected native candidate**.
   The known native skeleton supplies the root and six leg-role identities;
   the exact source GLB clocks and identity checks remain visible.
3. Enter explicit stance seconds, frozen boundary keys, a unit plane normal and
   plane offset, clearance/gap, ankle-displacement and angular limits. Add one
   or more intervals. A window needs at least three interior native keys.
   Same-foot edit windows cannot overlap.
4. Try correction. The original smoothing method remains the default; decoded
   between-key refinement is still an explicit, bounded eight-iteration choice.
   Compare the source and all retained proposals, including failures.
5. **Use candidate in native review** explicitly selects the converted result.
   It must belong to the currently selected draft, item and parent candidate.
   Review contacts, cleanup time, quality judgments and rights again before
   packing or saving decisions. Undo can restore the previous candidate.

No support result is selected automatically. The support editor uses its own
DOM namespace in the review panel and retains the existing character-editor
instance. Changing or closing review packets resets its binding and unloads
its comparison frame. Saved jobs remain inspectable. In-memory requests ignore
late bindings; the candidate callback rejects another source, busy operations
and duplicate use while selection is pending.

## Source and conversion checks

`native_review_support.py` resolves only complete hash-matching candidate
previews. It revalidates the original draft and candidate hash, native skeleton
identity, archived export methods, all pose channels and the exact FP32 30 fps
clock. Every preview joint transform must match the bound native NPZ within
1e-5 matrix elements. Known SOMA role names map to its explicit native joint
identities; this is not anatomical inference for arbitrary imported rigs.

`studio_native_support.py` accepts this source through the existing
`native_review` variant. Host/Origin, JSON/body-size and shared-worker dispatch
remain the existing support route's guards. Each job snapshots the checked
GLB, authored specification, parent native selection and bridge methods.
The wrapper verifies source, archive and current method bindings around fitting
and conversion. Generated evidence stays under ignored project reports.

The existing fitter proposes leg rotation changes only. Conversion requires
the original native mesh, skin, materials, node identities, binary payload,
translation tracks, duration and rotation clocks to remain unchanged.
Rotations outside the specified leg chains are rejected. Only individual
changed quaternion keys are reconstructed into native FP32 matrices; untouched
keys, other joints and the entire root trajectory copy the native source
exactly. The world reconstruction must match the fitted GLB within 1e-5 matrix
elements. The original-relative native authoring budget is checked again.

Conversion then re-exports a checked source-character preview and independently
audits that serialized preview. It rechecks foot-region plane heights, authored
ankle displacement/local rotation limits and full 120 Hz source-relative motion
rates. A pre-conversion fit passing does not substitute for this check. Native
budget or serialized-screen failures retain the actual source and keep the
failed native proposal, its preview when available and measured diagnostics.
The final selected preview gets its own serialized audit.

These are sampled foot-region support checks. They do not establish whole-sole
planting, horizontal foot locking, correct semantic stance timing, balance,
forces, self-collision, continuous collision or perceived realism. Authored
support events describe targets, not measured physical contact. No predicted
foot-contact labels are inherited into the NPZ or review form. Quality,
training admission and release approval remain false.

## Verification and measured limits

The focused CPU selection passes 212 tests. New synthetic tests cover exact
native source identity/clocks/roles, changed source and method rejection,
root and untouched-key preservation, unknown contact labels, unsupported joint
changes, translation/clock/mesh/payload mutation, cumulative bounds and native
serialization. A component test uses explicitly mocked passing screens to
exercise selection; it is not physical validation. A separate real serialized
audit overrides a mock fitter's passing claim and retains its failing source.
The actual wrapper also retains an unreachable synthetic case with every
trial's reason. DOM tests exercise the second editor namespace, explicit
source-bound use, retained failures, cleared review fields and undo.

The broader geometry/Studio selection passes all 1,648 Python tests and 15
JavaScript suites, including reproducible bundling and unique DOM identities.
The CPU CI job now uses the existing pinned model-free requirements plus
safetensors and CPU Torch, covering process inspection and thread-pool control
needed by the native support wrapper.

The terminal development canary runs four explicit support requests on prior
numerical native candidates: wave, kick and crawl against the Y=0 plane, plus
a wave target at Y=0.5 m. Timing windows are deliberately chosen numerical
intervals, not reviewed stance labels. These source candidates come from the
previous three-degree forearm/.01 m root authoring demonstration, rather than
a fresh generation or untouched benchmark population. All four retain their
input and all selected support screens remain false:

| Case | Source lowest-height range | Outcome |
| --- | --- | --- |
| Wave, floor | -2.034 to 0.457 mm | Four completed proposals fail motion-rate gates |
| Kick, floor | 3.894 to 7.545 mm | Four completed proposals fail motion-rate gates |
| Crawl, floor | 22.047 to 90.238 mm | Four proposals reject unreachable displacement |
| Wave, raised target | -502.034 to -499.543 mm | Four proposals reject unreachable displacement |

All 16 trials and their reasons remain available. No corrected motion was
accepted; neither a completed wrapper nor a passing export hides that result.
Every selected native root, boundary pose and retained-source rotation matches
its input exactly, and no contact labels are inserted. Godot 4.7.2 imports all
four clips/480 native frames with 77 bones, one skinned surface and loop mode
zero; all native-time joint samples agree within about 8.95e-7 metres and
9.80e-7 basis elements. Source and method hashes remain unchanged.
No actual browser/GPU rendering, human review or model improvement is established. The current scope remains a reusable native authoring and
review path. Real licensed reviewed corrections, demonstrated model training
and improvement, partner/object contacts, rig transfer and full human release
validation remain unfinished. All release capabilities stay unapproved and
the single full-project goal remains active.
