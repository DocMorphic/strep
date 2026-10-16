"""One bounded current-point restoration with immutable original source bounds."""
import argparse,copy,gc,shutil
from pathlib import Path
import numpy as np
import trimesh
from scipy import sparse
from threadpoolctl import threadpool_limits
from action_worker_lock import worker_lock
from native_interval_pair_fit_job import inputs,position_rows
from native_key_interval_model import KeyIntervalModel
from native_pair_key_guides import PairKeyGuides
from native_scene_contacts import SceneContacts,fields
from native_scene_norms import NormRows
from native_scene_conic import direction,solver_identity
from native_partner_surface_rows import build
from native_surface_key_jacobian import linearize as surface_linearize
from native_surface_lift import lift
from strep import ROOT,read,save,sha256,now

SCHEMA='strep-native-interval-pair-restore-v1'


def bind(path,output):
    path=Path(path).resolve();output=Path(output).resolve();r=read(path)
    fields(r,('schema','source_recipe','reference','current_contacts','value','trust','difference_step','rate_headroom','maximum_nonzeros'),'paired restoration recipe')
    if r['schema']!=SCHEMA or output.exists():raise ValueError('Explicit restoration schema and fresh output required')
    pins={str(path):sha256(path)};roles={}
    for role in ('source_recipe','reference','current_contacts'):
        v=r[role];fields(v,('path','sha256'),'pinned '+role)
        if type(v['path']) is not str or not v['path'] or type(v['sha256']) is not str or len(v['sha256'])!=64 or any(c not in '0123456789abcdef' for c in v['sha256']):raise ValueError('Explicit pinned path and lowercase SHA256 required')
        p=(path.parent/v['path']).resolve()
        if not p.is_file() or sha256(p)!=v['sha256']:raise ValueError('Restoration input changed')
        roles[role]=p;pins[str(p)]=v['sha256']
    source,cp,gp,actors,original_pins=inputs(roles['source_recipe'],output);pins.update(original_pins)
    for p in pins:
        target=Path(p)
        if target.is_relative_to(output) or any((a/'result.json').is_file() and output.is_relative_to(a) for a in target.parents):raise ValueError('Restoration must stay outside all immutable input populations')
    for key,lo,hi in [('trust',1e-6,1.),('difference_step',1e-6,.01),('rate_headroom',0.,.01)]:
        v=r[key]
        if type(v) not in (int,float) or not np.isfinite(v) or not lo<=v<=hi:raise ValueError('Invalid bounded '+key)
    if type(r['maximum_nonzeros']) is not int or not 1<=r['maximum_nonzeros']<=6000000:raise ValueError('Complete sparse budget up to six million required')
    if (not isinstance(r['value'],list) or not r['value'] or any(type(x) not in (int,float) or not np.isfinite(x) or abs(x)>1 for x in r['value'])):raise ValueError('Complete finite original-box control point required')
    width=0
    for name,actor in actors.items():
        declaration=read(actor['request'])
        if declaration['actor']!=name:raise ValueError('Actor declarations differ from original recipe IDs')
        width+=len(actor['active_keys'])*len(declaration['rotations'])*3
    if len(r['value'])!=width or width>768:raise ValueError('Complete original control layout within 768 components required')
    return r,source,cp,gp,actors,roles,pins


def reference(pair,path):
    native,contact=pair.norms(pair.initial,pair.source_worlds)
    with np.load(path,allow_pickle=False) as z:
        values=dict(controls=pair.initial,times_s=pair.times,native_vectors=native.vectors,native_caps=native.caps,native_scales=native.scales,contact_vectors=contact.vectors,contact_caps=contact.caps,contact_scales=contact.scales,protected_contact_caps=pair.protected_contact_caps,**{f'source_floor_{n}':pair.source_floor[n] for n in pair.names})
        if any(k not in z or not np.array_equal(v,z[k]) for k,v in values.items()):raise ValueError('Original source reference vectors/caps/scales/floors differ')
    return len(native.caps)


