# Native body constraints during contact fitting

The contact fitter previously had a small rotation regularizer and a soft added-speed penalty, while independent review rejected joint displacement above 22 cm or added joint speed above 1.5 m/s relative to either original raw or limb motion. A retained kicking fit therefore improved its foot target while exceeding body-change limits and adding a support-gap regression.

`NativeBodyObjective` adds a separate augmented inequality for every reference, native frame and joint. The two residuals are displacement norm divided by 0.22 m minus one, and the norm of the displacement's 30 Hz first difference divided by 1.5 m/s minus one. These measure changes from the corresponding reference, not the character's travel speed. Reference tensors are copied and detached; distinct raw and limb histories remain independently enforced. Violations are summed rather than diluted by averaging over inactive frames.

The optional `native_body_references` argument in `support_contact_v8.refine` evaluates the new objective, updates its multipliers at accepted outer stages and records reference-specific peaks. Defaults and Studio fitting remain unchanged until measured results justify adopting the new mode. This is an augmented penalty method, not a hard feasibility guarantee. It adds no support, anatomical or dynamics proof, and the independent body and export audits remain required.

## Declared comparison

The development runner accepts source, seed and saved-check directories without action-name restrictions. Its first experiment uses the exact retained kick-11 request and warm seed from the [previous six-stage restart](contact-joint-restart-v1.md). It retains six outer stages, 120 iterations per stage, original controls, the held edit window, the 5 mm foot target, 40-degree rotations, 0–22 cm root lift, fixed root XZ, and original export point/global rate and floor constraints. The new raw/limb body inequalities are the intended change. It does not enable a separate support-preservation mode or silently loosen acceptance limits.

Inputs and current Python/Godot methods are copied and hashed before fitting. Outputs are retained in a new folder, then independently exported and audited, including engine playback. Final native body peaks are recomputed from the saved NPZ. All failed results remain available and unapproved; source or previous candidates are never replaced.

```powershell
.venv\Scripts\python.exe scripts/study_native_body_constraints.py --source reports/contact-jobs/contact-breadth-v1-kick-11-repair/source-take --seed reports/contact-jobs/contact-breadth-v1-kick-11-repair/seed --checked-plan reports/contact-jobs/contact-breadth-v1-kick-11-repair/checked-plan --output reports/native-body-constraints-v1
```

## Verification before measurement

Fifty-five focused tests pass, covering the new objective's gradients, both independent references, immutable reference copies, pose-only and speed-only violations, unchanged fast source movement, multiplier updates and invalid inputs; existing rate, support, restart-budget, initialization and held-pose tests also pass. Four existing Torch deprecation warnings remain. CLI argument parsing passes.

The experiment was launched under a verified live worker identity. Its outcome is not yet established; optimizer loss and successful processing are not acceptance or realism evidence. The full project goal and all fourteen release capabilities remain open.


A [full-distance skin bound](contact-pose-sphere-v1.md) now proves kick-11 also conflicts with the current native edit screen: frame 50 requires at least 26.519804 cm versus the 22 cm budget. Exact outward rational bounds verify two new frame/reference conflicts; all 316 retained calculations were replayed, with no motion or acceptance changes. Twenty focused bound tests pass. The already-running body-constraint experiment remains frozen; its result will be retained, then the stronger certificate should enter Studio preflight. No further iteration-only retries are justified for this request.
