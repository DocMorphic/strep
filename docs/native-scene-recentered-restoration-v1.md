# Recentered native scene restoration

The native scene fitter offers an explicit experimental restoration model:

```powershell
python scripts/native_scene_fit.py contacts.json permissions.json reports/recentered-fit --proposal-model storage-vector --iterations 2 --vector-difference-scheme central --rotation-storage-policy source-scale --restoration-steps 3 --restoration-model recentered --serialized-ray-probes 64 --resume-from reports/prior-fit --geometry-policy geometry-policy.json
```

This requires a configured local Python environment and completed, source-bound
prior fit. The default remains `measured-cap`; scalar, ordinary vector and
surface-vector proposals cannot select the recentered model. The request and
result record the choice. Resume still reproduces the prior final GLB byte for
byte against the first native source epoch and unchanged motion-cap arrays.

## What changes

After a full primary proposal fails its decoded protected conditions, a
recentered restoration rebuilds every local vector row at that retained export.
Its intercept comes from actual GLB decoding. Its finite-difference derivatives
use the configured stored or continuous proxy and forward or symmetric stencil.
The new conic direction is relative to that candidate's controls, with the
original control boxes and a bounded local trust radius.

Contact no-worsening bounds continue to use the original accepted iteration
reference. A rejected candidate's worse contact cannot become its new permitted
baseline. Original authored contact rows remain in the objective and final
audit; rebuilding the model changes neither targets nor timing nor limits.

Each restoration tests at most ten backoffs. A candidate is accepted only after
its complete export passes all original source/edit/displacement/rate rows,
every original contact no-worsening check and strict overall merit improvement.
A failing candidate may become the next model anchor only when its measured
protected-defect merit decreases. This is provisional computation; it does not
replace the original or approve the animation. There are at most four
restoration models per primary iteration, each triggered at the first primary
backoff. Anchor labels, controls, derivatives, solver results and every exported
trial remain archived.

No source cap is tightened by this alternative. The existing measured-cap model
continues to work as before. Neither method certifies a feasible correction;
actual decoding remains the acceptance authority. Rebuilding full derivatives
costs additional computation, so equal primary-iteration counts are not an
equal-compute comparison. Geometry, engine import and human-quality checks
remain separate requirements.

## Validation scope

Numerical regression fixtures exercise a genuine conic recovery, rejected source
and contact conditions, provisional anchor advancement, unchanged original
contact references, malformed configurations and native GLB resume with exact
cap-array preservation. Numerical fixtures and test directions are distinguished
from humanoid motion observations.

The preceding supplied crawl used a previously floor-restored rough clip with
54 controls and anatomically unreviewed 19/19/33/33-vertex contact patches.
Measured-cap restoration and finite actual-key probes accepted no correction;
all four holds remained above the unchanged 20 mm/0.005 m/s limits. Some
cap-tightening solves became infeasible. This motivates testing a model anchored
on the rejected decoded pose, without changing the accepted limits.

The finite continuation uses the same source, 54 controls, two primary
iterations, three restoration steps and 64 actual-key probes per iteration as
the preceding source-scale comparison. It accepts zero corrections. All 180
retained exports independently byte-replay, decode and pass explicit native
edit bounds; the final source-cap arrays match the original exactly. The final
clip is unchanged. All four revised holds still fail, with maximum position
errors of 37.84/79.10/91.81/88.20 mm and speeds of
0.19313/0.54886/0.25190/0.27585 m/s. Full sampled floor checks pass.

Five additional local models are attempted. Three return a direction, one
reports insufficient progress and one reports primal infeasibility. No rebuilt
model produces an accepted export. Independent diagnosis maps every protected
row to its source condition and retains all contact guard observations for ten
selected anchors, with exact full-array readback.

The first primary proposal's peak source failure is right-leg position
acceleration at 1.833333 s, exceeding its unchanged cap plus tolerance by
0.000973842 m/s². A later provisional restoration anchor lowers the maximum
normalized source excess from 2.77947e-5 to 1.30769e-5, but still fails. Its
largest contact regression is left-hand relative speed at 1.8375 s; it falls
from 2.98950e-5 to 1.53343e-6 m/s and still violates the original no-worsening
condition. A second-iteration anchor instead peaks in right-leg angular
acceleration at 2.233333 s. Numerical reductions do not establish usable motion
or convergence.

The unchanged final clip reuses the preceding completed CPU Godot import and
runtime evidence; this turn performs no new engine run. The final related
regression groups cover 212 unique passing Python cases, including 21 new
recentered-restoration cases. Trials and diagnostics remain locally under
`reports/native-crawl-recentered-restoration-v1/`.

The trial permits proximal leg edits but leaves distal nodes 6/7/10/11 outside
the declared permissions. A separate control-completeness experiment can test
that omission while retaining this failed benchmark, the original actor epoch,
source motion caps and contact intent. Added permissions must be declared;
such a trial cannot claim to pass the old permission contract. No new
inference, training, held-out validation, developer review submission or release
approval follows from this solver option. The full project goal remains active.
