# Timed character contacts with imported objects

2026-10-21 (local date). Studio now connects saved object grips to an exact
character surface patch, touch/hold timing and explicitly placed or moving
objects. The worker produces a portable scene package and complete declared
point-contact measurements. It does not modify character motion or run a fit.

## Use in Studio

1. Add the intended character clips to the native scene in **Characters**.
2. In **Scene → Object grip points**, import a static GLB, pick a grip and save
   it. Leave the intended saved grip selected.
3. In **Characters → Character contacts with imported objects**, choose
   **Use current native scene**. Give the object a name and its world position
   and XYZ rotation. **Add object from selected grip** uses that exact asset.
   Optional end position/rotation authors a linear-position, spherical-rotation
   path across the shared clip duration; it is not simulated object movement.
4. Select the intended hand or other contact patch with the character surface
   picker. Choose its scene actor and target object, contact name, touch time or
   hold interval, allowed gap and relative speed. Add the contact using the
   selected character patch and saved object grip. Several contacts can use
   different saved grips on the same object.
5. **Save scene and measure contacts**, then **Refresh measurements**. Completed
   jobs provide a scene ZIP and contact report. A failed contact stays failed in
   both the UI and package. Refreshing a job does not apply its scene or replace
   any animation. Rebinding a changed native scene clears this object/contact
   draft explicitly.

The original native draft, geometry policy, source clips, object GLBs and grip
JSON remain in the package. Actor and prop paths are relative within the portable
mesh manifest. Source/geometry hashes, original prop provenance notes, exact
request/implementation hashes and all contact observation arrays are retained.
Existing body, speed and engine policies are preserved as authored data; this
worker does not claim to have evaluated them. Pending object edits/contact
revisions must be resolved before binding, rather than silently discarded.

Requests are queued before rig/mesh decoding. One owned worker runs under a
512 MiB process-tree cap, a 600 MiB free-memory reserve, 15-second stable
admission and 300-second execution limit. Changed requests or implementation
files reject before execution. Source changes during snapshotting/evaluation
also reject. Failed/deferred work keeps the original assets selected. Completed
downloads are checked against saved receipts and package-member hashes.

## Verified scope

`reports/mesh-grip-authoring-tests-v3` passes **206 Python checks** and both
object/mesh editor Node suites. Coverage includes real prop-store/rig/mesh-scene
integration, unchanged source bytes, reopened package replay, mirrored object
instances, exact native contact clocks, malformed/tampered inputs, timing,
asynchronous placement changes, queued API transport, failed startup and
desktop build preservation. Both new suites are registered in the model-free
CI inventory. This is local verification, not a claim of completed hosted CI.

`reports/mesh-grip-authoring-integration-v2` runs the actual queued supervisor
twice through its original resource guard. A generated rig fixture has one
matching touch with **zero position error**. An intentionally offset hold fails
with **3.000095998 m peak error across 679 samples**. Both saved packages reopen,
and all contact arrays and ZIP member bytes replay exactly. Implementation and
request hashes inside each ZIP match the queued job. Original and failed inputs
are retained; no result becomes a selected animation or clean training target.

Chromium submits the real editor's scene to actual Python API dispatch through
intercepted requests, then opens both measured results and downloads their ZIPs.
The test orchestrator runs each real supervisor synchronously between browser
phases to retain its process handle. There is no listening review server. The
generated patch context is supplied to the editor; a full live Studio session
and a new human hand-picking review are not claimed. Browser screenshots were
visually inspected; both phases report no page errors. The enclosing integration
process tree peaks at 532,226,048 sampled bytes under its separate 1 GiB cap.

Source epochs preserve the prior public implementation at
`40199555c1319acebbc7452c6b4dad0732454ddd` and the earlier uncommitted assembly
version used by integration-v1. The final version adds provenance to the ZIP;
historical results are not relabeled as executions of the new source.

## Next work and release limits

Show the assembled character/object contact scene, then connect its source-bound
manifest and geometry policy to explicit bounded correction and complete
geometry/export validation. A point-contact pass does not establish collision
clearance, grip orientation, support forces, believable grasping or engine
fidelity. The existing high-five diagnostic still has 38 physical failures.
All fourteen release capabilities, four unset acceptance gates and nineteen
configuration/evidence gaps remain under the unchanged project contract.
No new model inference, training, human ratings or cleanup-time evidence was
produced by this authoring work.
