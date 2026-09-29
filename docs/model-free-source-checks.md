# Public source checks

The public repository now defines a GitHub Actions workflow for a small suite that needs no motion checkpoint, gated text encoder, character payload, saved study or Godot executable. It runs on Windows and Linux with Python 3.10, pinned NumPy/SciPy/pytest requirements and Node 24. Both push and pull-request events run it; manual dispatch is also available.

The suite checks primitive preview geometry, endpoint travel bounds, exact rate/pose conflict certificates, reproducibility of the Studio HTML build and offline contact-editor behavior. This is software regression coverage, not a full-suite, inference, engine, visual or animation-quality approval. The legacy geometry/scene comparison test imports the full Torch-based pipeline and remains outside this model-free suite.

Before publication, a tracked-files archive of commit `954b6fc` was extracted into a new directory with no local `reports`, `models` or virtual environment. A fresh isolated Python environment installed only `requirements-ci.txt` and its package dependencies. All **48 selected Python tests and both Node editor tests passed** from that extracted checkout. Initial collection exposed the legacy geometry test's Torch dependency; it was excluded from this explicitly model-free suite, not changed or presented as passing. Local evidence stays under ignored `reports/model-free-ci-v1`.

The workflow follows [GitHub's Python testing guidance](https://docs.github.com/en/actions/tutorials/build-and-test-code/python). Action revisions are pinned to full commits, its token has read-only contents permission, checkout does not persist credentials, and test execution sets the Hugging Face/Transformers offline flags. Dependency installation still requires network access on a new runner; this does not establish a complete offline installation of Strep.

## Run locally on Windows

Use a separate environment to preserve an existing inference installation:

```powershell
py -3.10 -m venv .venv-ci
.venv-ci\Scripts\python.exe -m pip install --only-binary=:all: -r requirements-ci.txt
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
.venv-ci\Scripts\python.exe -m pytest -q tests/test_object_geometry_mesh.py tests/test_point_rate_reachability.py tests/test_contact_rate_feasibility.py tests/test_contact_pose_reachability.py tests/test_contact_pose_sphere_bound.py tests/test_desktop_build.py tests/test_desktop_build_preservation.py
node tests/test_contact_timing_editor.mjs
node tests/test_contact_export_review.mjs
```

The dedicated environment is ignored by Git. The broader test suite still requires separately provisioned assets and tools; all release capabilities remain unapproved.

## Hosted verification

[GitHub run 36642216213](https://github.com/DocMorphic/strep/actions/runs/36642216213), at commit `ac78f29`, passed on both Windows and Linux: 48 Python tests and both Node editor checks per operating system. The first workflow attempt failed YAML parsing because an unquoted command contained a colon; the corrected workflow uses a block string and was locally parsed before the successful run. Hosted success covers this declared source suite only, not the complete model or game-animation pipeline.
