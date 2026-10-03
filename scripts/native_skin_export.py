"""Separate weight-conditioned GLB; retain original mesh, binds and animation data."""
import argparse
import copy
import json
import struct
from pathlib import Path
import shutil
from threadpoolctl import threadpool_limits
from action_worker_lock import worker_lock
from strep import ROOT,read,save,sha256,now
from rig_asset import RigAsset
from gltf_tools import append_accessor
from skin_weight_grid import condition
from native_scene_engine import METHODS as ENGINE_METHODS

METHODS=tuple(dict.fromkeys(ENGINE_METHODS+('native_skin_export.py','skin_weight_grid.py')))


def unchanged(source, exported):
    if exported.binary[:len(source.binary)]!=source.binary:raise ValueError('Original GLB payload changed')
    doc=copy.deepcopy(exported.document)
    for key in ('accessors','bufferViews'):doc[key]=doc[key][:len(source.document[key])]
    doc['buffers'][0]['byteLength']=source.document['buffers'][0]['byteLength']
    for mesh,original in zip(doc['meshes'],source.document['meshes']):
        for primitive,old in zip(mesh['primitives'],original['primitives']):
            for key in ('WEIGHTS_0','WEIGHTS_1'):
                if key in old['attributes']:primitive['attributes'][key]=old['attributes'][key]
    if doc!=source.document:raise ValueError('Weight export changed non-weight scene data')


def write_export(path, document, binary):
    document=copy.deepcopy(document);document['buffers'][0]['byteLength']=len(binary)
    encoded=json.dumps(document,separators=(',',':'),allow_nan=False).encode('utf-8')
    encoded+=b' '*(-len(encoded)%4);payload=bytes(binary)+b'\0'*(-len(binary)%4)
    raw=struct.pack('<III',0x46546c67,2,28+len(encoded)+len(payload))
    raw+=struct.pack('<II',len(encoded),0x4E4F534A)+encoded
    raw+=struct.pack('<II',len(payload),0x004E4942)+payload;Path(path).write_bytes(raw)


def run(source_path, output):
    source_path,output=map(lambda p:Path(p).resolve(),(source_path,output))
    if output.exists():raise ValueError('Fresh weight export directory required')
    with worker_lock(),threadpool_limits(limits=1):
        source_hash=sha256(source_path);source=RigAsset.load(source_path);methods={n:sha256(ROOT/'scripts'/n) for n in METHODS}
        output.mkdir(parents=True);archive=output/'implementation';archive.mkdir()
        save(output/'pipeline.json',dict(status='processing',original_selected=True))
        try:
            shutil.copyfile(source_path,output/'original.glb')
            for n in methods:shutil.copyfile(ROOT/'scripts'/n,archive/n)
            save(output/'request.json',dict(at=now(),source_path=str(source_path),source_sha256=source_hash,implementation_sha256=methods,
                target='Godot 4.7.2 raw unsigned-16 weights',original_selected=True,quality_approved=False))
            doc=copy.deepcopy(source.document);data=bytearray(source.binary);reports=[]
            for p in source.primitives:
                values,report=condition(p['weights'])
                mesh=doc['meshes'][doc['nodes'][p['node']]['mesh']];primitive=mesh['primitives'][p['primitive']]
                for slot in range(values.shape[1]//4):
                    primitive['attributes']['WEIGHTS_'+str(slot)]=append_accessor(doc,data,values[:,4*slot:4*slot+4],'VEC4')
                reports.append(dict(node=p['node'],primitive=p['primitive'],**report))
            write_export(output/'proposal.glb',doc,data);exported=RigAsset.load(output/'proposal.glb');unchanged(source,exported)
            if sha256(source_path)!=source_hash or sha256(output/'original.glb')!=source_hash:raise ValueError('Weight export source changed')
            if any(sha256(ROOT/'scripts'/n)!=h or sha256(archive/n)!=h for n,h in methods.items()):raise ValueError('Weight export method changed')
            result=dict(status='complete',source_sha256=source_hash,proposal_sha256=sha256(output/'proposal.glb'),primitives=reports,
                original_selected=True,source_payload_prefix_preserved=True,non_weight_scene_data_preserved=True,
                mesh_weights_changed=True,animation_changed=False,engine_playback_verified=False,
                skin_fidelity_verified=False,quality_approved=False,training_admitted=False,release_approved=False)
            save(output/'result.json',result);save(output/'pipeline.json',dict(status='complete',original_selected=True));return result
        except Exception as exc:
            save(output/'pipeline.json',dict(status='failed',error=str(exc),original_selected=True));raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for n in ('source','output'):parser.add_argument(n,type=Path)
    args=parser.parse_args();run(args.source,args.output)
