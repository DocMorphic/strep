# Captured ground-motion reference intake

Completed 2026-10-11 under the existing full-project goal. The [30 generated
ground proposals](ground-proposals-v1.md) and [selective body-guide probe](selected-joint-guides-v1.md)
did not produce an acceptable replacement. This intake supplies captured
skeletal references for planning better support poses; it does not promote
either capture to a cleaned target animation or training example.

The [protocol](../benchmarks/cmu-ground-reference-v1.json) was frozen before
acquiring exactly two ASF skeletons and their two AMC motion files from CMU.
Source bytes, official URLs, acquisition times and SHA-256 values stay locally
under ignored reports. Raw or converted dataset payloads are absent from the
public repository.

| Official reference | Original frames | Joints including root | Rate | Last sample time |
|---|---:|---:|---:|---:|
| [111/03: Crawling](https://mocap.cs.cmu.edu/search.php?subjectnumber=111) | 1,524 | 31 | 120 Hz | 12.691667 s |
| [140/08: Get Up From Ground Laying on Back](https://mocap.cs.cmu.edu/search.php?subjectnumber=140) | 898 | 31 | 120 Hz | 7.475 s |

All **2,422 original frames and 75,082 joint transforms** are retained. Time
starts at zero for AMC frame one and ends at `(frame_count - 1) / fps`. There
is no clipping, filtering, nominal-limit clamping or downsampling. Original
numeric channel values, channel order/counts and presence flags accompany
global joint origins, orientations and bone endpoints in the local NPZ.

The new [importer](../scripts/acclaim_motion.py) requires explicit sample rate
and physical units. The [CMU format notes](https://mocap.cs.cmu.edu/info.php)
give `metres_per_unit = 0.0254 / ASF units.length`; both files declare `.45`,
giving `0.05644444444444444`. Supported input is bounded ASCII ASF 1.10,
degree angles, rotation-only bone DOFs, a zero-reference-orientation XYZ root,
and fully specified contiguous AMC frames. Unsupported conventions reject
explicitly. Child origins use parent endpoints, including helper segments;
axis conjugation follows the [Acclaim specification](https://research.cs.wisc.edu/graphics/Courses/cs-838-1999/Jeff/ASF-AMC.html).

All **47 model-free tests pass**, covering independent noncommuting rotation
examples, parent endpoints, units, clock/channel preservation and malformed or
unsupported inputs. Separate elementary-trigonometry, row-vector homogeneous
reconstruction checks every joint at every captured time. Maximum absolute
position/endpoint difference is `1.3323e-15 m`; matrix-element difference is
`1.9985e-15`. Clock and original numeric channels match exactly. This replay
shares the bounded text parser; it is independent transform arithmetic, not
an independent interpretation of the raw file format.

The first verification worker was stopped after discovering repeated archive
decompression. Its partial output and interruption receipt remain intact; its
182 resource observations replay with failed status. The replacement reads
each complete array once and finishes in 7.156 seconds, peaking at
192,126,976 bytes. Its 25 resource observations replay with complete status.
The populations, resource limits and accuracy checks are unchanged.

The [database terms](https://mocap.cs.cmu.edu/) permit research and commercial
inclusion but prohibit direct resale of raw or converted data. This intake is
local reference/evaluation use; training admission remains false. Attribution:
motion data obtained from the Carnegie Mellon University Graphics Lab Motion
Capture Database, mocap.cs.cmu.edu, funded by NSF EIA-0196217.

CMU warns that hand/toe channels may be noisy and that finger/thumb channels
are not captured evidence. Subject identifiers do not establish distinct
people. These files supply neither body surfaces nor contact, force, object,
partner or reviewer evidence. No measured fitness/strength labels are inferred.
Next work is explicit anatomical mapping, target-rig pose fitting and complete
target-mesh/contact evaluation before using a pose as a guide or reviewed
training target. All release capabilities and acceptance gates remain unchanged.

On an already provisioned workspace, an explicit local intake is:

```powershell
.venv\Scripts\python.exe scripts/acclaim_motion.py --asf reports/cmu-ground-reference-v1/111.asf --amc reports/cmu-ground-reference-v1/111_03.amc --fps 120 --length-convention cmu-inches --output reports/cmu-crawl-new-intake
```

The output directory must be fresh. Acquisition is separate; this command does
not fetch a dataset or change its admission status.
