"""Independent surface/contact audits for independently generated scene actors."""
import argparse
import time
from pathlib import Path
import numpy as np
from strep import ROOT,read,save,sha256,now
from audit_partner_surface import audit as partner_audit
from audit_body_ground import measure as ground_audit
from audit_generation_guides import audit as guide_audit
from generation_constraints import compile_guides
from build_soma_preview import ASSET


def run(folder):
    folder=Path(folder);manifest=read(folder/'manifest.json');freeze=read(folder/'freeze.json')
    plan=read(folder/'actor-plan.json');batch=read(folder/'request.json');skin=dict(np.load(ASSET));rows=[]
    guide_targets={}
    for i,name in enumerate(freeze['actor_order']):
        guide_targets[name]=compile_guides(next(r for r in batch['requests'] if r['id']==f'actor-{i}-guided'))[0]
    for item in manifest['scenes']:
        path=folder/item['variants']['palm'];bundle=read(path);scene=bundle['scene'];started=time.perf_counter()
        print('Auditing '+scene['id'],flush=True)
        for name,entry in scene['actors'].items():
            if sha256(ROOT/entry['motion'])!=entry['source_sha256']:raise ValueError('Generated scene source changed')
        destination=path.parent/'partner-surface-audit.json'
        if destination.exists():
            partner=read(destination)
            if partner['scene_sha256']!=sha256(path) or partner['auditor_sha256']!=sha256(ROOT/'scripts/audit_partner_surface.py'):
                raise ValueError('Audit resume mismatch')
        else:
            partner=partner_audit(scene,skin)
            partner.update(created_at=now(),seconds=time.perf_counter()-started,scene_sha256=sha256(path),auditor_sha256=sha256(ROOT/'scripts/audit_partner_surface.py'))
            save(destination,partner)
        actors={}
        for name,entry in scene['actors'].items():
            motion=dict(np.load(ROOT/entry['motion'],allow_pickle=False))
            actors[name]=dict(conditioning=guide_audit(motion,guide_targets[name]),ground=ground_audit(motion,skin))
        orientation=read(folder/item['orientation_file']);contact=bundle['evaluation']
        flags=[]
        if any(not c['all_requested_frames_within_tolerance'] for c in contact['contacts']):flags.append('requested_surface_contact_missed')
        if any(c['frames_over_tolerance'] or c.get('tangent_frames_over_tolerance',0) for c in orientation['contacts']):flags.append('hand_orientation_failed')
        if any(p['frames_over_tolerance'] for p in partner['pairs']):flags.append('partner_skin_penetration_above_5mm')
        if any(a['ground']['frames_over_1cm'] for a in actors.values()):flags.append('skin_floor_penetration_above_1cm')
        if any(not a['conditioning']['numerical_screen_passed'] for a in actors.values()):flags.append('generation_pose_target_failed')
        if any(c['frames_over_1cm'] for c in contact['object_collisions']):flags.append('object_skin_penetration_above_1cm')
        row=dict(scene_id=scene['id'],contacts=contact['contacts'],orientation=orientation['contacts'],partner=partner['pairs'],actors=actors,
            flags=flags,release_approved=False,scene_sha256=sha256(path))
        save(path.parent/'quality-audit.json',row);rows.append(row)
        item['partner_file']=destination.relative_to(folder).as_posix()
        item['quality_file']=(path.parent/'quality-audit.json').relative_to(folder).as_posix()
        save(folder/'manifest.json',manifest)
        print(dict(scene=scene['id'],point_errors=[c['max_interval_error_m'] for c in contact['contacts']],
            partner_depths=[p['max_depth_m'] for p in partner['pairs']],flags=flags),flush=True)
        save(folder/'scene-quality-audit.json',dict(status='processing',scenes=rows))
    save(folder/'scene-quality-audit.json',dict(status='complete',created_at=now(),scenes=rows,release_approved=False,
        method_sha256=sha256(__file__),scope='Actual skinned contact/orientation, all-frame floor and bidirectional partner vertex tests. Independent actor samples; not joint model, continuous collision, force/contact dynamics or human quality approval.'))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('folder',type=Path);run(parser.parse_args().folder)
