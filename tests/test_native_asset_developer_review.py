"""Native review packages preserve bytes and cannot manufacture human approval."""
import copy,sys,zipfile
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import native_asset_developer_review as review
from strep import read,sha256
from test_native_component_storage import fixture


def data(tmp_path):
    (tmp_path/'source').mkdir()
    base,*_=fixture(tmp_path/'source');asset=Path(next(iter(base.scene.inputs)))
    node=base.scene.actors['A']['rig'].document['nodes'][0]['name']
    license_path=tmp_path/'license.txt';license_path.write_text('Synthetic test asset attribution.')
    case=dict(id='native-test',glb=str(asset),sha256=sha256(asset),animation_index=0,fps=30,
        segments=[dict(prompt='A test pose')],reference_node=node,
        review_context=dict(note='Synthetic test, no human review.',flat_floor_screen_applicable=False,unavailable_categories={}))
    return case,license_path


def test_packet_preserves_actual_native_geometry_and_motion(tmp_path):
    case,license_path=data(tmp_path);packet=tmp_path/'packet';archive=tmp_path/'packet.zip';source=Path(case['glb']).read_bytes()
    result=review.build([case],packet,archive,license_path);manifest=read(packet/'manifest.json')
    assert manifest['review_type']=='developer' and not manifest['quality_approved'] and not manifest['release_approved']
    assert (packet/manifest['cases'][0]['path']).read_bytes()==source
    assert manifest['cases'][0]['reference_node']==case['reference_node'] and manifest['cases'][0]['animation_index']==0
    assert manifest['cases'][0]['reference_node_index']==0
    assert manifest['cases'][0]['duration_s']==2. and manifest['cases'][0]['frames']==61
    assert result['human_reviews_collected']==0 and result['all_native_clip_bytes_preserved'] and not result['independent_review']
    assert not result['quality_approved'] and not result['release_approved']
    assert (packet/'LICENSE.txt').read_bytes()==license_path.read_bytes()
    assert 'not blinded' in (packet/'README.txt').read_text() and 'Condition and seed labels are hidden.' not in (packet/'README.txt').read_text()
    inventory=read(packet/'package-integrity.json')['files']
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for name in inventory:assert z.read(name)==(packet/name).read_bytes()
    assert not any('source' in n for n in inventory)


@pytest.mark.parametrize('fault',['hash','reference','fps-bool','animation-bool','id-path','duplicate','missing-context','bad-na','external-path'])
def test_bad_population_or_bindings_reject_before_packet_creation(tmp_path,fault):
    case,license_path=data(tmp_path);cases=[case];packet=tmp_path/'packet'
    if fault=='hash':case['sha256']='0'*64
    elif fault=='reference':case['reference_node']='missing'
    elif fault=='fps-bool':case['fps']=True
    elif fault=='animation-bool':case['animation_index']=False
    elif fault=='id-path':case['id']='../other'
    elif fault=='duplicate':cases.append(copy.deepcopy(case))
    elif fault=='missing-context':case['review_context']={}
    elif fault=='bad-na':case['review_context']['unavailable_categories']={'action':'hidden'}
    else:case['glb']=str(packet/'clip.glb')
    with pytest.raises(ValueError):review.build(cases,packet,tmp_path/'packet.zip',license_path)
    assert not packet.exists()


def test_existing_packet_and_archive_are_preserved(tmp_path):
    case,license_path=data(tmp_path);packet=tmp_path/'packet';packet.mkdir();marker=packet/'keep';marker.write_text('preserve')
    with pytest.raises(ValueError):review.build([case],packet,tmp_path/'packet.zip',license_path)
    assert marker.read_text()=='preserve'


def test_namespace_bone_names_keep_original_native_index(tmp_path):
    from rig_asset import RigAsset
    from gltf_tools import write_glb
    case,license_path=data(tmp_path);source=Path(case['glb']);rig=RigAsset.load(source)
    document=copy.deepcopy(rig.document);document['nodes'][0]['name']='mixamorig:Hips'
    write_glb(source,document,rig.binary);case.update(reference_node='mixamorig:Hips',sha256=sha256(source))
    packet=tmp_path/'packet';review.build([case],packet,tmp_path/'packet.zip',license_path)
    row=read(packet/'manifest.json')['cases'][0]
    assert row['reference_node']=='mixamorig:Hips' and row['reference_node_index']==0
    assert (packet/row['path']).read_bytes()==source.read_bytes()
