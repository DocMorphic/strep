# Studio metadata memory reduction

The Studio page periodically lists saved studies and contact checks. That route imported `contact_timing_job.listing`, whose module-level imports reached `support_contact` and PyTorch. A status request therefore retained numerical libraries for the life of the HTTP host, despite performing no numerical check. On the development laptop the live host occupied about 550 MiB, and the previous real correction required stopping the test host to meet resource admission.

The change moves numerical imports into preparation, source verification and execution. The listing and option-validation functions remain usable with the Python standard library. Numerical algorithms, source/mesh checks, method snapshot binding, tolerance values, worker locks and resource policy are unchanged. Previously bound jobs retain their original method hashes; editing this file does not authorize executing old snapshots with replacement methods.

## Measurements

A fresh process dispatched the real Handler for characters, rig jobs, studies, continuation sources and continuation jobs. Before: final resident memory 539,877,376 bytes (514.87 MiB), with Torch loaded after the studies route. After: 69,246,976 bytes (66.04 MiB), with Torch absent throughout that sequence. This is a 470,630,400-byte reduction (448.83 MiB, about 87%). All five routes returned HTTP 200 in both runs. These are process observations on this host, not cross-platform memory guarantees.

The existing ordinary Studio host was restarted after verifying its PID, birth, workspace and loopback listener. It retained the open desktop page's metadata polling and measured roughly 70 MiB rather than 550 MiB. Reports and source clips were not replaced. Fresh probe evidence is retained under ignored `reports/studio-server-memory-v1`.

## Validation scope

Two isolated regression tests block Torch, NumPy and SciPy imports. They exercise actual study dispatch with a timing-check fixture and verify timing status, receipt hash and report links, plus option validation without numerical dependencies. These tests fail if read-only imports reintroduce the correction stack. Existing numerical source validation and altered-snapshot/weight rejection tests cover the paths that still require numerical imports. This does not certify concurrent inference, GPU/VRAM availability or motion realism; it removes a measured unnecessary host dependency.

The isolated import regressions pass: 2 tests in 1.51 seconds. The live loopback host returned all 83 studies in 0.203 seconds, 110 rig jobs in 0.141 seconds and the completed continuation job in 0.093 seconds, with resident memory 75,968,512 bytes (72.45 MiB). The page remained open and continued polling during this check. Startup character details may still load the rig numerical stack; this change specifically removes Torch from metadata polling. Numerical authoring endpoints can still load their required libraries in the host and need further separation if measured pressure justifies it.

The complete selected batch passes **44 tests in 17.45 seconds**, including source API options, held-boundary rejection, changed frozen inputs, changed encoded skin weights, registered continuation routes and the new isolated import checks. The guard completes in 237.234 seconds including 216.672 seconds of admission; all 236 recorded observations independently replay. Peak worker-tree RSS is 572,551,168 bytes. The unchanged 2,776,629,248-byte admission requirement, 600-MiB runtime floor, 7-GiB tree ceiling and 900-second execution guard remain in force. The same OS-verified Studio host is alive after the batch, serves all 83 studies and occupies 76,611,584 bytes (73.06 MiB). This proves this specific numerical-validation batch and metadata host coexisted; it is not a full inference concurrency result.

No numerical study was rerun merely for publication, no clip was regenerated or accepted, and no gate changed. The full-project goal remains active; all 14 release capabilities are still unapproved. Test inventories now include 501 Python/44 Node files and 63 focused Python/4 Node files.
