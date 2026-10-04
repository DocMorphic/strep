# Native edit support at contact times

`scripts/native_contact_support.py` identifies contact clocks where the declared native edits cannot alter either involved actor. A failing source condition at such a clock cannot be corrected with that edit setup. Detecting this before optimization prevents an impossible endpoint target from being mistaken for a weak solver.

For each permitted LINEAR rotation or translation channel, the diagnostic marks native keys with any nonzero control weight as potentially mutable. An exact key uses only that key; an interior sample uses both neighboring keys, and out-of-channel times clamp to the endpoint key. A pose is classified fixed only when every declared track for that actor has unchanged contributing keys. This is conservative: an unused track may prevent a fixed classification. It does not omit ancestors, infer anatomical names or assume that a contact vertex follows one bone.

World and object targets retain their source trajectories under these actor-only edit permissions. A partner contact is fixed only if both actors are fixed. Every contact clock, individual point or centroid group and both facing-side rows remain in the original `ContactNorms` order.

```python
from native_contact_support import diagnose

# Measure the complete canonical source with ContactNorms or its verified cache.
source_contact = contact_model.residual(motion.source_world)
fixed_rows, diagnostic = diagnose(motion, source_contact)
```

`diagnose` checks complete finite residual shape and rehashes actor inputs. Its caller must bind the supplied source measurements to the correct scene and row identities; the function does not authenticate the residual array. `fixed_source_failures_present` is a conditional structural diagnostic, not a general infeasibility, collision, dynamics or quality certificate. No fixed failure does not prove that a correction exists. This remains a Python diagnostic API, not a Studio feature.

## Actual held-contact setup

The unchanged canonical sphere-hold source contains four groups, 1,033 times per group, ten point correspondences and 30,990 orientation/facing rows. Its twelve permitted rotation channels have the edit window `[2.0, 4.0333333015441895]`. Twenty point observations, or sixty surface rows, are structurally fixed: the start and end of the hold. Twelve of those fixed rows fail their authored orientation conditions. These measurements are bound to the complete source/reference comparison, including original ordered point identities. No row, limit or target is removed.

Independent native key lookup confirms that every permitted channel is frozen at these two exact source clocks. Two additional saved GLBs, using different random bounded rotation controls, preserve all decoded endpoint transforms and all 18,056 actor vertices exactly. Their native edit/static-payload audits pass. These trials demonstrate the endpoint behavior; they do not establish whole-motion contact/rate, geometry, engine or animation quality, and neither is selected as a correction.

The current coupled study can still measure improvements elsewhere in the clip, but it cannot satisfy all authored surface conditions with this setup. It remains running on its original inputs. The next setup must explicitly permit motion around the held endpoints if those targets are to change, while retaining original source-rate and authored contact/geometry limits. Revising that setup requires a new source-bound study; it does not change this study or prove that the broader correction will succeed.

Twenty focused tests cover exact keys, neighboring support, endpoint clamping, all declared tracks, world/partner touch/hold populations, complete point/side order, centroid groups, malformed inputs and conditional fixed failures. They pass from an isolated source copy without vendor code, model weights or character payloads. No human review or release evidence is created.

Local evidence: `reports/native-contact-support-development-v1`, `reports/native-contact-support-verification-v1` and `reports/native-contact-support-clean-source-v1`. All release criteria remain unchanged.
