"""Create a three-stage target contact review, keeping all failures visible."""
import argparse
import os
import shutil
from pathlib import Path
from strep import ROOT,read,save,sha256
from rig_asset import RigAsset
from gltf_tools import sample_animation
import numpy as np


def build(output, raw, axes):
    output,raw,axes=map(lambda p:Path(p).resolve(),(output,raw,axes))
    manifest=read(output/'manifest.json');cases=[]
    def relative(p):return os.path.relpath(p,output).replace('\\','/')
    for item in manifest['cases']:
        original=read(raw/item['id']/'report.json');calibrated=read(axes/item['id']/'report.json');audit=read(output/item['audit'])
        feasibility_file=output/item['id']/'feasibility-diagnostic.json'
        rig=RigAsset.load(output/item['path'])
        floor=[max(0.,-float(rig.vertices(sample_animation(rig.document,rig.binary,0,f))[:,1].min())) for f in range(item['frames'])]
        cases.append(dict(id=item['id'],frames=item['frames'],fps=item['fps'],root_node=original['root_node'],
            variants=dict(raw=dict(path=relative(raw/item['id']/'character.glb'),sha256=original['glb_sha256']),
                          axes=dict(path=relative(axes/item['id']/'character.glb'),sha256=calibrated['glb_sha256']),
                          fitted=dict(path=item['path'],sha256=item['sha256'])),
            raw_floor_depth_m=original['target_mesh_floor_depth_max_m'],audit=audit,audit_url=item['audit'],spec_url='specs/'+item['id']+'.json',
            worst_corrected_floor_frame=int(np.argmax(floor)),corrected_floor_depth_track_m=floor,
            feasibility=read(feasibility_file) if feasibility_file.exists() else None))
    data=dict(cases=cases,engine_verification=manifest.get('engine_verification'))
    save(output/'review.json',data)
    shutil.copyfile(ROOT/'scripts/target-contact-review.html',output/'viewer.html')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['output','raw','axes']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();build(a.output,a.raw,a.axes)
