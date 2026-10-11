# Explicit scenes without point-contact targets

Native scenes now accept `contacts: []`. This allows whole-mesh floor or scene
clearance work without manufacturing an unrelated point target. All actor hashes,
selected animation indices, placement, shared duration and scene geometry remain
explicit. A missing contact list, `null`, a dictionary or a Boolean is rejected.
Nonempty requests retain the same contact definitions and limits.

The contact audit reports `point_contact_conditions_declared` and
`point_contact_intent_evaluated`. For an empty list these are `0` and `false`.
Its `passed` value means every **declared** point condition passed; for an empty
list this is vacuous and provides no hand, foot, support or interaction evidence.
The observations archive contains no fabricated contact measurements. Use the
separate source-bound geometry result to assess declared floor/object/partner
geometry, and retain contact-intent absence in review and downstream decisions.

For floor-only authoring, load the actor through
`scripts/native_scene_contacts.py:SceneContacts`, bind the exact scene JSON hash
in a `strep-native-scene-geometry-v1` policy and declare the plane and sample clock.
The existing `scripts/native_scene_fit.py` surface-vector path can then propose
changes within explicit `strep-native-scene-edit-v1` track/joint bounds. The
original remains selected; decoded geometry and motion/edit limits still decide
the measured result. No implicit floor or contact is introduced.

The change passes **111 tests** across the new eight-test suite and the existing
contact, geometry, fit and surface-model suites. New tests verify source/archive
retention, rejected malformed declarations, a real floor failure despite an empty
point audit passing, and actual serialized surface-fit runs for both clear and
impossible floor requests. The impossible request remains a geometry failure and
does not change original selection. Recorded resource admission/completion replays
successfully with the unchanged policy.

Local source-check evidence is retained in
`reports/geometry-only-scene-source-checks-v1` and its guarded job/resource records
under `reports/central-hand-physical-v1`. This is backend support. It does not
establish animator quality, floor-contact intent, balance, continuous-time
clearance, engine playback, Studio UI verification or release approval.
