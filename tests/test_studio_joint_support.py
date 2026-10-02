"""Opt-in joint search under unchanged native support and rate gates."""
from pathlib import Path
import copy
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from test_studio_native_support import setup
import studio_native_support as studio
from strep import read,save,sha256


@pytest.mark.parametrize('choice',[1,0,'true',None,{},[]])
def test_joint_search_choice_requires_boolean(setup,choice):
    body=copy.deepcopy(setup.body);body['joint_source_rate_search']=choice
    with pytest.raises(ValueError,match='choice'):studio.validate_request(body)


def test_joint_and_sampled_modes_are_explicit_alternatives(setup):
    body=copy.deepcopy(setup.body);body.update(joint_source_rate_search=True,sampled_support_repair=True)
    with pytest.raises(ValueError,match='one support'):studio.validate_request(body)
    body.pop('sampled_support_repair')
    for key in ('joint_search_evaluations','joint_evaluations','joint_swivel','joint_foot_orientation','repair_from'):
        candidate=dict(body,**{key:160})
        with pytest.raises(ValueError,match='draft required'):studio.validate_request(candidate)


def complete(setup):
    body=copy.deepcopy(setup.body);body['joint_source_rate_search']=True
    folder=studio.folder_for('joint-fixture');studio.prepare(body,folder);studio.run(folder)
    return folder,setup.root/'reports/native-support-fit-joint-fixture'


def test_actual_joint_search_archives_controls_and_retains_failed_source(setup):
    original=sha256(setup.source);folder,output=complete(setup);review=studio.manifest('joint-fixture')
    request=read(folder/'request.json');fit=read(output/'request.json')
    assert request['joint_source_rate_search'] is True and request['joint_search_evaluations']==160
    assert fit['joint_search_maximum_evaluations']==160 and fit['proposal_method']=='joint_support_source_rate_orientation_search'
    assert read(folder/'draft.json')==setup.spec
    assert review['joint_search']==dict(maximum_evaluations=160,swivel_limit_degrees=5.,orientation_limit_degrees=1.)
    assert review['refinement'] is None and review['retained_input'] and not review['output_support_samples_pass']
    assert sha256(output/'candidate.glb')==original==sha256(setup.source)
    assert len(review['trials'])==4
    for index,row in enumerate(review['trials']):
        assert row['joint_search']['maximum_evaluations']==160
        control=studio.served_file(row['joint_search']['controls_url'].removeprefix('/files/'))
        assert control==output/f'trial-{index}.controls.json'
        assert read(control)['proposal_sha256']==sha256(output/f'trial-{index}.glb')
    assert not review['quality_approved']


def test_frozen_joint_request_rejects_changed_budget_and_mixed_mode(setup):
    body=dict(setup.body,joint_source_rate_search=True);folder=studio.folder_for('bound-joint');studio.prepare(body,folder)
    request=read(folder/'request.json')
    for field,value in [('joint_search_evaluations',80),('joint_search_evaluations',160.),('joint_source_rate_search',1),('sampled_support_repair',True)]:
        changed=dict(request,**{field:value});save(folder/'request.json',changed)
        # Deliberately update a shallow hash: semantic frozen choices must still reject.
        binding=read(folder/'prepared.json');binding['request_sha256']=sha256(folder/'request.json');save(folder/'prepared.json',binding)
        with pytest.raises(ValueError,match='choice|budget'):studio.frozen(folder)


def test_changed_controls_or_search_freedom_cannot_be_served(setup):
    folder,output=complete(setup);control=output/'trial-0.controls.json';original=control.read_bytes()
    control.write_bytes(original+b'changed')
    with pytest.raises(ValueError):studio.manifest('joint-fixture')
    control.write_bytes(original)
    request=read(output/'request.json');request['joint_foot_orientation_limit_degrees']=2
    save(output/'request.json',request);result=read(output/'result.json');result['outputs']['request.json']=sha256(output/'request.json')
    save(output/'result.json',result);receipt=read(folder/'completion.json');receipt['result_sha256']=sha256(output/'result.json');save(folder/'completion.json',receipt)
    with pytest.raises(ValueError,match='freedom'):studio.manifest('joint-fixture')
    assert studio.served_file('native-support-jobs/joint-fixture/candidate.glb') is None
