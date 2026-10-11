# Explicit permission to edit clip boundary keys

`strep-native-scene-edit-v2` adds a required `editable_clip_boundaries` list to
each actor declaration. Choose `[]`, `["start"]`, `["end"]` or
`["start", "end"]`. V1 recipes retain frozen boundary keys; V2 with `[]` uses
the same interior controls. Track rotation/translation and joint-displacement
limits remain unchanged. The original asset stays retained and selected.

Only an actual zero-time first key or exact final-duration key can be enabled.
The edit window must reach that clip edge. An internal window boundary or a
track ending before the shared clip duration is rejected. Protection remains
hard: an enabled boundary key may not affect a protected point or interval
anywhere within its interpolation support. Permissions are checked before
building controls, and original clocks and unpermitted values remain preserved.

Enabled boundaries receive control knots at their actual endpoints. The same
source-relative track bounds, decoded export checks, full-joint displacement
checks and original sampled motion caps apply. This does not raise those limits
or grant permission to change other tracks, geometry, duration or animation
populations. The existing solver's complete control/resource limits still apply.

`SceneEdits.audit` records allowed boundaries and the node/path/key/time of actual
`clip_boundary_changes`. It reports
`boundary_transition_compatibility_verified: false`. A measured edit can change
a clip's connection poses; seam, transition, contact and animator review are
separate requirements. An endpoint permission is not a quality approval.

The feature passes **132 tests**: 21 new boundary tests plus all 111 affected
contact, geometry, fit and surface regressions. Tests export actual translation
and rotation edits at start/end, compare decoded interpolation with the proposal,
retain original inputs/clocks/unselected tracks, verify legacy equivalence and
reject protected support, malformed opt-ins, internal windows and absent end
keys. Recorded resource admission/completion independently replays successfully.

This resolves a concrete authoring limitation exposed by the
[expanded Kenney ground scenes](kenney-ground-scenes-v2.md): some original clip
boundaries already penetrate the declared floor, so a recipe that freezes those
poses cannot clear the entire mesh. Boundary permissions enable a bounded
attempt; they do not prove that the allowed bounds contain a feasible correction.
Local evidence is retained in `reports/scene-boundary-source-checks-v1` and the
guarded job/resource records under `reports/central-hand-physical-v1`. Studio UI,
continuous-time safety, engine playback and release approval remain unverified.
