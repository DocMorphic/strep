"""Portable cycle metadata; weighted vertices must belong to the mapped subtree."""
import shutil
import numpy as np
from pathlib import Path
from strep import ROOT,read,save,sha256
from rig_asset import RigAsset


def write(folder):
    folder=Path(folder);report=read(folder/'report.json');timeline=read(folder/'timeline.json');rig=RigAsset.load(folder/'character.glb');root=report['root_node'];p=timeline['period_frames']
    if report['frames']!=p+1:raise ValueError('Runtime cycle requires one period plus terminal sample')
    if report['glb_sha256']!=sha256(folder/'character.glb'):raise ValueError('Runtime cycle GLB changed')
    descendants=[]
    for n in range(len(rig.parents)):
        a=n
        while a>=0 and a!=root:a=rig.parents[a]
        if a==root:descendants.append(n)
    for primitive in rig.primitives:
        if primitive['joints'] is None:raise ValueError('Runtime root extraction does not support rigid mesh primitives outside the skin')
        weighted=set(rig.joints[j] for j in np.unique(primitive['joints'][primitive['weights']>0]))
        if weighted-set(descendants):raise ValueError('Weighted bones outside the mapped pelvis subtree prevent root extraction')
    names=[rig.document['nodes'][j].get('name') for j in rig.joints]
    if len(set(names))!=len(names) or any(not isinstance(n,str) for n in names):raise ValueError('Runtime adapter requires unique named skin joints')
    from rig_events import load,runtime_markers
    markers,excluded=runtime_markers(load(folder),p)
    data=dict(schema='strep-runtime-cycle-v1',fps=30,period_frames=p,glb_sha256=report['glb_sha256'],root_bone=rig.document['nodes'][root]['name'],root_node=root,descendant_nodes=descendants,cycle_transform=timeline['cycle_transform'],markers=markers,excluded_events=excluded,
        playback=dict(forward_method='advance',reverse_method='rewind',reverse_default='silent',reverse_notification_signal='marker_reversed',reverse_notifications_undo_gameplay=False,minimum_time_s=0),
        scope='Forward and explicit reverse cycle playback. Full pelvis translation and rotation extraction, not planar game movement or collision handling. Timing-confirmed authored markers dispatch; reverse notifications do not undo gameplay. Ambiguous blend markers require explicit timing review. No physical/action approval.')
    data['playback']['crossfade']=dict(adapter='godot_cycle_blend.gd',instructions='GODOT-BLENDS.md',direction='forward_and_latest_transition_reverse',reverse_method='rewind',frame_methods=['advance_frames','rewind_frames'],reverse_default='silent',reverse_notification_signal='marker_reversed',reverse_history='latest_transition_only',reverse_notifications_undo_gameplay=False,event_policies=['dominant','incoming','silent'],same_rig_required=True,contact_correction=False)
    data['playback']['object_consumer']=dict(adapter='godot_event_object_body.gd',instructions='GODOT-OBJECT-EVENTS.md',opt_in=True,bindings_automatic=False,scope='One prop and one owned cycle clock; explicit first-cycle authored attach/release; fixed physics steps; recorded silent preview resumes saved live state, not world rollback.',validated_physics_fps=60)
    save(folder/'runtime-cycle.json',data)
    shutil.copyfile(ROOT/'scripts/godot_cycle_adapter.gd',folder/'godot_cycle_adapter.gd')
    shutil.copyfile(ROOT/'scripts/godot_cycle_blend.gd',folder/'godot_cycle_blend.gd')
    shutil.copyfile(ROOT/'scripts/godot_event_object_body.gd',folder/'godot_event_object_body.gd')
    shutil.copyfile(ROOT/'integrations/godot/CYCLES.md',folder/'GODOT-CYCLES.md')
    shutil.copyfile(ROOT/'integrations/godot/BLENDS.md',folder/'GODOT-BLENDS.md')
    shutil.copyfile(ROOT/'integrations/godot/OBJECT-EVENTS.md',folder/'GODOT-OBJECT-EVENTS.md')
    return data
