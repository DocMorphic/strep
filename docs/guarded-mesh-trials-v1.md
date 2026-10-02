# Experimental bounded mesh-contact trials

The opt-in mesh feasibility solver can now retain useful intermediate proposals
from constraint evaluations and sample partial steps toward contact iterates.
This follows the fixed crawl study where floor restoration succeeded but contact
targets remained outside the authored tolerance. It does not change that study's
saved results or establish that the new search improves real animation quality.

Enable both `--feasibility` and `--guarded-trials` on
`scripts/rig_mesh_trajectory.py`. The default feasibility path remains unchanged.
At contact callbacks, the experimental path samples eight segment fractions from
1 through 1/128. Where a segment violates the sampled floor constraint, it tries
a common vertical root-control lift calculated from the existing skin weights
and temporal basis. Fixed geometry that cannot be lifted remains a failure.
Candidates must satisfy the original edit and motion limits; contact-stage
selection also requires the floor's existing one-percent interior margin.
Targets, contact times, budgets and quality thresholds are not relaxed.

Each phase saves finite examined control vectors, warm parameters, basis and
selected controls in a compressed trial archive, with separate records of
retention and rejection reasons. A candidate must still pass the existing
independent audit and solver-completion requirement to be accepted. All files are
included in the hash-bound output inventory; generated archives remain local
under ignored `reports/`.

Fixture tests compare the fast limit values against the original Jacobian path,
check whole-mesh floor protection, frozen geometry and over-budget rejection,
replay retained proposals, and exercise actual GLB export and mode isolation.
The [fixed crawl follow-up](crawl-body-contact-guarded-trials-v1.md) now measures
this path and records its contact regression and between-key floor failure.
No animator review or cleanup-time measurement accompanies it. It adds search evaluations and
storage, so matching iteration budgets do not imply equal computation. Sampling
does not establish continuous collision freedom, anatomical contact correctness,
convergence or infeasibility. Release capabilities remain unapproved.

Validation for this source batch: all 1,511 model-free Python tests and 14
JavaScript suites pass, including the 11 new guarded-trial cases. The later
export-gate follow-up passes 1,533 Python tests and 14 JavaScript suites. These
checks do not replace release review.
