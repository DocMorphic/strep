"""Screen imported-weight CPU reconstructions on the unchanged original mesh topology."""
import argparse
from pathlib import Path
import shutil
import numpy as np
from scipy.spatial.transform import Rotation
from strep import ROOT,read,save,sha256,now
from rig_asset import RigAsset,array
from rig_clip_import import AnimationSampler
from imported_skin_reconstruction import ImportedSkin
from native_finger_motion import palm_geometry
from shared_palm_meeting import measure
from triangle_crossing import audit
from convex_partner_surface import penetration


def run(gpu_study,output):
    gpu_study,output = Path(gpu_study).resolve(),Path(output).resolve()
    if output.exists() or output.parent != ROOT/'reports': raise ValueError('Fresh immediate reports folder required')
    q,result = read(gpu_study/'request.json'),read(gpu_study/'result.json')
    if result['status'] != 'complete' or not result['passed']: raise ValueError('Completed passing imported-data/GPU study required')
    files = dict(q['inputs'])
    for name,digest in result['outputs'].items():
        path = (gpu_study/name).resolve()
        if not path.is_relative_to(gpu_study): raise ValueError('Escaping evidence')
        if str(path) in files and files[str(path)] != digest: raise ValueError('Conflicting evidence')
        files[str(path)] = digest
    for name in ('request.json','result.json'): files[str(gpu_study/name)] = sha256(gpu_study/name)
    def bound(path):
        path = Path(path).resolve()
        if files.get(str(path)) != sha256(path): raise ValueError('Unbound imported skin input')
        return read(path)
    def unchanged():
        for path,digest in files.items():
            if sha256(path) != digest: raise ValueError('Changed imported-skin evidence')
    unchanged()
    engine = Path(q['engine_audit']); eq = bound(engine/'request.json'); er = bound(engine/'engine-output.json')
    intent = bound(Path(eq['study'])/'request.json')
    imported = bound(gpu_study/'engine-output.json')['cases']
    actors = []
    for i,case in enumerate(q['cases']):
        if case['id'] != imported[i]['id'] or case['id'] != er['cases'][i]['id']: raise ValueError('Participant correspondence differs')
        rig = RigAsset.load(case['path']); sampler = AnimationSampler(rig.document,rig.binary,0)
        primitive = rig.primitives[0]; names = [rig.document['nodes'][n]['name'] for n in rig.joints]
        weights = np.zeros((len(primitive['positions']),len(names)))
        for column in range(primitive['joints'].shape[1]): np.add.at(weights,(np.arange(len(weights)),primitive['joints'][:,column]),primitive['weights'][:,column])
        skin = ImportedSkin(primitive['positions'],weights,names,rig.inverse,imported[i]['surfaces'][0])
        mesh = rig.document['meshes'][rig.document['nodes'][primitive['node']]['mesh']]['primitives'][primitive['primitive']]
        faces = array(rig.document,rig.binary,mesh['indices']).reshape(-1,3)
        rotation = Rotation.from_quat(case['placement']['rotation_xyzw']).as_matrix(); translation = np.asarray(case['placement']['translation_m'])
        actors.append(dict(rig=rig,sampler=sampler,skin=skin,faces=faces,rotation=rotation,translation=translation,engine=er['cases'][i],times=eq['cases'][i]['sample_times_s']))
    output.mkdir(); archive = output/'implementation'; archive.mkdir()
    methods = {ROOT/'scripts'/name:sha256(ROOT/'scripts'/name) for name in ('diagnose_imported_native_contact.py','imported_skin_reconstruction.py','imported_skin_evidence.py','rig_asset.py','rig_clip_import.py','gltf_tools.py','strep.py','native_finger_motion.py','shared_palm_meeting.py','triangle_crossing.py','convex_partner_surface.py')}
    for path,digest in methods.items():
        target = archive/path.name; shutil.copyfile(path,target); files[str(target)] = digest
    save(output/'request.json',dict(at=now(),gpu_study=str(gpu_study),inputs=files,guard_times_s=intent['guard_times_s'],event_time_s=intent['event_time_s'],
        scope='Observed imported positions/raw quantized weights/bind matrices plus bound headless native-resource world joints. Reconstruct in original source vertex order and original source triangle topology. Float64 CPU calculation of the documented linear-weight formula; not GPU position readback, engine physics or a continuous certificate.'))
    rows,contact = [],None
    for time in intent['guard_times_s']:
        points,errors,floors = [],[],[]
        for a in actors:
            frame = a['engine']['frames'][a['times'].index(time)]
            actual = a['skin'].vertices(frame['bones'],a['engine']['bone_names'])@a['rotation'].T+a['translation']
            original = a['rig'].vertices(a['sampler'].sample(time))@a['rotation'].T+a['translation']
            points.append(actual); errors.append(float(np.linalg.norm(actual-original,axis=1).max()))
            floors.append(dict(imported_cpu_depth_m=max(0.,-float(actual[:,1].min())),original_depth_m=max(0.,-float(original[:,1].min()))))
        surface = audit(points[0],actors[0]['faces'],points[1],actors[1]['faces'])
        depths = [penetration(points[a],points[b],actors[b]['faces'],tolerance_m=1e-8) for a,b in ((0,1),(1,0))]
        passed = not any(v for k,v in surface['counts'].items() if k != 'disjoint') and not any(surface['degenerate_faces']) and max(d['max_depth_m'] for d in depths) <= 1e-8
        row = dict(time_s=time,passed=bool(passed),surface=surface,depths=depths,maximum_vertex_errors_m=errors,floor=floors)
        if time == intent['event_time_s']:
            centers,normals = [],[]
            for i,a in enumerate(actors):
                vertex = intent['selected_contact']['effector' if i == 0 else 'target']['surface_vertex']
                patch = a['faces'][np.any(a['faces'] == vertex,axis=1)]; c,n = palm_geometry(points[i],patch,vertex)
                centers.append(c); normals.append(n)
            contact = measure(centers,normals,intent['target']); row['contact'] = contact
        rows.append(row); save(output/f'geometry-{len(rows)-1:02d}.json',row)
        print(dict(completed=len(rows),total=len(intent['guard_times_s']),passed=bool(passed)),flush=True)
    if contact is None: raise ValueError('Missing authored event guard')
    unchanged()
    if any(sha256(p) != d for p,d in methods.items()): raise ValueError('Imported reconstruction method changed')
    save(output/'decoded.json',dict(contact=contact,guard_samples=len(rows),failed_geometry_samples=sum(not r['passed'] for r in rows),
        maximum_vertex_error_m=max(max(r['maximum_vertex_errors_m']) for r in rows),
        maximum_imported_floor_depth_m=max(v['imported_cpu_depth_m'] for r in rows for v in r['floor'])))
    save(output/'result.json',dict(at=now(),status='complete',contact_target_pass=contact['contact_target_pass'],
        guard_samples=len(rows),failed_geometry_samples=sum(not r['passed'] for r in rows),
        maximum_depth_m=max(d['max_depth_m'] for r in rows for d in r['depths']),
        outputs={p.relative_to(output).as_posix():sha256(p) for p in output.rglob('*') if p.is_file()},
        gpu_positions_read_back=False,original_topology=True,continuous_collision_certified=False,quality_approved=False,selected_for_studio=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('gpu_study',type=Path); parser.add_argument('output',type=Path)
    args = parser.parse_args(); run(args.gpu_study,args.output)