def current(pair,value,cp,base):
    spec=read(cp);source=copy.deepcopy(pair.models[pair.names[0]].spec);canonical=copy.deepcopy(spec)
    if set(spec['actors'])!=set(pair.names):raise ValueError('Current actors differ from original source')
    scene=SceneContacts(spec,base);worlds={}
    for i,name in enumerate(pair.names):
        actor=scene.actors[name];m=pair.models[name];rig=actor['rig']
        changing={'animations','accessors','bufferViews','buffers'}
        if {k:v for k,v in rig.document.items() if k not in changing}!={k:v for k,v in m.rig.document.items() if k not in changing}:raise ValueError('Current static rig metadata changed')
        for key in ('nodes','meshes','skins'):
            if rig.document[key]!=m.rig.document[key]:raise ValueError('Current rig or canonical topology changed')
        for key in ('accessors','bufferViews'):
            if rig.document[key][:len(m.rig.document[key])]!=m.rig.document[key]:raise ValueError('Original accessor prefix changed')
        if rig.binary[:len(m.rig.binary)]!=m.rig.binary:raise ValueError('Original rig bytes changed')
        expected={(c[0],c[1]):c for c in m.actor['sampler'].channels};observed={(c[0],c[1]):c for c in actor['sampler'].channels}
        if len(expected)!=len(m.actor['sampler'].channels) or len(observed)!=len(actor['sampler'].channels) or set(expected)!=set(observed):raise ValueError('Current native channel population changed')
        quats=dict(zip(m.nodes,m.quaternions(value[pair.offsets[i]:pair.offsets[i+1]],quantized=True)))
        for key,a in expected.items():
            b=observed[key];target=quats[key[0]] if key[1]=='rotation' and key[0] in quats else a[3]
            if a[4]!=b[4] or not np.array_equal(a[2],b[2]) or not np.array_equal(target,b[3]):raise ValueError('Current clip does not match declared original-layout controls')
        worlds[name]=np.array([actor['sampler'].sample(float(t)) for t in pair.times])
        canonical['actors'][name].update({k:source['actors'][name][k] for k in ('glb','sha256','animation_index')})
    if canonical!=source:raise ValueError('Current contacts, placements or scene differ from original contract')
    scene.check_inputs();return scene,worlds


