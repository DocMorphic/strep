# Repair proposals around rejected motion

`scripts/recentered_coupled_contacts.py` adds a proposal model for repairing an
exported candidate that fails native motion limits. Earlier coupled improvement
models require a feasible starting motion. This model can calculate derivatives
around a rejected candidate while keeping the preceding feasible motion as its
contact reference. It does not select or approve an animation.

The original `SceneProblem` supplies the source motion, control boxes, rate clock,
rate caps and tolerances. Both candidate and reference controls must remain in
those boxes. Both decoded world populations must contain every actor and sample.
The preceding reference must pass every native condition. Source rate settings
are checked before and after model construction; the rejected motion cannot
replace that baseline.

The model retains the complete native row prefix, including contact position and
frame speed. Complete surface orientation and side-gap rows are duplicated into
hard individual contact guards. A guard compares the current candidate with the
preceding feasible motion: previously passing rows must remain passing, and
previously failed rows must not gain excess. Separate soft rows retain the
original authored conditions so remaining failures stay visible.

Signed side gaps use positive affine norm offsets. A reference gap can exceed
the offset chosen at the candidate. In that case the offset is expanded for both
candidate and reference. The physical gap, clearance, scale and derivative stay
unchanged. This coordinate change is recorded; it does not relax a contact limit.
Symmetric continuous derivatives are calculated around the current candidate,
with decoded vectors as the anchor and the existing recorded one-sided fallback
near a control boundary. No measured small derivative is discarded.

## Use and limits

```python
from recentered_coupled_contacts import RecenteredCoupledContactModel

model = RecenteredCoupledContactModel(problem, surface_policy, contacts_digest)
system, jacobian, identity = model.linearize(
    rejected_controls, rejected_decoded_worlds,
    previous_feasible_controls, previous_decoded_worlds,
    trust=.02, step=.001,
)
```

This is a model-construction API, not a repair command or Studio feature. A
caller must bound and preserve solver proposals, independently export and
decode each trial, check all original native conditions and original/preceding
contact guards, then evaluate the complete declared geometry before retaining
any change. Solver success and affine feasibility do not establish nonlinear
saved-motion feasibility. Geometry is not part of this proposal model.

There is no real-character restoration result yet. The separate cumulative
study continues on its unchanged methods and inputs. This component does not
alter that worker, source limits, historical failures or release evidence. Floor,
partner, self-collision, continuous collision, engine equivalence and human
motion quality require their own evidence.

## Validation

All 28 focused tests pass. Exported synthetic GLB fixtures cover world and partner
targets, touch and hold clocks, a nonzero feasible reference, rejected native
origins, worsened contacts, complete paired row/Jacobian populations and exact
source caps. They also reject changed rate settings, incomplete/nonfinite worlds,
outside controls and invalid contact encodings. Offset-expansion tests compare
physical residuals before and after the coordinate change. An isolated source
copy passes 314 native/contact/geometry/solver checks without vendor models or
downloaded characters. These are bounded fixture checks, not production repair
success or quality approval.

Local evidence stays under ignored `reports/recentered-coupled-contacts-tests-v1.log`
and `reports/recentered-coupled-contacts-clean-source-v1`. Public CI includes the
new focused suite alongside the existing checks.
