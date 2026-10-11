# Authored speed limits in native scene fitting

`SpeedLimitedSceneProblem` adds the author's local joint-speed limits to the
existing native scene solver. It first performs the necessary-condition
[preflight](temporal-rotation-bounds-v1.md), then retains every original scene
constraint and appends speed residuals for every neighboring key on each
selected rotation track. Original clocks, frozen keys, edit caps, contact goals
and existing source-relative motion bounds remain in force.

The existing optimizer can use this problem directly. Each proposed export must
be checked with its `decoded` method. That method reads the fresh GLB, checks
original edit/static/frozen-key preservation, and calculates rotation speeds
using separate normalized-quaternion relative-angle arithmetic. The model uses
SciPy rotation arithmetic; output checking does not reuse that angle decoder.
Every rate and native time is retained in `last_speed_output_audit`. A violated
edit/payload contract raises an error; a speed violation remains an optimization
residual and prevents a passing result. Failed exports stay available for review.

These are local-key geodesic speeds in degrees per second, without an extra speed
acceptance allowance or invented anatomical limit. They do not establish
instantaneous speed throughout glTF interpolation, physically plausible joint
dynamics, whole-surface collision freedom, engine fidelity or animation quality.
Scene fitting remains bounded and may fail even after preflight does not exclude
the request. Studio route/UI integration is pending.

The 17 new regression cases include identity, tiny angles, half-turns and
quaternion sign/length changes; invalid clocks and values; fresh serialized
output that disagrees with submitted controls; hard edit-audit rejection; and
a complete fixture fit with unchanged contact conditions, native clocks and
source bytes. The fixture deliberately isolates a rotation track from mesh
deformation, so its fit does not prove simultaneous full-body contact correction.
Both CPU workflows include these tests. All 59 local speed-related checks pass,
including the 17 fitting/output cases and the earlier 42 preflight cases. The
serialized fit meets the unchanged 1-degree/second request and every original
scene row. The guard's last execution sample is at 7.172 seconds, with 134,590,464-byte sampled
process-tree peak RSS under the unchanged resource policy. All 25 observations
independently replay. The [expanded focused run](https://github.com/DocMorphic/strep/actions/runs/38152277829)
at `f597448` passes all 321 checks on each operating system, including all 17
fitting/output cases, without skips or failures. Linux takes 23.40 seconds and
Windows 36.41 seconds. Logs and exact committed source bindings are retained.

The first run at `bbd71a6` passes 318 cases per platform but fails the complete
fit: the existing forward-difference optimizer leaves the selected track near
8 degrees/second against its unchanged 1-degree/second request. That failed run
is retained. `optimize_speed_limited` now first constructs a bounded control
proposal following shortest rotation arcs between frozen keys. It fits the
existing control weights, rescales any oversized radial edit, and checks the
fresh serialized proposal against **all** original scene constraints and speed
limits. Only a complete passing improvement is adopted; otherwise fitting starts
from the retained original controls. This changes initialization, not acceptance
thresholds, permissions or clocks. Two additional cases check untouched controls
and rejection of a failed complete-scene proposal.
