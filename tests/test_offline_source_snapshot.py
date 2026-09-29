import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import offline_source_snapshot as snapshot
from build_offline_install import copy_tree


@pytest.fixture
def source(tmp_path):
    root=tmp_path/'source'
    for directory in snapshot.PROJECT_DIRECTORIES:(root/directory).mkdir(parents=True)
    for name in ['scripts/main.py','scripts/scene-feedback.js','assets/model.txt','benchmarks/cases.json','integrations/import.gd',
                 'scripts/__pycache__/main.pyc','scripts/.git/config','scripts/local.pth','scripts/__editable__tool.py']:
        path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('synthetic '+name)
    return root,tmp_path/'installation'


def test_complete_project_copy_and_existing_exclusions(source,tmp_path):
    root,dest=source;record=snapshot.capture_project(root)
    assert len(record['files_sha256'])==5
    snapshot.copy_project(root,dest,record)
    assert snapshot.verify_project(root,dest,record)==5
    runtime=tmp_path/'runtime';copy_tree(root/'scripts',runtime)
    assert sorted(p.name for p in runtime.rglob('*') if p.is_file())==['main.py','scene-feedback.js']
    with pytest.raises(ValueError,match='Preserve'):snapshot.copy_project(root,dest,record)


@pytest.mark.parametrize('change',['modify','add','remove','destination'])
def test_changed_source_set_or_destination_cannot_pass_final_check(source,change):
    root,dest=source;record=snapshot.capture_project(root);snapshot.copy_project(root,dest,record)
    if change=='modify':(root/'scripts/main.py').write_text('new revision')
    if change=='add':(root/'scripts/added.py').write_text('new module')
    if change=='remove':(root/'scripts/main.py').unlink()
    if change=='destination':(dest/'scripts/main.py').write_text('damaged copy')
    with pytest.raises(RuntimeError):snapshot.verify_project(root,dest,record)


def test_change_after_capture_is_rejected_during_copy(source):
    root,dest=source;record=snapshot.capture_project(root)
    (root/'scripts/main.py').write_text('changed after capture')
    with pytest.raises(RuntimeError,match='during copy'):snapshot.copy_project(root,dest,record)


def test_unsafe_inventory_path_and_overlapping_destination_rejected(source):
    root,dest=source;record=snapshot.capture_project(root)
    with pytest.raises(ValueError,match='separate'):snapshot.copy_project(root,root/'nested',record)
    record['files_sha256']['../outside']='0'*64
    with pytest.raises(ValueError,match='Unsafe'):snapshot.copy_project(root,dest,record)
