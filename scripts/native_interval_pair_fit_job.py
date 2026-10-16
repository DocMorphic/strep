"""Recipe-driven source-zero paired native contact/surface proposals.

Never selects an animation. Exported candidates require separate full decoded
native, contact, floor and geometry validation; all release flags remain false.
"""
import argparse,copy,gc,shutil
from pathlib import Path
import numpy as np
import trimesh
from scipy import sparse
from threadpoolctl import threadpool_limits
from action_worker_lock import worker_lock
from native_key_interval_model import KeyIntervalModel
from native_pair_key_guides import PairKeyGuides
from native_partner_surface_rows import build
from native_surface_key_jacobian import linearize as surface_linearize
from native_surface_lift import lift
from native_scene_conic import direction,solver_identity
from native_scene_norms import NormRows
from native_scene_contacts import SceneContacts,fields
from strep import ROOT,read,save,sha256,now

SCHEMA='strep-native-interval-pair-fit-v1'


def position_rows(pair):
    """Distance reserves apply to position norms, never relative-speed norms."""
    cursor=0;selected=[]
    for data in pair.models[pair.names[0]].contact_rows:
        row=data['entry']['authored'];points=1 if row['reduction']=='centroid' else len(data['entry']['ids'])
        count=len(data['times'])*points;selected.extend(range(cursor,cursor+count));cursor+=count
        for pop in data['populations']:cursor+=1 if len(pop['times_s'])<2 else (len(pop['times_s'])-1)*points
    if cursor!=len(pair.contact_caps):raise ValueError('Complete coupled contact norm layout differs')
    return np.asarray(selected,int)


def inputs(path,output):
    path=Path(path).resolve();output=Path(output).resolve();request=read(path)
    fields(request,('schema','contacts','geometry','actors','surface_samples','surface_seed','trust','difference_step','contact_reserve_m','maximum_nonzeros'),'paired interval recipe')
    if request['schema']!=SCHEMA or output.exists():raise ValueError('Explicit schema and fresh separate output required')
    pins={str(path):sha256(path)}
    def pinned(value):
        fields(value,('path','sha256'),'pinned input')
        if (type(value['path']) is not str or not value['path'] or type(value['sha256']) is not str
                or len(value['sha256'])!=64 or any(c not in '0123456789abcdef' for c in value['sha256'])):
            raise ValueError('Explicit path and lowercase SHA256 required')
        target=(path.parent/value['path']).resolve()
        if not target.is_file() or sha256(target)!=value['sha256']:raise ValueError('Pinned source input changed')
        if target.is_relative_to(output) or ((target.parent/'result.json').exists() and output.is_relative_to(target.parent)):
            raise ValueError('Inputs and immutable result populations must remain outside output')
        pins[str(target)]=value['sha256'];return target
    contacts=pinned(request['contacts']);geometry=pinned(request['geometry'])
    actors=request['actors']
    if not isinstance(actors,dict) or len(actors)!=2:raise ValueError('Exactly two explicit actor layouts required')
    if set(actors)!=set(read(contacts)['actors']):raise ValueError('Actor names must match the bound original scene')
    sources={}
    for name,actor in actors.items():
        SceneContacts.name(name)
        fields(actor,('request','controls','active_keys'),'actor interval recipe')
        declaration=pinned(actor['request']);controls=pinned(actor['controls']);keys=actor['active_keys']
        if (not isinstance(keys,list) or not keys or any(type(k) is not int for k in keys)
                or keys!=sorted(set(keys)) or any(b-a!=1 for a,b in zip(keys,keys[1:]))):
            raise ValueError('Explicit complete contiguous integer key interval required')
        with np.load(controls,allow_pickle=False) as z:
            if set(z.files)!={'times_s','controls'} or not np.isfinite(z['controls']).all() or np.any(z['controls']):
                raise ValueError('Original zero-control epoch required, never a recentered seed')
        sources[name]=dict(request=declaration,controls=controls,active_keys=keys)
    samples=request['surface_samples']
    if (not isinstance(samples,list) or not samples or any(type(i) is not int or i<0 for i in samples)
            or samples!=sorted(set(samples))):raise ValueError('Sorted unique original surface sample indices required')
    if type(request['surface_seed']) is not int or not 0<=request['surface_seed']<=2**32-1:
        raise ValueError('Explicit bounded integer surface-query seed required')
    for key,low,high in [('trust',1e-6,1.),('difference_step',1e-6,.01),('contact_reserve_m',0.,.005)]:
        v=request[key]
        if type(v) not in (int,float) or not np.isfinite(v) or not low<=v<=high:raise ValueError('Invalid explicit '+key)
    if type(request['maximum_nonzeros']) is not int or not 1<=request['maximum_nonzeros']<=6000000:
        raise ValueError('Explicit complete sparse budget up to six million entries required')
    return request,contacts,geometry,sources,pins


