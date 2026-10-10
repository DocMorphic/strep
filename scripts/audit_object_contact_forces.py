"""Immutable conditional force assessment of a sampled rigid-object track.

Explicit local contact schedules, masses, friction/capacity and support phases
are required. Unknown phases and cross-phase derivative stencils are retained
but unassessed. This does not establish actual hand contact or human balance.
"""
import argparse,json,shutil
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from contact_force_balance import solve,validate as validate_contact
from object_dynamics import diagnose,uniform_box_inertia
from strep import ROOT,read,save,sha256,now

SCHEMA='strep-object-contact-force-spec-v1'
METHODS=('audit_object_contact_forces.py','contact_force_balance.py','object_dynamics.py','strep.py')
SPEC_FIELDS={'schema','masses_kg','gravity_m_s2','phases','contacts','assumption_notes','force_tolerance_N','torque_tolerance_Nm','seconds_per_sample'}
CONTACT_FIELDS={'id','point_from_com_local_m','normal_into_body_local','friction_coefficient','max_force_N','start_frame','end_frame_exclusive'}


def validate(track,spec):
    if not isinstance(spec,dict) or set(spec)!=SPEC_FIELDS or spec['schema']!=SCHEMA:
        raise ValueError('Complete explicit object contact-force specification required')
    if not isinstance(track,dict) or track.get('space') not in ('world','World metres, Y-up'):raise ValueError('World-space COM track required')
    frames=len(track['positions_m']);fps=track['fps']
    if not 3<=frames<=900 or type(fps) not in (int,float) or not np.isfinite(fps) or not 1<=fps<=240:
        raise ValueError('Bounded complete sample clock required')
    masses=spec['masses_kg']
    if (not isinstance(masses,list) or not 1<=len(masses)<=4
            or any(type(m) not in (int,float) or not np.isfinite(m) or not 0<m<=1e6 for m in masses)
            or len(set(masses))!=len(masses)):
        raise ValueError('One to four distinct explicit masses required')
    notes=spec['assumption_notes']
    if (not isinstance(notes,dict) or set(notes)!={'com','mass','inertia','friction','capacity','contacts'}
            or any(not isinstance(v,str) or not 1<=len(v)<=2000 for v in notes.values())):
        raise ValueError('Explicit COM/mass/inertia/friction/capacity/contact provenance required')
    contacts=spec['contacts']
    if not isinstance(contacts,list) or len(contacts)>16:raise ValueError('Bounded explicit contact schedule required')
    parsed=[]
    for c in contacts:
        if not isinstance(c,dict) or set(c)!=CONTACT_FIELDS:raise ValueError('Complete local contact schedule required')
        a,b=c['start_frame'],c['end_frame_exclusive']
        if type(a) is not int or type(b) is not int or not 0<=a<b<=frames:raise ValueError('Bounded contact interval required')
        parsed.append(dict(id=c['id'],lever_from_com_world_m=c['point_from_com_local_m'],normal_into_body_world=c['normal_into_body_local'],
            friction_coefficient=c['friction_coefficient'],max_force_N=c['max_force_N']))
    validate_contact([0,0,0],[0,0,0],parsed,spec['force_tolerance_N'],spec['torque_tolerance_Nm'])
    if type(spec['seconds_per_sample']) not in (int,float) or not np.isfinite(spec['seconds_per_sample']) or not .01<=spec['seconds_per_sample']<=2:
        raise ValueError('Explicit bounded per-sample budget required')
    # Diagnose validates complete positions/quaternions/inertia/gravity/phases.
    diagnose(track['positions_m'],track['rotations_xyzw'],fps=fps,mass_kg=masses[0],
        inertia_body_kg_m2=uniform_box_inertia(masses[0],track['size_m']),gravity_m_s2=spec['gravity_m_s2'],phases=spec['phases'])
    for c in contacts:
        for phase in spec['phases']:
            if phase['support_assumption']=='free_flight' and max(c['start_frame'],phase['start_frame'])<min(c['end_frame_exclusive'],phase['end_frame_exclusive']):
                raise ValueError('Declared free flight cannot have active support contacts')
    return frames


