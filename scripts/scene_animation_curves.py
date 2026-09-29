"""Hash-bound authored TRS curves for imports with nonuniform key clocks."""
from pathlib import Path
import numpy as np
from gltf_tools import read_glb
from rig_clip_import import AnimationSampler
from strep import save,sha256


def write(path,output):
    path,output=Path(path),Path(output)
    doc,binary=read_glb(path)
    if len(doc.get('animations',[]))!=1:raise ValueError('One animation required')
    sampler=AnimationSampler(doc,binary,0)
    names=[node.get('name') for node in doc['nodes']]
    bones={j for skin in doc.get('skins',[]) for j in skin['joints']}
    channels=[]
    for node,prop,times,values,mode in sampler.channels:
        name=names[node]
        if not isinstance(name,str) or not name or names.count(name)!=1:
            raise ValueError('Unique named animated nodes required for exact scene import')
        if mode not in ['LINEAR','STEP']:
            raise ValueError('Exact scene import currently supports LINEAR and STEP curves')
        if not np.isfinite(values).all():raise ValueError('Nonfinite authored curve')
        channels.append(dict(node_name=name,target_kind='bone' if node in bones else 'node',
                             path=prop,interpolation=mode,times_s=times.tolist(),values=values.tolist()))
    save(output,dict(schema='strep-animation-curves-v1',source_sha256=sha256(path),
                     duration_s=sampler.duration,channels=channels))
