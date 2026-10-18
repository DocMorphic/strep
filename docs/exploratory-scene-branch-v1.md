# Fixed final checks during exploratory correction

Development component, 2026-10-18. A rejected pose can be useful as a new
numerical center for geometry derivatives. Exploring it must not select that
pose, reset its edit allowance or replace the original final acceptance test.

`ExploratorySceneBranch` owns a copy of an original `SceneStepGuard`. Complete
named observations can update its numerical center even when they fail the
final gate. Original control-vector balls still apply to every exploratory
point. The fixed required/protected masks and original worst-search-progress
target never advance. Changing the caller's guard later cannot change the
branch's final gate.

Reports distinguish a final retention-gate pass from **all supplied rows being
nonnegative**, and both from animation approval. This matters when an original
physical condition was already failing and was not part of the required or
protected subset. Passing the subset cannot turn that remaining failure into
a pass. Even an exploratory point satisfying every supplied numeric row does
not advance the accepted guard or select a clip.

Inputs, properties and nested reports have owned values. Invalid, incomplete,
misordered or nonfinite observations and controls outside the original author
balls reject without changing the exploratory state. The class keeps only its
current observations and a count; caller-owned study files preserve history.
It does not bind character assets or manufacture geometry measurements.
Callers must keep the original rig, tracks, permissions and physical criteria
bound and supply complete independent observations.

All **237 focused source cases pass locally**, including the previous 221
and sixteen new cases. The new cases exercise rejected and numerically passing
exploration, original masks and progress targets, chained moves within fixed
author balls, caller mutation, owned reports and invalid complete observations.
Hosted results will be recorded when complete.

The real scene experiment refreshes all 120 original frames and complete
surface/motion queries around a previously rejected pose, keeping the original
final gate. Detailed results will be recorded when the assembled model and
proposal checks finish. Local source evidence:
`reports/exploratory-branch-tests-v1`. The broad project goal and release matrix
remain unchanged.
