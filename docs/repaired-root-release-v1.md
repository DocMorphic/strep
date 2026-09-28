# Release correction after a verified root repair

The foot follow-up must preserve the repaired root, not restart from the older held animation. `study_repaired_root_release.py` binds a completed source and its independent audit, verifies all non-release original comparisons already pass, copies the source parameters, eliminates all root coordinates, and keeps the existing protected joint. It may tighten frozen root/release envelopes to resolved source limits; it cannot loosen them. The existing selector chooses the largest remaining release excess and its acceleration centers plus two neighboring frames.

Three source-validation tests pass in3.44seconds: accepting a bound source with only release failures, rejecting a remaining root failure, and rejecting changed source/audit evidence. Rig03's actual-mesh preflight passes three directions, maximum error1.07e-5. The selected left release129 uses frames126–133,168 variables and67,988 inequalities.

The bounded SLSQP proposal terminates with status8 after seven iterations. The full endpoint is rejected. Only1/64 of the proposal is accepted, reducing the target acceleration23.736974→23.707514m/s²; the original22.708076 limit still fails. All three original failing releases remain. The root is identical to the repaired source (decoded matrix error0), with maximum12.147652m/s². All12 repaired-root checks pass,142 unrelated frames are unchanged, and450 native engine actor-frames verify import. This is a small guarded improvement, not successful release correction.

The independent audit retains the original-held fixed-root diagnostic, where root preservation is expected to be false. Its separate corrected-source root check is explicit. This prevents a changed baseline from concealing the earlier root failure or accidentally undoing its repair.

## Rejected second root block and a different proposal method

Rig02's second root block terminates with status8 after36 iterations. None of its eight safeguard fractions is feasible; its output bytes remain exactly the first root repair (`2e47db5d99217a224c713911b856dcf80b5145a4dc0664c457e0c33786d303d4`). Center77 remains12.222871m/s² versus11.673293. The independent audit confirms the unchanged result and450 engine actor-frames.

`diagnose_root_block_proposal.py` labels the rejected inequalities. The full endpoint violates right-foot acceleration at center75 (normalized margin-0.943952); smaller fractions mainly violate right support-speed constraints at step ends78–80. Geometry is evaluated separately and passes at all eight fractions. Earlier solver logs marked geometry false when feasibility prevented that check from running; that field alone did not prove a geometry failure.

`feasible_descent.py` then tests a separate method: at most12 small linearized descent steps, trust sizes1e-4/1e-5/1e-6,1e-6 normalized interior search margin and eight fractions each. Actual acceptance still requires all original serialized inequalities at-1e-8, geometry preservation and objective improvement. Three tests pass in0.64seconds, including rejection of a nonlinear violation despite linear feasibility. SciPy's warning about forwarding the single-thread HiGHS option is retained.

The actual experiment (`reports/feasible-root-descent-v1`) stops after its first iteration: all three linear programs solve, but all24 nonlinear candidate steps fail. It retains the same source GLB and unresolved root target. Independent reconstruction of the proposed-step history, strict checks and450 engine actor-frames confirms this outcome. This is evidence against that linear proposal method in the tested neighborhood, not proof that the original motion constraints are globally infeasible.

## Next formulation to test

A tangent approximation to a squared speed limit can miss perpendicular velocity changes, especially near zero speed. The next hypothesis is to keep the norm of the affine velocity/acceleration prediction as a second-order cone constraint, while still checking the actual serialized skin afterward. This changes proposal construction, not final acceptance.

Clarabel documents a direct Python interface using sparse matrices and nonnegative/second-order cones. Its pinned0.11.1 Windows wheel supports Python3.9+ and carries the Apache2.0 license. [Official interface documentation](https://clarabel.org/stable/python/getting_started_py/), [pinned package and wheel details](https://pypi.org/project/clarabel/0.11.1/).

`bootstrap_conic_solver.py` downloads the official Windows wheel, verifies SHA256`557d5148a4377ae1980b65d00605ae870a8f34f95f0f6a41e04aa6d3edf67148`, and retains it with its license in `vendor/clarabel-0.11.1`. No active environment packages were installed or upgraded. Bootstrap records all six retained file hashes. CVXPY, Clarabel, SCS and OSQP were absent from the environment before this isolated experiment; the Python environment also lacks pip.

`prove_conic_speed_constraint.py` tests a known boundary case: the tangent constraint accepts z=1 for velocity(z,1), although its true speed exceeds1 by0.414214. The conic result is z≈5.29e-8 with independently measured speed residual1.33e-15. Solver status is AlmostSolved after34 iterations and is retained. This small diagnostic supports investigating the formulation; it establishes neither solver convergence nor animation quality.

The intended next character trial should form cones for affine predicted foot velocity, foot/root acceleration and adjacent edit vectors; retain affine floor/selected-hover constraints, original box bounds, fixed trust budgets and actual serialized nonlinear acceptance. Freeze a new protocol, test the matrix/sign conventions and real-mesh predictions, and bind the vendored solver hashes before fitting. Do not merely rerun the failed SLSQP/linear trials with more iterations or silently widen their limits.

## Broader study

`whole-support-breadth-interim-v14` independently verifies14/24 completed cases. The second kneel/rise rig improves left support-speed maximum223.580→127.887mm/s, but right maximum rises131.478→503.407mm/s and root acceleration4.993→5.123m/s². Hover remains27.863/26.751mm; floor depth is0.186mm. Its360 engine actor-frames pass import. All motion-quality failures and missing animator reviews remain visible.
