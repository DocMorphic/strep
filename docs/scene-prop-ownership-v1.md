# Shared actor clock and explicit prop ownership

The new opt-in native scene SDK coordinates multiple grip memberships and
independent dynamic props on one finite actor clock. A two-hand hold can lose one
hand without releasing the prop; a character-to-character handoff is atomic;
loss of the last hand inherits the incoming grip velocity and spin. Confirmed
source event IDs and explicitly mapped grip providers determine behavior, with
no action-name or anatomical inference. All active grips must agree; conflicting
poses fault instead of being averaged or silently omitted.

The [integration guide](../integrations/godot/SCENE-PROP-OWNERSHIP.md) describes the
compiler request, actor/body/provider binding and transport contracts. This is a
source SDK, not automatic native package or Studio hookup. Existing one-body and
baked-scene consumers retain their own behavior.

## Method and population

`scripts/study_scene_prop_ownership.py` runs serial headless Godot 4.7.2 fixtures,
using the actual native scene player, two actual procedural three-bone skinned
triangle rigs and two actual dynamic bodies. Actor A embeds root motion and actor
B extracts it. Their native AnimationPlayers use linear position/rotation tracks
with 61 keys over two seconds. These are tiny software fixtures, not production
humanoid assets, reconstructed characters, mocap or imported GLB evidence.

The cylinder is radius 0.15 m/full height 0.4 m; the sphere is radius 0.15 m.
Both have mass 2 kg, explicit uniform inertia, centered geometry, friction 0.6,
zero restitution/damping and a static floor. Jolt margin fraction is zero and
penetration slop is 0.001 m. Engine binary SHA256 is
`c8f0a6bc45a19b33541501e57f6f7cd972ab18453743266339d495cbbe846643`.
Project physics rate is configured before startup, without weakening the callback
step check. No engine changes or dependency installation are required by this
study.

The unchanged binary clock is `[0, 0.2, 0.6, 1, 1.305, 2]` seconds. At 0.2 s, A's
two hands acquire cylinder P and B's right hand acquires sphere Q. At 0.6 s one
of A's hands releases P; at 1 s A's remaining hand transfers P to B's left hand.
At 1.305 s both props lose their final hand and enter independent physics. They
make actual mutual/floor contacts, including measurable horizontal impulse
response on both bodies. Actor root movement continues and then holds at the
finite endpoint while physics runs through three seconds. Positive cases also
pause, preview an older retained record, resume the saved live state, reject an
expired preview and restart for a second traversal.

At each of 60, 120 and 240 Hz, six cases run: ordinary body insertion order,
reversed insertion order, incompatible grips, an outside clock change, a missing
body callback and a provider that changes the owned clock. The last four must
fault. Every case first rejects five malformed bindings without body mutation
and rejects a second owner. Final population: **18 cases, 4,287 complete records,
72 positive prop transaction observations, 90 malformed-binding rejections,
18 second-owner rejections and 12 detected fault cases**. Reversed insertion
order checks ownership behavior; it does not establish deterministic physics.

## Independent checks and retained failures

Python checks source event order/count and binary time identity, grip membership,
installed geometry/inertia, full actor/prop populations and actual Jolt direct
states. Expected native trajectories are computed independently from fixture
keys, including B's interpolated local hand motion. Held/action poses retain the
original 3e-5 matrix-element error limit; inherited velocity/spin retain 1e-3
m/s and rad/s limits. Whole-step actor root deltas are compared against complete
boundary roots, including physics steps split by marker sampling. Restore checks
use 1e-7 pose/velocity/spin tolerance. Limits are unchanged across rates.

The maximum observed held-pose matrix-element error is 1.529e-7; action-pose error
is 9.156e-8; whole-step root error is 1.467e-7. Maximum velocity/spin errors are
7.562e-5 m/s and 2.174e-5 rad/s. These quantify fixture playback and state
transfer, not realism, articulation accuracy or humanoid dynamics.

| Physics rate | Complete records, all six cases | Maximum physical application delay | Maximum sampled floor depth | Original 10 mm depth screen |
| --- | ---: | ---: | ---: | --- |
| 60 Hz | 621 | 11.667 ms | 63.229 mm | **Fail**, both positive cases |
| 120 Hz | 1,227 | 3.333 ms | 0.0966 mm | Pass, both positive cases |
| 240 Hz | 2,439 | 3.333 ms | 1.7411 mm | Pass, both positive cases |

