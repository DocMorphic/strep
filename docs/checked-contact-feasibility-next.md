# Next experiment: explicit feasibility correction

The [longer solve](checked-contact-convergence-v1.md) leaves two small but genuine constraint violations after 1,028 evaluations. Its current optimizer directly bounds root coordinates, while position, rate and floor inequalities enter augmented objectives. The next experiment should determine whether a constrained correction can remove those residuals while preserving every already-passing check. This is a proposal, not a claimed solution.

## Available primary-source methods

The installed environment has SciPy 1.15.3 and PyTorch 2.10.0. SciPy's `NonlinearConstraint` accepts vector lower/upper bounds and callable dense or sparse Jacobians. It also exposes per-component feasibility preservation. These are relevant interfaces for representing contact and rate limits explicitly. [SciPy 1.15.3 documentation](https://docs.scipy.org/doc/scipy-1.15.3/reference/generated/scipy.optimize.NonlinearConstraint.html)

The `trust-constr` solver reports constraint violation separately from optimality and supports sparse Jacobians. Its gradient termination condition includes both Lagrangian-gradient and constraint-violation tolerances. Rank-deficient factorization can fall back to dense work, so memory and rank must be measured on this problem before adopting it. A success flag would still not replace the exported-motion audit. [SciPy 1.15.3 solver documentation](https://docs.scipy.org/doc/scipy-1.15.3/reference/optimize.minimize-trustconstr.html)

PyTorch's Jacobian transform supports row chunks; `chunk_size=1` computes rows without `vmap` restrictions. This provides a potential diagnostic fallback, not evidence that all of Strep's sparse skin operations work efficiently with the transform. The actual derivative path needs value, gradient, memory and runtime checks. [PyTorch 2.10 documentation](https://docs.pytorch.org/docs/2.10/generated/torch.func.jacrev.html)

## Proposed implementation order

1. Expose pure residual calculations for the unchanged point, per-point rate and full-floor constraints. Keep independent export measurements separate from solver diagnostics.
2. On the retained candidate, identify violated and near-active samples and test a small correction with derivatives checked against finite differences. Preserve the original source's global edit budgets and held boundaries; a warm start must not become a new reference that grants extra motion.
3. Measure derivative cost before attempting a dense full-clip constrained solve. Exclude mathematically constant locked rows from the optimization only when their preservation is established; continue auditing them after export. Floor witness changes and rate maxima make local derivatives insufficient for acceptance by themselves.
4. Re-export and inspect every original contact sample, full-mesh floor sample, rate phase, root/rotation bound and outside-window sample. Reject a proposed repair if it merely moves a violation elsewhere. Keep the failed proposal and optimizer termination information.
5. If this succeeds, repeat on predeclared development cases from other actions and then separate held-out cases; one nearly repaired get-up clip cannot validate general motion editing.

The existing environment does not have CVXPY or Clarabel installed. No solver package has been installed or selected on the assumption that it would solve this problem. The prototype should first test the available numerical interfaces and reuse relevant existing correction code where its bounds and sampling match.


Implemented experiment: [root-height feasibility repair](checked-root-feasibility-v1.md) uses the existing linear-program proposal helper and exact nonlinear rechecks in a restricted translation subspace. It clears the retained contact/rate residuals without changing caps. Full pose correction and broader action-family validation remain open; the trust-constr alternative was not adopted.
