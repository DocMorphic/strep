# Explicit rig preparation in Studio

Studio's native foot-support editor now offers an unchecked preparation choice
when a selected rig has eligible tiny static scale differences. Eligibility is
a static preflight, not geometry approval. The worker creates a separate input
version and runs the existing full geometry/rigidity checks before fitting.
See [rig preparation and multi-surface fitting](native-support-rigs-v1.md).

The limits remain 5e-7 static scale drift and 1e-5 m sampled geometry change.
Animated non-unit scales, scaled matrices and larger differences are rejected.
Original meshes, inverse binds and native animation bytes remain unchanged.
The prepared draft changes only the source GLB hash; authored contact windows,
planes, displacement limits, angles and source-relative rate gates remain fixed.

Original input, prepared input, retained candidate and every completed proposal
are separately available for review. The comparison reports changed nodes and
sampled mesh distance. The original source/draft, conversion result/methods,
derived draft and numerical runtime are hash-bound; mutations reject review or
serving. A retained prepared input is explicitly labelled. Failed candidates
do not become approved animations.

## Actual worker verification

A real Studio CLI worker reused the previously examined Quaternius female wave
clip and the published authored support draft. This is development evidence,
not a new model generation or held-out case. The first verification completed
fitting but failed byte parity for two proposals. Its outputs and failure
record remain under `reports/studio-support-preparation-v1`.

The runtime diagnostic found both OpenBLAS pools at 16 threads: the initial
thread limit preceded NumPy/SciPy's lazy imports. The worker now loads its
numerical dependencies before entering a one-thread context and binds the
observed pool counts to completion. The caller's prior limits are restored.

A fresh job under `reports/studio-support-preparation-v2` observes both pools
at one thread. All six fitting GLBs (input, candidate and four proposals) are
byte-identical to the earlier female CLI study. Its existing Godot bone and
skin audits therefore apply by exact file identity; they are not a new browser
render or fresh engine run of the Studio job.

The original GLB hash is
`f5736e8d509e421e1af3e1c74f7d17745eccd7c985cfd1f413cf00b3be334a3b`.
The prepared input hash is
`0101488285d9610d3d61ef4559e6a7fde1aa9c7fd03334f451d1f869349d0456`.
Preparation changes 29 static nodes and compares 701 poses plus the reference;
maximum sampled mesh change is 1.1596143472e-7 m (0.116 micrometres).
The review manifest hash is
`ade8f7ea8d4355f7bcbf7dd0e9ac651bf02a2a8feb6d679359c8448762cb597e`.
The fresh worker verification result hash is
`e7b2316e663f64a04ebe2afb75ac7d977158c04034f4ee4934ad67252059c700`.
Its original/prepared evidence, preserved first failure and reused engine
bindings are included in the action study's 2,456-file rehash receipt.

All four proposals still fail the unchanged source-relative rate selection.
The candidate remains the exact prepared input. Preparation improves input
compatibility; this experiment does not establish motion naturalness.

## Validation and limits

Twenty-two new Python tests cover explicit choices, static eligibility versus
geometry failure, original/derived isolation, changed evidence and bounds,
runtime restoration, and HTTP origin/busy/serving guards. The HTTP fixture runs
the real handler and worker function with a substituted launcher. The separate
actual CLI job verifies real process execution. JavaScript DOM tests cover the
unchecked choice, immutable submitted draft, source changes and retained-input
feedback. The complete model-free source suite passes 1,422 Python tests and
14 JavaScript suites, including reproducible Studio bundle construction.

No fresh live-server/browser or GPU render was verified. Existing completed
jobs without runtime receipts remain readable without a new runtime claim.
No training, independent cleanup review or release approval occurred. The
broader [action diagnostics](native-support-action-breadth-v1.md) retain the
unresolved support and derivative failures.
