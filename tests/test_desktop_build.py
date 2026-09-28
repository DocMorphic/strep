"""A fresh local build must retain the currently shipped authoring controls."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from build_desktop import render,ROOT


def test_desktop_bundle_is_reproducible_from_its_sources():
    assert render()==(ROOT/'scripts/action-studio.html').read_text(encoding='utf8')
