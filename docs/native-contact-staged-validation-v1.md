# Validate a coupled native scene without retaining both curve models

The [contact-time study](native-pair-authored-contact-objectives-v1.md) repeatedly
stops at the 600 MiB free-RAM floor while retaining both native curve models
and running geometry checks. Its matrix and fitted direction are already
saved. Rebuilding or solving them again would not finish validation reliably.

`native_contact_actor_validation.native_rows` extracts one actor's full native
rotation, displacement and rate population in the exact order used by
`PairKeyGuides.norms`. It excludes single-model contact estimates, which would
otherwise observe a frozen partner. Coupled contacts remain a separate actual
two-character observation. No native row, source cap, time sample or scale is
discarded or weakened.

`geometry_cache` retains every canonical vertex and face at explicitly selected
original-clock times, including the actor's actual scene placement. It records
partial versus complete time coverage and enforces a declared byte budget by
rejecting oversized requests. It never truncates a requested population.
Malformed, duplicated, unsorted, boolean or out-of-range sample declarations
reject, including mixed boolean/integer lists. Cached observations alone
confer no geometry or quality approval.

## Validation

All **22** selected checks pass in **108.39 s**: the 14 new staging cases plus
the eight existing authored-contact cases. They prove that independently
extracted actor rows recombine into the complete paired vectors/caps/scales
exactly, retain all selected vertices and faces with placement, distinguish
partial and complete clocks, copy clock data, reject incomplete observations
and fail an undersized cache budget without truncation.

The 512 MiB CPU test guard completes in **125.734 s**, peak sampled tree RSS
**150,982,656 bytes**, with all **124** resource observations replayed and the
additional 600 MiB free floor. Local records remain under ignored
`reports/native-contact-actor-validation-tests-v1`.

The [focused hosted run](https://github.com/DocMorphic/strep/actions/runs/38883848122)
at `d16ff21` passes all **14 staging cases per OS**: Ubuntu **2.50 s**, Windows
**11.53 s**. Inventories contain **525 Python modules / 45 Node suites**;
contact/rig contains **89 Python modules / five Node suites**. These are counts
and affected-suite results, not a full-inventory or release pass.

## Actual eighth-step validation

The second saved-fit continuation completes the quarter-step comparison, then
stops at **455,049,216 bytes** of free RAM while checking the eighth step. Its
failed guard and partial output remain intact under
`reports/high-five-authored-contact-resume-v2`. That run lasts **371.312 s**,
peak sampled tree RSS **598,953,984 bytes**, with all **369** resource
observations replayed. The quarter step passes native and floor/contact
protection but still has a **31.920551-mm** hand gap and regressed mesh measures;
it is rejected.

The final eighth-step actor files are already complete and bound by their
contact specification. New actor stages validate those exact files at every
original motion and floor time. Each stage reconstructs original zero-source
caps, compares its entire native slice with the original combined snapshot,
and retains the original geometry/skin/node payload and animation selection.
It also caches the same five complete contact-time meshes. These are
single-actor curve jobs under the existing 512 MiB CPU profile and 600 MiB free
floor, rather than simultaneously retaining both curve models. Admission
policies for matrix solves, neural inference and engine runs stay unchanged.

The subsequent coupled stage must recompute the saved native-row residuals,
check full original floor protection, replay every cached mesh vertex exactly
against the actual exports, and evaluate coupled contacts using both edited
characters. It then calls the same direct native geometry method at the same
five original times in a fresh process. No curve-model buffers need remain
resident for that query. Every original acceptance gate remains in force.

Actor A completes **309,831** native rows with zero failures, retains all
**2,017** floor samples and preserves the original floor condition. All 2,017
samples still fail the physical floor screen; protection is not a repair.
Its guard completes in **221.485 s**, peak **270,876,672 bytes**, with all **219**
resource observations replayed. Actor B independently completes its **309,831**
native rows with zero failures and retains all **2,017** original failed floor
samples without worsening. Its guard completes in **185.688 s**, peak
**269,340,672 bytes**, with all **184** observations replayed.

The coupled stage recomputes all **619,662** saved native residuals against the
exact original caps/scales and replays every cached mesh vertex exactly against
the actual actor exports. It evaluates contacts from both selected native
animations, then runs the original direct geometry query at all five declared
times. It completes in **149.781 s**, peak **298,381,312 bytes**, with all **149**
resource observations replayed under the same 512 MiB CPU / 600 MiB free-floor
profile. No matrix, solve, model inference or engine run is repeated.

The eighth-step hand gap is **32.573864 mm**, still outside the authored 30-mm
limit; **15** selected mesh measures regress. Its native/floor/contact
protection passes, but both actors still fail the physical floor screen at all
2,017 times. The candidate remains rejected. Lower memory use finishes the
original checks; it does not make an unsuitable clip pass.

The guarded three-stage path finishes without another RAM stop, keeping its
sampled per-process peak below 285 MiB. This is not a matched runtime benchmark
against the interrupted simultaneous-model run. All raw clips, source bounds,
partial attempts and failed decisions remain retained. The complete four-step
record/decision assembly is under ignored
`reports/high-five-authored-contact-complete-v1`; none of the four steps
qualifies, and the original remains selected.
