# Preserve solver-point identity in synthetic backoff tests

Hosted run [38021940453](https://github.com/DocMorphic/strep/actions/runs/38021940453), source `965aa7f`, passes all ten source/material jobs and fails both native adapter jobs on the same synthetic backoff fixture. The fixture previously zeroed unconstrained coordinates after solving. Recorded raw solver points still contained the original coordinates, so the new observation-to-selected-point integrity check correctly rejected the archive.

The backoff fixture now supplies a deterministic synthetic solver response with the desired zero unused coordinates **before** the production helper records and checks it. Original bounds, scalar/vector populations, captured points and selected points remain consistent. The helper checks the complete original affine problem, and interval replay checks the saved native backoff pose. Other fixtures retain real Clarabel solves. No production solver, replay check, tolerance, motion or retention behavior changes.

An initial attempted fixture repair fixes those coordinates through bounds but fails because the altered bounds do not match the archived native problem. That failed run remains immutable. The final resume/conic/integration suites pass **135 tests in 41.43 seconds**. Their supervisor completes in 46.875 seconds, sampled peak 593,076,224 bytes, with all 46 resource observations independently replayed. The earlier supervisor deferral for an existing owned worker and the failed test run remain separately recorded. Hosted CI for the corrected fixture remains pending.

These are regression-test results, not animation-quality evidence. Continue the same full-project goal; release approvals remain unchanged.
