import copy
import json
import sys
import threading
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from strep import ROOT,read,sha256
from rig_asset import RigAsset
from gltf_tools import sample_animation
from inspect_rig_contacts import inspect
from action_studio_server import Handler
from rig_contact_authoring import metadata


def test_contact_inspection_localizes_known_export_failure():
    folder=ROOT/'reports/rig-jobs/20260926-195952-76bed1e3'
    spec=read(folder/'contact-spec.json');spec['glb_sha256']=sha256(folder/'corrected/character.glb')
    data=inspect(folder/'corrected/character.glb',spec,read(folder/'transfer/report.json')['mapping'])
    peak=max(data['contacts'],key=lambda c:c['error_max_m'])
    assert peak['patch']=='Left-fore-a' and peak['worst_frame']==67
    assert peak['error_max_m']==pytest.approx(.05120773,abs=1e-6)
    assert data['worst_floor']['frame']==67 and data['floor_frames_failed']==70
    assert data['worst_floor']['skin_influences'][0]['label']=='LeftFoot'
    assert data['worst_floor']['depth_m']==pytest.approx(.02249251,abs=1e-6)


def test_single_frame_target_has_known_error_and_no_speed():
    folder=ROOT/'reports/rig-jobs/20260926-195412-bf0e8a1d'
    spec=read(folder/'contact-spec.json');glb=folder/'transfer/character.glb';rig=RigAsset.load(glb)
    point=rig.vertices(sample_animation(rig.document,rig.binary,0,4))[spec['patches']['Left-heel']['vertices']].mean(0)
    spec['contacts']=[dict(patch='Left-heel',start_frame=4,end_frame_exclusive=5,target_position_m=(point+[.03,0,0]).tolist())]
    data=inspect(glb,spec);contact=data['contacts'][0]
    assert data['failed_intervals']==1 and contact['failed_frames']==1
    assert contact['worst_frame']==4 and contact['speed_max_m_s'] is None
    assert contact['error_max_m']==pytest.approx(.03)
    assert contact['worst_error_vector_m']==pytest.approx([-.03,0,0])
    json.dumps(data,allow_nan=False)
    spec['glb_sha256']='0'*64
    with pytest.raises(ValueError,match='different mesh'):inspect(glb,spec)


def test_inspection_http_is_read_only_and_checks_origin():
    job='20260926-195412-bf0e8a1d';meta=metadata(job,'corrected')
    payload=dict(source_job=job,variant='corrected',spec=meta['spec'])
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler);host=f'127.0.0.1:{server.server_port}'
    server.allowed_hosts={host}
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    before=set((ROOT/'reports/rig-jobs').iterdir())
    try:
        for origin,status in [('https://example.com',403),('http://'+host,200)]:
            client=HTTPConnection(host);client.request('POST','/api/rig-contact-inspect',body=json.dumps(payload),headers={'Content-Type':'application/json','Origin':origin})
            response=client.getresponse();assert response.status==status;body=json.loads(response.read());client.close()
            if status==200:
                assert body['glb_sha256']==meta['glb_sha256'] and body['failed_intervals']==0
        assert set((ROOT/'reports/rig-jobs').iterdir())==before
    finally:server.shutdown();server.server_close();thread.join()
