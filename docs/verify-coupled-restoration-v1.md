# Replay saved native repairs

`scripts/verify_coupled_restoration.py` checks a completed offline restoration
study from its saved curves and full observations. It requires the original
inputs and the same source methods. A fresh output directory preserves the
replay request, method snapshots, result or failure. It uses the shared worker
lock and one numerical thread.

```powershell
python scripts/verify_coupled_restoration.py reports/repair-v1 reports/repair-replay-v1
```

Every closed population is checked: original source, preceding baseline,
rejected origin and every recorded backoff. The file inventory must be complete;
source files, closed observations and verifier snapshots remain hash-bound
through completion. Recomputing a checksum alone cannot establish that altered
evidence matches the motion.

The replay reconstructs every editable raw quaternion or translation key from
the original keys, permissions and source-relative controls. Frozen keys,
channel clocks, static rig/mesh payloads and original binary prefixes must stay
unchanged. It decodes the actual saved files and compares every actor's complete
world population. The decoder and authoring clock construction are shared with
the producer; this is not independent engine decoding.

Separate scalar and vector arithmetic reconstructs original rate caps from the
source's uniform clock and four time bins, then checks complete control,
displacement, linear/angular rate and native contact position/frame-speed rows.
Uncached full surface observations recompute contact orientation and side gaps.
The paired hard/soft contact rows retain the preceding baseline, with original
orientation caps, side-gap encodings and scales. Jacobian duplicates are checked,
but individual derivative columns are not recomputed. Numeric parity checks
allow stated floating differences; they do not add slack to native feasibility
or the producer's individual contact guards.

Raw and projected directions, exact original control/trust boxes, rounded
backoffs and each recorded repair decision are reconstructed. Native failures
stay failures at any positive stored excess. The final motion must reproduce
the claimed eligibility, chosen export and retained controls, including a
nonzero baseline fallback.

For an eligible final candidate, the replay independently reconstructs every
placed vertex and triangle input, all object poses/shapes and the original
geometry policy. It reruns complete geometry and containment queries at every
declared sample through the unchanged kernel. A streaming comparator checks
every numeric output and the entire fresh report against the saved archive;
earlier arrays are not retained in memory. Failed geometry and unavailable
partner containment remain failed. The geometry kernel is shared with the
producer; no alternative kernel, exact arithmetic, self-collision, continuous
collision, engine equivalence or human quality is certified.

## Validation scope

Small serialized fixtures cover successful partial repair, failed geometry,
timeouts, world/partner/moving-object targets, touch/hold intervals and raw
rotation/translation keys. Deliberately altered worlds, scalars, source caps,
controls, model rows, retained controls, projection records, geometry reports
and selected-file metadata must reject even after their recorded hashes are
updated. Missing inventory entries and mid-replay source-snapshot mutation also
reject. A command fixture runs in its own copied source checkout, preserving
the production worker lock.

This verifies the bounded fixture and declared sampled-study evidence, not
general solver convergence or professional animation quality. Source selection
and every project release gate remain separate. Production restoration and its
fresh complete replay are pending until their actual runs finish.


All 27 focused cases and 378 isolated native/contact/geometry/solver source cases pass. The command fixture performs the fresh complete geometry replay in a separate copied checkout. Local evidence: `reports/verify-coupled-restoration-tests-v5.log` and `reports/verify-coupled-restoration-clean-source-v1`. The real-character restoration worker is still auditing final geometry; this new replay command has not yet verified that production result.
