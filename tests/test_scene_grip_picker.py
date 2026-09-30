"""Cross-check browser-authored grips against the actual region compiler geometry."""
import json
import shutil
import subprocess
import sys
from pathlib import Path
import numpy as np
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from object_geometry import Geometry
from action_studio_server import allowed_file


def test_picked_grips_meet_backend_surface_contract():
    node=shutil.which('node')
    if not node:pytest.skip('Node is required for the actual browser geometry cross-check')
    result=subprocess.run([node,'tests/test_scene_grip_picker.mjs','--fixture-json'],cwd=ROOT,capture_output=True,text=True,check=True)
    rows=json.loads(result.stdout)
    assert len(rows)==453
    for row in rows:
        normal=Geometry.parse(row['geometry']).local_surface_normal(row['point'])
        np.testing.assert_allclose(normal,row['normal'],atol=1e-12)


def test_grip_module_uses_existing_static_file_boundary():
    assert allowed_file('/scene-grip-picker.js')==ROOT/'scripts/scene-grip-picker.js'
    assert allowed_file('/../scene-grip-picker.js') is None
