# Authored turning-speed limits in Studio corrections

The character-correction editor now offers an optional maximum turning speed
for each eligible rotation track. Values are local joint rotation speeds in
degrees per second. A blank field omits the limit; zero explicitly requests
unchanging orientation. No anatomical or fitness threshold is inferred.

A request with limits uses `strep-studio-native-scene-fit-v2` and retains an
explicit `rotation_speed_limits` list. Requests without limits retain the v1
contract. Before creating a job, Studio validates actor/joint identities,
finite values, duplicate limits and the rotation-edit feasibility preflight.
The prepared policy binds the exact snapshotted contact request. Inputs, policy,
source clips and the additional implementation files are preserved together.

Studio keeps its existing storage-vector correction path, source-relative
motion bounds, contact conditions, geometry policy, and serialized checks.
Rotation-speed vectors are appended to the scalar, vector and surface models;
continuous-proxy and decoded-world linearization retain the same selected native
keys. Fresh output verification uses the independent quaternion calculation
described in [speed fitting](native-rotation-speed-fit-v1.md). The existing
original scene rows remain in their original order and protected prefix.

Every probe saves its speed report. Completed jobs retain the bound policy,
preflight, full native-key lower bounds and complete final speed audit as
downloadable evidence. Review exposes the speed decision, and a speed-enabled
proposal cannot be staged unless native conditions, geometry and authored speed
checks all pass. Original clips remain selected until explicit staging.

Continuation retains the exact original policy and limits. Removing, changing
or silently adding limits requires a fresh correction epoch. Source, policy,
implementation or evidence changes reject reuse and serving. Bounds apply to
neighboring native-key geodesic speeds; instantaneous interpolation dynamics,
engine playback, anatomical plausibility, broad motion quality and release
readiness still require their separate evidence.

Synthetic integration tests exercise vector/scalar residual parity, stored and
continuous-proxy guidance, actual Studio prepare/fit/review/resume, exclusion
before folder creation, immutable policies and independent final export checks.
Editor tests exercise optional fields, zero versus blank, invalid input,
continuation and staging rejection. These are source/fixture tests; live Studio
browser appearance and operation have not been verified in this change.
The final targeted run passes all 37 integration and fitting cases in 61.16
seconds. Sampled process-tree peak RSS is 203,649,024 bytes; all 73 resource
observations independently replay under the unchanged admission policy. The
earlier 19-case integration run and editor source checks also pass. The first
187-case run retained one failure because its positive fixture declared no
geometry conditions; that fixture now explicitly declares its floor plane.
The geometry gate and tolerances are unchanged. The [expanded Windows/Linux run](https://github.com/DocMorphic/strep/actions/runs/38156291788)
at `2f07363` passes all 451 Python checks on each platform, plus the editor
checks. Linux takes 93.05 seconds and Windows 216.94 seconds, without skips
or failures. Exact committed source bytes and hosted logs are retained. Rebound file receipts cannot conceal changed exported rotations: review
recomputes the complete selected native-key speeds before serving the proposal.
