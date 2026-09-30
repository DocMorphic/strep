import sys
import shutil
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from recover_pair_geometry import recover_current,extraction_kernel
from strep import ROOT,save,read,sha256
from test_scene_pair_problem import actors


def fixture(folder):
    (folder/'implementation').mkdir();(folder/'current').mkdir();methods={}
    for name in ['study_scene_pair_relinearization.py','strep.py','build_guarded_pair_witnesses.py','convex_partner_surface.py',
                 'scene_pair_problem.py','timed_rotation_edit.py','paired_approach_basis.py','rig_asset.py','rig_clip_import.py']:
        shutil.copyfile(ROOT/'scripts'/name,folder/'implementation'/name);methods[name]=sha256(folder/'implementation'/name)
    pair=actors();worlds=[a['model'].source_world for a in pair];controls=np.zeros(sum(a['model'].size for a in pair));directions=[]
    for a in pair:a['faces']=np.array([[0,1,2]])
    for s,t in [(0,1),(1,0)]:
        a,b=pair[s],pair[t];p=a['skin'].evaluate(worlds[s],np.array([0]),np.array([0]))[0]@a['rotation'].T+a['translation']
        tri=b['skin'].evaluate(worlds[t],np.zeros(3,int),np.arange(3))@b['rotation'].T+b['translation']
        bary=np.array([.2,.3,.5]);q=bary@tri;normal=np.array([1.,0.,0.]);gap=float((p-q)@normal)
        record=dict(vertex=0,target_triangle=0,target_vertices=[0,1,2],barycentric=bary.tolist(),normal=normal.tolist(),
            gap_m=gap,source_position_m=p.tolist(),target_position_m=q.tolist())
        directions.append(dict(source=s,target=t,selected_witnesses=1,maximum_depth_m=max(0.,-gap),records=[record]))
    save(folder/'current/sample-000.json',dict(sample=0,time_s=0.,directions=directions))
    save(folder/'request.json',dict(study=str(folder/'parent'),cumulative_controls=controls.tolist(),inputs={},implementation=methods))
    return pair,worlds,controls


@pytest.mark.parametrize('fault',[None,'controls','clock','gap','point','incomplete_snapshots','snapshot','completed','hole'])
def test_recovery_binds_geometry_and_checks_recorded_witnesses(tmp_path,fault):
    pair,worlds,controls=fixture(tmp_path)
    if fault=='controls':controls[0]=.1
    if fault in ['clock','gap','point']:
        row=read(tmp_path/'current/sample-000.json')
        if fault=='clock':row['time_s']=.1
        if fault=='gap':row['directions'][0]['records'][0]['gap_m']+=.01
        if fault=='point':row['directions'][0]['records'][0]['source_position_m'][0]+=.01
        save(tmp_path/'current/sample-000.json',row)
    if fault=='incomplete_snapshots':
        request=read(tmp_path/'request.json');request['implementation'].pop('convex_partner_surface.py');save(tmp_path/'request.json',request)
    if fault=='snapshot':(tmp_path/'implementation/strep.py').write_text('changed')
    if fault=='completed':save(tmp_path/'result.json',dict(status='complete'))
    if fault=='hole':(tmp_path/'current/sample-000.json').rename(tmp_path/'current/sample-001.json')
    if fault is None:
        recovered,files=recover_current(tmp_path,tmp_path/'parent',controls,{},pair,worlds)
        assert list(recovered)==[0] and recovered[0][1] is True
        assert files[str(tmp_path/'current/sample-000.json')]==sha256(tmp_path/'current/sample-000.json')
    else:
        with pytest.raises((ValueError,AssertionError)):recover_current(tmp_path,tmp_path/'parent',controls,{},pair,worlds)


def test_extraction_kernel_ignores_orchestration_but_rejects_query_changes():
    source=(ROOT/'scripts/study_scene_pair_relinearization.py').read_text()
    assert extraction_kernel(source)==extraction_kernel(source+'\n# orchestration comment\n')
    changed=source.replace("query(points[s],points[t],actors[t]['faces'])","query(points[s],points[t],actors[s]['faces'])")
    assert extraction_kernel(source)!=extraction_kernel(changed)