def run(recipe_path,output):
    output=Path(output).resolve();r,source,cp,gp,actors,roles,pins=bind(recipe_path,output)
    with worker_lock(),threadpool_limits(limits=1):
        output.mkdir(parents=True);archive=output/'implementation';archive.mkdir();methods={p.name:sha256(p) for p in (ROOT/'scripts').glob('*.py')}
        for n in methods:shutil.copyfile(ROOT/'scripts'/n,archive/n)
        save(output/'restore-recipe.json',r);save(output/'recipe.json',source);models={};layouts={}
        def phase(label,**data):
            save(output/'pipeline.json',dict(status='processing',phase=label,at=now(),**data));print(dict(phase=label,**data),flush=True)
        try:
            for name,a in actors.items():
                phase('original-source-model',actor=name);paths=dict(contacts=cp,geometry=gp,request=a['request'],controls=a['controls'])
                m=KeyIntervalModel.from_inputs(**paths,active_keys=a['active_keys'],output=output/name/'source-seed',expected_sha256={k:pins[str(p)] for k,p in paths.items()});models[name]=m;pins.update(m.pins);layouts[name]=dict(nodes=m.nodes,degrees=m.degrees,active_keys=a['active_keys'])
            pair=PairKeyGuides(models,[],fit_contacts=True);n=reference(pair,roles['reference']);value=pair.controls(r['value'])
            shutil.copyfile(roles['reference'],output/'start-observations.npz');save(output/'layouts.json',layouts);save(output/'actor-order.json',dict(actors=pair.names,offsets=pair.offsets.tolist()))
            phase('current-decoded-observations');scene,worlds=current(pair,value,roles['current_contacts'],cp.parent);pins.update(scene.inputs);del scene
            native,contact=pair.norms(value,worlds);before=int((native.residual()>0).sum());contacts_before=bool(np.all(contact.residual()<=0))
            np.savez_compressed(output/'current-observations.npz',controls=value,native_vectors=native.vectors,native_caps=native.caps,native_scales=native.scales,contact_vectors=contact.vectors,contact_caps=contact.caps)
            save(output/'source-reference.json',dict(original_source_reference_exact=True,native_rows=n,failed_current_native_rows=before,authored_current_contacts_pass=contacts_before,original_selected=True,quality_approved=False,release_approved=False))
            save(output/'request.json',dict(schema=SCHEMA,inputs_sha256=pins,implementation_sha256=methods,solver=solver_identity(),controls=pair.size,geometry_sample_indices=source['surface_samples'],original_source_epoch=True,linearization_at_current=True,original_selected=True,quality_approved=False,release_approved=False))
            candidate_path=None;info=dict(status='NoNativeMotionRestorationNeeded');affine_pass=None;point=value.copy();decoded_contacts=None
            if before or not contacts_before:
                def vertices(name,time):
                    index=int(np.searchsorted(pair.times,time))
                    if index>=len(pair.times) or pair.times[index]!=time:raise ValueError('Exact complete-clock current surface time required')
                    p,q=models[name].actor['placement'];return models[name].rig.vertices(worlds[name][index])@q.T+p
                phase('current-surface-witnesses');random=trimesh.util.random_generator();state=copy.deepcopy(random.bit_generator.state)
                try:
                    seeded=np.random.default_rng(source['surface_seed'])
                    if type(random.bit_generator) is not type(seeded.bit_generator):raise ValueError('Compatible seeded geometry generator required')
                    random.bit_generator.state=copy.deepcopy(seeded.bit_generator.state);save(output/'surface-rng-before.json',random.bit_generator.state)
                    surface=build(pair.scene,models[pair.names[0]].policy,sha256(cp),maximum_rows=100000,sample_indices=source['surface_samples'],actor_vertices=vertices,include_world_planes=False)
                finally:
                    save(output/'surface-rng-after.json',random.bit_generator.state);random.bit_generator.state=state
                gaps=surface.gaps(vertices);smooth,gjac,gmeta=surface_linearize(surface,layouts,value=value,maximum_nonzeros=r['maximum_nonzeros'])
                save(output/'surface-rows.json',surface.rows);save(output/'surface-report.json',surface.report);save(output/'surface-linearization.json',dict(**gmeta,maximum_measured_smooth_gap_difference_m=float(abs(gaps-smooth).max()) if len(gaps) else 0.))
                np.savez_compressed(output/'surface-gaps.npz',actual_gaps_m=gaps,continuous_gaps_m=smooth);sparse.save_npz(output/'surface-jacobian.npz',gjac)
                del surface,native,contact;gc.collect();phase('current-native-linearization',controls=pair.size)
                system,jac,identity=pair.linearize(value,worlds,r['trust'],step=r['difference_step'],maximum_nonzeros=r['maximum_nonzeros']);hard=identity['hard_rows'];c=identity['contact_rows']
                del worlds,vertices;gc.collect()
                accepted_caps=system.caps.copy();accepted_caps[n:n+c]=pair.contact_caps;system.caps[n:n+c]=pair.contact_caps
                system.caps[n+position_rows(pair)]-=source['contact_reserve_m']
                if np.any(system.caps[n+position_rows(pair)]<=0):raise ValueError('Position reserve consumes authored tolerance')
                response=np.diff(jac[:3*n].tocsr().indptr).reshape(n,3).sum(1)>0
                reserve=np.minimum(r['rate_headroom']*system.scales[:n],.01*system.caps[:n]);reserve[~response]=0.;system.caps[:n]-=reserve
                np.savez_compressed(output/'search-reserves.npz',native_reserve=reserve,original_native_caps=accepted_caps[:n])
                if len(gaps):
                    extra,ejac,conversion=lift(gaps,gjac,value,pair.lower,pair.upper,r['trust']);system=NormRows(np.r_[system.vectors,extra.vectors],np.r_[system.caps,extra.caps],np.r_[system.scales,extra.scales]);jac=sparse.vstack([jac,ejac],format='csc');save(output/'surface-lift.json',conversion);del extra,ejac
                if jac.nnz>r['maximum_nonzeros']:raise ValueError('Complete current-point matrix exceeds sparse budget; no subset returned')
                save(output/'linearization.json',dict(**identity,total_rows=len(system.caps),combined_nonzeros=jac.nnz,surface_rows=len(gaps),rate_headroom=r['rate_headroom'],search_stricter_than_original=True))
                np.savez_compressed(output/'affine-observations.npz',vectors=system.vectors,caps=system.caps,scales=system.scales);sparse.save_npz(output/'jacobian.npz',jac)
                del gjac;gc.collect();phase('bounded-current-solve',rows=len(system.caps),nonzeros=jac.nnz)
                step,info=direction(system,jac,value,pair.lower,pair.upper,r['trust'],hard_rows=hard);save(output/'solver.json',info)
                if step is not None:
                    residual=system.residual(jac,step);point=value+step;np.savez_compressed(output/'proposed-direction.npz',controls=point,step=step,affine_residual=residual);affine_pass=bool(np.all(residual[:hard]<=1e-8))
                    save(output/'affine-postcheck.json',dict(passed=affine_pass,hard_rows=hard,failed_rows=int((residual[:hard]>1e-8).sum()),maximum_normalized_excess=float(residual[:hard].max()),comparison=1e-8))
                del system,jac;gc.collect()
                if affine_pass:
                    phase('export-candidate');folder=output/'probe-00';folder.mkdir();candidate=copy.deepcopy(read(cp))
                    for i,name in enumerate(pair.names):
                        path=folder/f'{name}.glb';index=models[name].export(point[pair.offsets[i]:pair.offsets[i+1]],path);candidate['actors'][name].update(glb=str(path),sha256=sha256(path),animation_index=index)
                    candidate_path=folder/'contacts.json';save(candidate_path,candidate);np.savez_compressed(output/'direction.npz',delta=point);np.savez_compressed(output/'controls.npz',controls=point,step=step)
                    result_scene=SceneContacts(candidate,cp.parent);decoded_contacts,arrays=result_scene.evaluate();save(folder/'contacts-audit.json',decoded_contacts);np.savez_compressed(folder/'contact-observations.npz',**arrays);result_scene.check_inputs()
            pair.check()
            if any(sha256(p)!=h for p,h in pins.items()) or methods!={p.name:sha256(p) for p in (ROOT/'scripts').glob('*.py')}:raise ValueError('Original input or implementation changed')
            result=dict(schema=SCHEMA,status='complete',solver_status=info['status'],controls=pair.size,original_source_reference_exact=True,original_native_failures_before=before,affine_pass=affine_pass,candidate_contacts=str(candidate_path) if candidate_path else None,selected_controls=point.tolist(),direction_array_semantics='absolute original-source controls; local step stored separately',decoded_authored_contacts_pass=None if decoded_contacts is None else decoded_contacts['passed'],decoded_native_floor_geometry_pending=candidate_path is not None,original_selected=True,quality_approved=False,training_admitted=False,release_approved=False,scope='One bounded current-point restoration. Original source reference and actual acceptance caps unchanged; responsive search caps may tighten with declared dimensionless headroom. Full decoded motion/floor/contact/geometry and engine/semantic/human checks remain required.')
            save(output/'result.json',result);save(output/'pipeline.json',dict(status='complete',phase='complete',at=now()));return result
        except Exception as exc:
            save(output/'pipeline.json',dict(status='failed',phase='failed',error=str(exc),at=now(),original_selected=True,quality_approved=False,release_approved=False));raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('recipe',type=Path);parser.add_argument('output',type=Path);args=parser.parse_args();run(args.recipe,args.output)