def run(recipe_path,output):
    output=Path(output).resolve();request,cp,gp,sources,pins=inputs(recipe_path,output)
    with worker_lock(),threadpool_limits(limits=1):
        output.mkdir(parents=True);archive=output/'implementation';archive.mkdir()
        methods={p.name:sha256(p) for p in (ROOT/'scripts').glob('*.py')}
        for n in methods:shutil.copyfile(ROOT/'scripts'/n,archive/n)
        save(output/'recipe.json',request);models={};layouts={}
        def phase(name,**details):
            save(output/'pipeline.json',dict(status='processing',phase=name,at=now(),**details))
            print(dict(phase=name,**details),flush=True)
        try:
            for name,source in sources.items():
                phase('source-model',actor=name)
                paths=dict(contacts=cp,geometry=gp,request=source['request'],controls=source['controls'])
                model=KeyIntervalModel.from_inputs(**paths,active_keys=source['active_keys'],output=output/name/'source-seed',expected_sha256={k:pins[str(p)] for k,p in paths.items()})
                if model.name!=name:raise ValueError('Actor recipe names differ from bound source requests')
                models[name]=model;pins.update(model.pins)
                layouts[name]=dict(nodes=model.nodes,degrees=model.degrees,active_keys=source['active_keys'])
            pair=PairKeyGuides(models,[],fit_contacts=True);zero=pair.initial.copy();native,contact=pair.norms(zero,pair.source_worlds)
            positions=position_rows(pair);hard_contacts=contact.caps.copy();hard_contacts[positions]-=request['contact_reserve_m']
            if np.any(hard_contacts[positions]<=0):raise ValueError('Search reserve must fit every authored position tolerance')
            np.savez_compressed(output/'start-observations.npz',controls=zero,times_s=pair.times,native_vectors=native.vectors,native_caps=native.caps,native_scales=native.scales,contact_vectors=contact.vectors,contact_caps=contact.caps,contact_scales=contact.scales,protected_contact_caps=pair.protected_contact_caps,**{f'source_floor_{name}':pair.source_floor[name] for name in pair.names})
            save(output/'layouts.json',layouts);save(output/'actor-order.json',dict(actors=pair.names,offsets=pair.offsets.tolist()))
            save(output/'request.json',dict(schema=SCHEMA,inputs_sha256=pins,implementation_sha256=methods,solver=solver_identity(),original_source_epoch=True,controls=pair.size,geometry_sample_indices=request['surface_samples'],original_selected=True,quality_approved=False,release_approved=False))
            del native,contact;gc.collect();phase('source-surfaces',controls=pair.size)
            random=trimesh.util.random_generator();state=copy.deepcopy(random.bit_generator.state)
            seeded=np.random.default_rng(request['surface_seed'])
            if type(random.bit_generator) is not type(seeded.bit_generator):raise ValueError('Explicit compatible surface-query random generator required')
            try:
                random.bit_generator.state=copy.deepcopy(seeded.bit_generator.state)
                save(output/'surface-rng-before.json',random.bit_generator.state)
                surface=build(pair.scene,pair.models[pair.names[0]].policy,sha256(cp),maximum_rows=100000,sample_indices=request['surface_samples'],include_world_planes=False)
            finally:
                save(output/'surface-rng-after.json',random.bit_generator.state)
                random.bit_generator.state=state
            gaps,gjac,gmeta=surface_linearize(surface,layouts,maximum_nonzeros=request['maximum_nonzeros'])
            save(output/'surface-report.json',surface.report);save(output/'surface-rows.json',surface.rows);save(output/'surface-linearization.json',gmeta)
            np.savez_compressed(output/'surface-gaps.npz',gaps_m=gaps);sparse.save_npz(output/'surface-jacobian.npz',gjac)
            del surface;gc.collect();phase('complete-native-linearization',controls=pair.size)
            system,jac,identity=pair.linearize(zero,pair.source_worlds,request['trust'],step=request['difference_step'],maximum_nonzeros=request['maximum_nonzeros'])
            n=identity['native_rows'];c=identity['contact_rows'];hard=identity['hard_rows']
            if c!=len(hard_contacts):raise ValueError('Original coupled contact population differs')
            system.caps[n:n+c]=hard_contacts
            if len(gaps):
                extra,ejac,conversion=lift(gaps,gjac,zero,pair.lower,pair.upper,request['trust'])
                system=NormRows(np.r_[system.vectors,extra.vectors],np.r_[system.caps,extra.caps],np.r_[system.scales,extra.scales]);jac=sparse.vstack([jac,ejac],format='csc')
                del extra,ejac
            else:conversion=dict(rows=0,scope='No source surface witnesses; contact-only proposal, no geometry clearance inferred.')
            if jac.nnz>request['maximum_nonzeros']:raise ValueError('Complete combined model exceeds sparse budget; no subset returned')
            save(output/'linearization.json',dict(**identity,total_rows=len(system.caps),combined_nonzeros=jac.nnz,surface_rows=len(gaps),contact_position_rows=positions.tolist(),search_contact_caps=hard_contacts.tolist()))
            save(output/'surface-lift.json',conversion);sparse.save_npz(output/'jacobian.npz',jac)
            np.savez_compressed(output/'affine-observations.npz',vectors=system.vectors,caps=system.caps,scales=system.scales)
            del gjac;gc.collect();phase('coupled-solve',rows=len(system.caps),nonzeros=jac.nnz)
            delta,info=direction(system,jac,zero,pair.lower,pair.upper,request['trust'],hard_rows=hard);save(output/'solver.json',info)
            affine_pass=False
            if delta is not None:
                residual=system.residual(jac,delta);np.savez_compressed(output/'proposed-direction.npz',delta=delta,affine_residual=residual)
                affine_pass=bool(np.all(residual[:hard]<=1e-8))
                save(output/'affine-postcheck.json',dict(passed=affine_pass,hard_rows=hard,failed_rows=int((residual[:hard]>1e-8).sum()),maximum_normalized_excess=float(residual[:hard].max()),comparison=1e-8))
            candidate_path=None;decoded_contacts=None;del system,jac;gc.collect()
            if affine_pass:
                phase('export-candidate');folder=output/'probe-00';folder.mkdir();candidate=copy.deepcopy(read(cp))
                for i,name in enumerate(pair.names):
                    path=folder/f'{name}.glb';index=models[name].export(delta[pair.offsets[i]:pair.offsets[i+1]],path)
                    candidate['actors'][name].update(glb=str(path),sha256=sha256(path),animation_index=index)
                candidate_path=folder/'contacts.json';save(candidate_path,candidate);np.savez_compressed(output/'direction.npz',delta=delta)
                scene=SceneContacts(candidate,cp.parent);decoded_contacts,arrays=scene.evaluate();save(folder/'contacts-audit.json',decoded_contacts);np.savez_compressed(folder/'contact-observations.npz',**arrays);scene.check_inputs()
            pair.check()
            if (any(sha256(p)!=h for p,h in pins.items()) or methods!={p.name:sha256(p) for p in (ROOT/'scripts').glob('*.py')}):raise ValueError('Bound source or implementation changed')
            result=dict(schema=SCHEMA,status='complete',solver_status=info['status'],affine_pass=affine_pass,controls=pair.size,geometry_sample_indices=request['surface_samples'],candidate_contacts=str(candidate_path) if candidate_path else None,source_base_directory=str(cp.parent),decoded_authored_contacts_pass=decoded_contacts['passed'] if decoded_contacts else None,decoded_native_floor_geometry_pending=candidate_path is not None,original_selected=True,quality_approved=False,training_admitted=False,release_approved=False,scope='Source-zero paired contact/surface proposal with complete original native/floor protection and position-only search reserves. Any exported candidate remains unselected pending independent full decoded native/floor/contact/geometry validation and engine/semantic/human review.')
            save(output/'result.json',result);save(output/'pipeline.json',dict(status='complete',phase='complete',at=now()));return result
        except Exception as exc:
            save(output/'pipeline.json',dict(status='failed',phase='failed',error=str(exc),at=now(),original_selected=True,quality_approved=False,release_approved=False));raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('recipe',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args();run(args.recipe,args.output)
