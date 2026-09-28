"""Finite target-rig clock metadata; keep unsupported exports usable with a reason."""
from pathlib import Path
import shutil
import numpy as np
from strep import ROOT, read, save, sha256
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from rig_events import load, runtime_markers


def write(folder):
    folder=Path(folder)
    event_folder=folder;provenance=None
    if (folder/'report.json').exists(): report=read(folder/'report.json')
    elif (folder/'audit.json').exists() and (folder.parent/'transfer/report.json').exists():
        # Legacy finite contact candidates store geometry in corrected/ and
        # shared timing/rig metadata in transfer/. Bind both hashes explicitly.
        event_folder=folder.parent/'transfer';original=read(event_folder/'report.json');audit=read(folder/'audit.json')
        if audit.get('source_glb_sha256')!=original['glb_sha256'] or sha256(event_folder/'character.glb')!=original['glb_sha256'] or audit.get('frames')!=original['frames'] or audit.get('fps')!=original['fps']:
            raise ValueError('Corrected clip does not match source timing/geometry provenance')
        report={k:original[k] for k in ('frames','fps','root_node')}
        report['glb_sha256']=audit['glb_sha256']
        provenance=dict(source_glb_sha256=original['glb_sha256'],correction_audit_sha256=sha256(folder/'audit.json'),scope='Unchanged timing from explicitly hash-bound source. Correction status and human approval are not changed.')
    else: raise ValueError('Finite runtime requires a clip report or a hash-bound corrected-source audit')
    frames=report['frames'];root=report['root_node']
    if type(frames) is not int or not 2<=frames<=900 or report['fps']!=30: raise ValueError('Finite runtime supports 2-900 samples at 30 fps')
    if sha256(folder/'character.glb')!=report['glb_sha256']: raise ValueError('Finite runtime GLB changed')
    rig=RigAsset.load(folder/'character.glb')
    if type(root) is not int or root not in rig.joints: raise ValueError('Root must identify a skin joint')
    if len(rig.document.get('animations',[]))!=1: raise ValueError('Finite runtime requires one sampled animation')
    sampler=AnimationSampler(rig.document,rig.binary,0)
    if abs(sampler.duration-(frames-1)/30)>1e-5: raise ValueError('Finite runtime sample count does not match animation endpoint')
    descendants=[]
    for node in range(len(rig.parents)):
        parent=node
        while parent>=0 and parent!=root: parent=rig.parents[parent]
        if parent==root: descendants.append(node)
    for primitive in rig.primitives:
        if primitive['joints'] is None: raise ValueError('Root extraction requires skinned primitives')
        weighted={rig.joints[j] for j in np.unique(primitive['joints'][primitive['weights']>0])}
        if weighted-set(descendants): raise ValueError('Weighted bones outside mapped root prevent extraction')
    names=[rig.document['nodes'][j].get('name') for j in rig.joints]
    if any(not isinstance(n,str) for n in names) or len(set(names))!=len(names): raise ValueError('Unique named skin joints required')
    eligible,excluded=runtime_markers(load(event_folder),frames)
    markers=[e for e in eligible if 'event_id' in e]
    data=dict(schema='strep-runtime-finite-v1',frames=frames,fps=30,last_sample_time_s=(frames-1)/30,duration_s=frames/30,glb_sha256=report['glb_sha256'],root_bone=rig.document['nodes'][root]['name'],root_node=root,descendant_nodes=descendants,markers=markers,excluded_events=excluded,
        playback=dict(adapter='godot_finite_adapter.gd',instructions='GODOT-FINITE.md',terminal_pose='hold',events_repeat=False,simulation_clock_continues=True,reverse_notifications_undo_gameplay=False,object_consumer='godot_event_object_body.gd',object_instructions='GODOT-OBJECT-EVENTS.md',bindings_automatic=False),scope='Finite sampled target-rig clip and explicit authored intent. Pose holds after final sample; physical simulation clock continues. No automatic bindings or motion quality approval.')
    if provenance is not None: data['correction_source']=provenance
    save(folder/'runtime-finite.json',data)
    for name in ('godot_finite_adapter.gd','godot_cycle_adapter.gd','godot_event_object_body.gd'): shutil.copyfile(ROOT/'scripts'/name,folder/name)
    for name,target in [('FINITE.md','GODOT-FINITE.md'),('OBJECT-EVENTS.md','GODOT-OBJECT-EVENTS.md')]: shutil.copyfile(ROOT/'integrations/godot'/name,folder/target)
    return data