def assess(track,spec,mass):
    frames=validate(track,spec)
    if mass not in spec['masses_kg']:raise ValueError('Predeclared mass required')
    demand=diagnose(track['positions_m'],track['rotations_xyzw'],fps=track['fps'],mass_kg=mass,
        inertia_body_kg_m2=uniform_box_inertia(mass,track['size_m']),gravity_m_s2=spec['gravity_m_s2'],phases=spec['phases'])
    rotations=Rotation.from_quat(track['rotations_xyzw']).as_matrix();labels=[None]*frames
    for phase in spec['phases']:
        for i in range(phase['start_frame'],phase['end_frame_exclusive']):labels[i]=phase['support_assumption']
    rows=[];unassessed=[]
    for frame,same,force,torque in zip(demand['sample_frames'],demand['same_phase_stencil'],demand['required_non_gravity_force_world_N'],demand['required_torque_about_com_world_Nm']):
        if not same or labels[frame]=='unknown':
            unassessed.append(dict(frame=frame,reason='cross_phase_stencil' if not same else 'unknown_support'))
            continue
        active=[]
        for c in spec['contacts']:
            if c['start_frame']<=frame<c['end_frame_exclusive']:
                if labels[frame]=='free_flight':raise ValueError('Declared free flight cannot have active support contacts')
                active.append(dict(id=c['id'],lever_from_com_world_m=(rotations[frame]@np.array(c['point_from_com_local_m'])).tolist(),
                    normal_into_body_world=(rotations[frame]@np.array(c['normal_into_body_local'])).tolist(),friction_coefficient=c['friction_coefficient'],max_force_N=c['max_force_N']))
        report=solve(force,torque,active,force_tolerance_N=spec['force_tolerance_N'],torque_tolerance_Nm=spec['torque_tolerance_Nm'],seconds=spec['seconds_per_sample'])
        rows.append(dict(frame=frame,assessment=report))
    return dict(mass_kg=mass,demand=demand,assessed_samples=rows,unassessed_samples=unassessed,
        unestimated_endpoint_frames=[0,frames-1],assumption_notes=spec['assumption_notes'],quality_approved=False,release_approved=False,
        scope='Original sampled rigid-object COM trajectory, uniform solid-box inertia and declared contact model only. No actual geometry/hand forces, actor response, articulated dynamics, impact or overall animation certificate.')


def run(track_path,spec_path,output):
    track_path=Path(track_path).resolve();spec_path=Path(spec_path).resolve();output=Path(output).resolve()
    if output.exists():raise FileExistsError(output)
    if (not output.is_relative_to(ROOT/'reports') or output==ROOT/'reports'
            or any(output.is_relative_to(p) or p.is_relative_to(output) for p in (track_path,spec_path))):
        raise ValueError('Fresh ignored output separate from immutable inputs required')
    bindings={str(track_path):sha256(track_path),str(spec_path):sha256(spec_path)}
    track=read(track_path);spec=read(spec_path);validate(track,spec)
    output.mkdir(parents=True);inputs=output/'inputs';inputs.mkdir();methods=output/'implementation';methods.mkdir()
    for source,name in ((track_path,'object-track.json'),(spec_path,'force-spec.json')):
        shutil.copyfile(source,inputs/name)
        if sha256(inputs/name)!=bindings[str(source)]:raise ValueError('Source changed while freezing')
    track=read(inputs/'object-track.json');spec=read(inputs/'force-spec.json');validate(track,spec)
    for name in METHODS:shutil.copyfile(Path(__file__).resolve().parent/name,methods/name)
    protocol=dict(schema='strep-object-contact-force-study-v1',at=now(),input_sources_sha256=bindings,
        inputs_sha256={p.name:sha256(p) for p in inputs.iterdir()},methods_sha256={p.name:sha256(p) for p in methods.iterdir()},
        masses_kg=spec['masses_kg'],quality_approved=False,release_approved=False)
    save(output/'protocol.json',protocol);rows=[]
    try:
        for index,mass in enumerate(spec['masses_kg']):
            report=assess(track,spec,mass);name=f'case-{index+1}-mass-{mass:.17g}kg.json';save(output/name,report)
            counts={}
            for item in report['assessed_samples']:
                status=item['assessment']['status'];counts[status]=counts.get(status,0)+1
            rows.append(dict(mass_kg=mass,file=name,sha256=sha256(output/name),assessed=len(report['assessed_samples']),
                conditional_feasible=sum(r['assessment']['conditional_force_balance_passed'] for r in report['assessed_samples']),statuses=counts,
                unassessed=len(report['unassessed_samples']),unestimated_endpoint_frames=report['unestimated_endpoint_frames']))
        if any(sha256(Path(p))!=h for p,h in bindings.items()):raise ValueError('Source inputs changed')
        if any(sha256(methods/n)!=h or sha256(Path(__file__).resolve().parent/n)!=h for n,h in protocol['methods_sha256'].items()):raise ValueError('Bound methods changed')
        if any(sha256(inputs/n)!=h for n,h in protocol['inputs_sha256'].items()):raise ValueError('Frozen inputs changed')
        result=dict(status='complete',protocol_sha256=sha256(output/'protocol.json'),cases=rows,quality_approved=False,release_approved=False,
            scope='Conditional sampled point-contact force-model assessment; never actual grasp, strength, whole-body dynamics, engine, held-out or human-quality approval.')
        save(output/'result.json',result);save(output/'pipeline.json',dict(status='complete',result_sha256=sha256(output/'result.json'),quality_approved=False,release_approved=False));return result
    except BaseException as exc:
        save(output/'pipeline.json',dict(status='failed',error_type=type(exc).__name__,error=str(exc),quality_approved=False,release_approved=False));raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('track',type=Path);parser.add_argument('spec',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args()
    from action_worker_lock import worker_lock
    from threadpoolctl import threadpool_limits
    with worker_lock(),threadpool_limits(limits=2):print(json.dumps(run(args.track,args.spec,args.output)))
