# Contact-aware native TRS initialization

The existing native-key contact initializer now has an explicit path for the actual affine transforms in supplied rigs. It edits existing quaternion channels while retaining their sampled translation and scale, untouched local matrices, skin influences, source key clocks and original motion reference. This is a pose-initialization stage followed by complete clip checks; independent feasible poses do not establish a usable animation.

## Authoring contract

The existing command remains:

```powershell
python scripts/native_key_contact_initializer.py contacts.json geometry.json request.json fresh-output
```

The source-bound `strep-native-key-contact-initializer-v1` request may explicitly select:

```json
{
  "pose_representation": "native-trs-v1",
  "orientation_mode": "right-polar-v1",
  "boundary_keys": {"start": "edit", "end": "preserve"},
  "acknowledge_changed_boundary_compatibility": true
}
```

These fields supplement the existing actor, root, permitted rotation tracks, original-key window/frozen times, iteration/time budget and displacement/floor-reserve declaration. The default pose representation remains the old rigid method, angular measurement remains strict, and both endpoints remain preserved. Unknown modes reject. The explicit polar metric is described in [affine orientation measurement](native-affine-angular-metrics-v1.md); it does not normalize source geometry or waive historical strict failures.

Boundary edits require both exact start/end choices and the matching Boolean acknowledgment. Preserved channel endpoints must be listed as frozen native keys. An edited endpoint cannot also be frozen, must be at the corresponding edge of the edit window, and must coincide with the actual clip boundary (zero or declared scene duration). An interior channel endpoint cannot authorize changes to held poses outside that window. Partially spanning channels remain supported when both endpoints are preserved. Ordinary interior window edges remain frozen. The result's `boundary_contract_changed` flag records changed permissions, even if a feasible source returns zero edits; it does not certify transition compatibility. Original clips remain selected. No Studio control for these new options is claimed here.

The existing limits remain: 1–16 explicitly permitted non-root skin rotation tracks, at most 30 degrees each, at most 22 cm joint displacement, a fixed root, identical existing LINEAR clocks, at most 4,096 complete keys, and the original full constraint population. No action-name whitelist is introduced. Source import restrictions remain those of `RigAsset`; arbitrary large nonuniform scale or reflected rigs are not newly supported by this initializer.

## Actual transform and contact derivatives

The previous rigid cross-product derivative assumes orthogonal local bases and rejects the measured supplied-rig matrices at `1e-8`. The optional native TRS path instead samples every original channel with the existing decoder. At an edited joint it applies the permitted rotation to the sampled quaternion before the original scale, following the actual T·R·S transform order. No local matrix is projected to a rotation.

The analytic derivative propagates the complete affine product through every affected ancestor/descendant chain. Skin derivatives retain every influence and its actual inverse-bind homogeneous point. Vertex gathers are processed in chunks of 512 to bound temporary memory; no vertex, influence or constraint is discarded. Joint origins and mesh surfaces come from the same articulated pose. Zero controls reproduce the original world matrices exactly.

The unchanged pose constraint builder then enforces rotation-vector balls, every skin-joint displacement, every declared plane and every active affected point target. World, moving-object and outgoing/incoming partner contacts retain their actual target coordinates and individual/centroid reductions. Other actors and objects retain their original trajectories during this single-actor initialization. A pose touch is not a hold-slip, surface-normal, balance or collision certificate.

Quaternion export retains the original rig nodes, translation/scale channels and original animation library. For the native TRS path, decoded edit angles are measured directly from the sampled original and exported local quaternion channels, rather than interpreting a scaled/sheared matrix product as a rotation. Root identity and displacement remain strict. Complete contact/geometry and original 120-Hz four-bin positional/angular rate checks still decide the sampled result.

Original source caps are established before solving and must match the same source samples after solving. They are never recalibrated from a corrected proposal. Explicit metric/pose choices and boundary permissions are bound to the original request; the fresh auditor verifies them, exact exported bytes, every key-pose decision and complete observation arrays without executing optimization.

## Bounded-job retention

Each completed key appends its decision to `key-results.jsonl` and updates `key-checkpoint.npz` with the complete control array and completed-key count. Future zero entries are pending, not passed observations. A handled numerical/time-budget failure records its pending key and last evaluated pose/constraints/Jacobian when available, while retaining the prior completed checkpoint. No complete result or animation is published from that interrupted path. Checkpoints are diagnostic recovery data; this command does not yet offer a resume contract. Fresh output remains required.

## Validation

The compatibility/affine/boundary/checkpoint batch passes **52 checks in 152.66 seconds**. It includes complete skin/joint/plane/contact finite differences with rotated placement, incoming partner targets and nonunit homogeneous points; actual Float32 quaternion exports retaining the affine rig; full original-cap, boundary and byte/array replay; preserved legacy rejection; explicit endpoint conflicts; and forced timeout retention. Its guard completes in 169.422 seconds with all 167 resource observations replayed.

