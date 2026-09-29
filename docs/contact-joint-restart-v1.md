# Full-joint restart of retained contact failures

The root-only repair cannot solve every contact miss. In the retained crawl-11 candidate, the maximum horizontal hand-pin error is 5.007995 mm against a 5 mm tolerance. Kick-11 reaches 44.484085 mm horizontally and 63.214993 mm in total. Vertical root translation cannot remove those horizontal errors while rotations and root XZ remain fixed.

The preceding full-joint fits stopped at iteration limits. Their poses remain representable by the original correction spline: recovering controls after restoring held source keys gives maximum rotation-vector errors of 4.31e-8 radians for crawling and 3.20e-8 for kicking. Maximum original-relative rotation changes are approximately 32.34 and 25.27 degrees, below the existing 40-degree budget. These facts justify testing a bounded restart; they do not establish feasibility or motion quality.

## Declared experiment

`scripts/study_contact_joint_restart.py` runs crawl-11 followed by kick-11. Each uses its retained fitted poses as a warm start, six outer fitting stages and up to 120 optimizer iterations per stage. The original run used four stages. Optimizer history and inequality multipliers restart from their normal initial state; only poses carry over.

All twenty existing body-joint controls remain available. Root lift is still bounded by 0–0.22 m relative to the immutable original source, rotation changes by 40 degrees, and root XZ remains fixed. The source also defines point/global rate and floor references. The edit window remains frames 10–109, with 22 held native keys including adjoining endpoints. Those keys are restored exactly before initialization and preserved after fitting.

The method retains tolerance-scaled authored-point constraints, quarter-frame point/rate/floor guards, sparse skin evaluation and the existing physical root-coordinate bounds. It does not apply the new root-only export-feedback repair afterward; that separation identifies what the full-joint restart itself accomplishes.

The comparison changes both initialization and the number of outer stages. It tests this combined configuration, not an isolated causal benefit of warm starts. These remain development examples with authored targets, not held-out actions or naturalness evidence.

## Verification and retained evidence

The runner verifies the historical benchmark, snapshots its current Python/Godot implementation and hashes source, seed, contact-policy and mesh inputs. It recomputes the original point-rate reference before fitting, checks original global-rate ceilings afterward, and verifies root/rotation budgets against the original source rather than the warm seed. Every final candidate is exported and independently audited for pins, per-time floor regression, outside preservation, point/global rates and body flags, then receives an actual engine check. Failed results remain stored and unapproved.

Twenty-nine focused tests pass: eight restart-budget checks, seventeen exact held-pose checks and four initialization checks. The new tests include counterexamples where a candidate fits within a fresh allowance relative to the warm seed but exceeds the original root or rotation budget. The CLI help check also passes.

```powershell
.venv\Scripts\python.exe scripts/study_contact_joint_restart.py --suite reports/contact-breadth-v1 --output reports/contact-joint-restart-v1
```

The output folder must be new. The completed original archive, licensed local assets and pinned Godot acquisition are required. This is a development runner, not an automatically approved Studio correction.

Execution has started under a recorded live process identity. Crawling's re-exported warm seed still misses four of 81 pin samples, with a 5.012671 mm maximum. Its point-phase rate limits pass, raw added floor depth is now zero, and all 80 outside samples have exactly zero pose/basis/skin difference. This establishes the restart input; no restarted-fit result is available yet. The original benchmark and all release approvals remain unchanged.