**Exact physical event timing fails in all six positive cases.** Actor poses and
source gameplay notifications visit exact native marker times, but physical
transitions apply at the next fixed boundary. Source times are not rounded or
shifted to disguise this delay. No fractional collision solver or delay
compensation has been implemented. The 60 Hz floor penetration failure also
remains recorded without a higher threshold or silent rate restriction.

Cylinder/sphere penetration bounds are queried at every recorded live boundary.
The observed inter-prop upper depths are zero despite real engine contact
notifications/impulses. Boundary checks do not capture unsampled extrema or
certify continuous collision. Higher-rate sampled passes therefore do not
resolve the 60 Hz failure or general collision robustness.

## Reproduction and provenance

Use an already available model-free Python environment with NumPy/SciPy and the
pinned engine at the path used by `scripts/object_release.py`:

```powershell
python scripts/study_scene_prop_ownership.py --output reports/ownership-60-fresh --physics-fps 60
python scripts/study_scene_prop_ownership.py --output reports/ownership-120-fresh --physics-fps 120
python scripts/study_scene_prop_ownership.py --output reports/ownership-240-fresh --physics-fps 240
```

Run serially. Every output directory must be fresh. Request, raw engine output,
logs, frozen method copies and their hashes remain local under ignored reports;
no models, downloaded assets, credentials or machine payloads are published.

| Final local receipt | SHA256 of result.json |
| --- | --- |
| reports/scene-prop-ownership-engine-60-v1 | `0cf060297454b1f7bb077c7f199fb8cb6196f14c41de976c5e3022385bf11b5e` |
| reports/scene-prop-ownership-engine-120-v2 | `f694baca0affb21594db78b001ae634d0a9d9d5d91725d982c62089aa86f17db` |
| reports/scene-prop-ownership-engine-240-v4 | `fd429bcb9c62bf46029d160b4799907bcb21022b679d2f9c8bfd9a863e73c2ac` |

All final frozen engine methods match current source; all owned study commands
are terminal with zero exit status. Isolated frozen source validation passes
**252 tests with four explicit engine skips** in 39.85 s, covering 34 new compiler,
pose-consistency, exact-clock and no-overwrite CLI cases plus existing native
clock/scene/root and cylinder-bound regressions. No engine execution is inferred
from source tests. Hosted GitHub CI is tracked separately.

Source-check result SHA256:
`b4191087c1cb0be2968c784e7f69b9b5f7618b45a15d6759e37d33193d429550`.

Intermediate failures remain retained: an initial GDScript inferred-type parse
failure (its exact owned engine process was terminated and the parent exit
accounted); an independent verifier list multiplication error; native observation
matrix layout mismatch; and a 120 Hz startup attempt whose first callback still
used the default 60 Hz project step. Saved outputs were preserved, the respective
type/reference/layout/startup configuration defects corrected, and final current
methods validated. The step assertion, timing identity and penetration thresholds
were not relaxed. No completed expensive production job was rerun.

## Supported limits and remaining work

Held/parked/paused/previewing props have collision masks disabled. Their grips
are prescribed transforms, so holding does not enforce clearance or physical
constraints. Characters do not respond to collisions. Acquisitions/handoffs must
already meet pose continuity bounds; this SDK does not solve catches or align
hands. Native gameplay listeners may emit side effects before a complete physical
transaction, and faults do not undo those effects. Pause/preview/resume restores
the owned participants, not unrelated moving-world state or solver caches.

The next integration work is explicit native package/Studio grip-provider binding
and preserving these timing/depth failures while improving constrained physical
interaction. Blended-controller ownership, production rig/object/partner
generalization, appearance and animator cleanup still require separate evidence.
No model sampling/training, GPU rendering, live Studio/browser access, anatomical
intent selection, human rating, cleanup record or held-out acceptance was created
here. All fourteen release evidence arrays remain empty; quality/release approval
is false and the single full-project goal remains active.

The implementation uses Godot's
[RigidBody3D integration contract](https://docs.godotengine.org/en/stable/classes/class_rigidbody3d.html#class-rigidbody3d-private-method-integrate-forces)
and [PhysicsDirectBodyState3D](https://docs.godotengine.org/en/stable/classes/class_physicsdirectbodystate3d.html).


Follow-up: [source-bound native prop packages](scene-prop-runtime-v1.md) now install the SDK from explicit source-joint and prop-offset choices, with complete authored/physical ownership modes and actual exported boot evidence. This does not change the timing/collision failures or scope of the earlier ownership study; Studio grip authoring remains open.