Two additional checks pass in **34.96 seconds**: coupled parent/child rotation derivatives with a moving object and centroid contact, and strengthened full journal/fresh replay validation. One strengthens a previously counted case. That guard completes in 53.407 seconds with all 54 observations replayed. An earlier attempt is deferred before launching a worker when headroom changes; all 33 observations replay as deferred, not as numerical success or failure. The same 512 MiB estimate/runtime cap, additional 600 MiB free-RAM floor, 15-second stability and 900-second worker limit apply. Model/full-body resource policy is unchanged.

Two later regressions pass in **4.25 seconds** for interior start/end channel endpoints; the same cases also verify that preserving a partially spanning channel remains accepted. A passive check confirms that the real full-duration pilot's original request still passes preflight with identical clocks, permissions, root and source bytes. Its guard completes in 21.390 seconds and all 23 resource observations replay. These input-validation changes follow the production pilot and replay below; their archived implementations remain intact. No production optimization is rerun for this hardening. The complete source inventories validate at 506 Python/45 Node files and 69 Python/5 Node files in the focused contact/rig inventory; inventory validation is not execution of every listed test.

## Development pilot

The pilot uses the unchanged seed-77 male Quaternius crawl transfer, with its original source hash and original 120-Hz caps. Its first pose already penetrates the Y=0 floor by 20.377 mm, so a request preserving that pose cannot clear the floor. The separately recorded trial explicitly permits changing the start and preserves the end; the root remains fixed at every time.

All sixteen mapped non-root tracks other than the two wrists receive the existing 30-degree permission. Every original native key is retained. At the original worst native calf-surface sample, 0.10000000149 seconds, vertex `[67, 0, 3374]` is deliberately assigned a world-floor touch at its original X/Z and Y=0, within 5 mm. The original surface is 20.646 mm below that target. This is authored surface-to-ground intent, not inferred stance, anatomical or naturalness approval. The floor remains Y=0 with 5-mm tolerance and 0.5-mm proposal reserve. The finite pilot allows four iterations per key and 600 seconds for key solving, retaining failed keys and their proposed controls.

The pilot completes all **477 native keys**: 470 key poses pass and seven retain their original controls after their proposed pose fails the finite four-iteration test. Complete decoded edit limits pass; maximum joint displacement is 59.716 mm and maximum rotation is 25.062% of the 30-degree permission (about 7.519 degrees). Every root matrix remains exact, and the complete final world pose is unchanged. The explicitly editable start changes joint positions by at most 52.703 mm.

The complete clip remains **rejected**:

| Observation | Original | Proposal |
| --- | ---: | ---: |
| Failed floor times, same 2,829-time population | 672 | 49 |
| Peak floor depth | 20.646 mm | 20.646 mm |
| Authored ground-touch position error | 20.646 mm | 20.646 mm |
| Failed original motion-rate rows, 123,630 total | Reference | 412 |

The touch key reaches its four-iteration limit; the unsuccessful controls and constraint margin are retained. The 412 failed rate rows comprise 86 positional-speed, 98 positional-acceleration, 115 angular-speed and 113 angular-acceleration conditions. The original four cap arrays match the earlier continuous-root cohort exactly. Thus improving most floor samples with independent pose edits still does not meet temporal or contact requirements. Neither seven bounded solver failures nor this whole-clip rejection proves global infeasibility.

Production uses 214.328 seconds, peak sampled process-tree RSS 278,138,880 bytes, and 211 resource observations. A fresh audit reconstructs the exact exported bytes and all key, contact, geometry, edit and rate observations without optimization; it reproduces every failure and passes complete-array comparison. It takes 144.406 seconds, peak sampled RSS 260,243,456 bytes, with all 143 resource observations replayed. The audit shares the native reader, skin and pose methods; it is a separate bound replay, not an independent implementation of all geometry or physics.

Local evidence is retained under `reports/crawl-affine-articulated-v1`, `reports/crawl-affine-articulated-replay-v1` and `reports/native-affine-key-pose-validation-v1` through `v5`. The original transfer SHA-256 is `925709b5b2fad06d398d3a232687c217b635960fb7ef2ff0e54f844521530c56`; the proposal is `c4cdcff60eea9279f915acd270c789a4f1cf660d383f28956c195bdedb623643`. Reports and third-party asset payloads remain local. The source animation is index 0; the proposal appends index 1.

Next work must address the failed authored contact and coupled temporal behavior without resetting source limits or discarding failed samples. No held-out actions, new generation, training, engine playback, human ratings or cleanup evidence are claimed. This failed Quaternius pilot is separate from the earlier Kenney crawl developer-review packet. All fourteen capability/calibration approvals remain unchanged and the full-project goal stays active.
