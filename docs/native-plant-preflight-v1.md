# Native foot-planting precheck

New Studio planting requests use revision 3. Before generating a seed or
running the joint fitter, `native_plant_preflight.py` checks a necessary
condition for holding each fixed stance-start foot patch. A conflict stops
fitting, preserves the input, and reports the stance, native time, minimum
required point movement and maximum permitted movement. Source, draft,
policy and method hashes accompany the saved evidence.

The draft's displacement budget limits the ankle, not every mesh point. For
each fully foot-owned patch point, the precheck derives a movement allowance
from the ankle budget, the sum of the three edited local rotation budgets,
the pivot-relative radius and the exact homogeneous skin response. It then
compares that allowance against distance to the permitted tangent disk and
clearance half-space. Existing final-audit tolerances are included; this
check introduces no tighter acceptance threshold. Frozen edit boundaries
have zero permitted pose change.

Applicability requires rigid ancestry, no ancestor scale channels, and every
positive patch influence inside the foot subtree. All descendant local
tracks remain unchanged under the planting preservation contract. Unsupported
geometry or checks exceeding 200,000 point/key observations skip the precheck
and retain the ordinary fitting path. A supported row can still reject a
request when another row is unsupported: every requested stance must hold.

Only native keys are checked. Local-key rotation caps do not justify applying
the same bound between keys. No conflict found is not a feasible correction,
nor a contact, rate, collision, engine or animation-quality approval. The
existing fitting, serialized checks and human review remain required. The
arithmetic includes conservative numerical reserves, not a formal interval
certificate.

Revision 1 and revision 2 method sets and saved-job interpretation remain
available. Completed revision 3 jobs expose the bound precheck evidence and a
plain-language summary; rejected jobs retain `plant-preflight.json` locally
and expose the failure explanation through the existing Studio job error.

This change saves futile fitting work and prevents confusing ankle and mesh
budgets. It does not solve the rejected KayKit contact/rate corrections or
establish broader action, object or partner quality.

## Validation

Nine targeted Python modules cover 160 tests plus 17 subtests, including
actual fitting and saved-job serving. The first guarded run passed 159 tests;
one new boundary fixture violated the existing minimum edit-window size.
That failure is retained. Only the two boundary/tolerance test functions were
corrected; the complete affected module then passed all 19 tests. Production
source stayed identical across both runs. The Node contact-diagnostics suite
also passes. This is targeted coverage, not a new full repository CI claim.

On the actual KayKit rig, two constructed stance requests each cover 182
foot/key combinations and 546 patch-point observations. Ordinary edit limits
produce no necessary conflict. Tight ankle/angle limits expose 456 conflicting
point observations before any optimizer runs. Neither result approves a
corrected clip. All three recorded resource traces replay successfully, with
no memory-guard stop. Local evidence is in
`reports/studio-plant-preflight-v1/`, `reports/studio-plant-preflight-v2/`,
`reports/studio-plant-preflight-rig-v1/` and
`reports/studio-plant-preflight-publication-v2/`. The first publication verifier
mistakenly expected subtests to be separate JUnit case elements; its failure
is retained in `reports/studio-plant-preflight-publication-v1/`.
