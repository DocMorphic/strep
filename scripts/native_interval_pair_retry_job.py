"""Retry a pinned current-point affine proposal without rebuilding its matrix."""
import argparse,copy,gc,shutil
from pathlib import Path
import numpy as np
from scipy import sparse
from threadpoolctl import threadpool_limits
from action_worker_lock import worker_lock
from native_interval_pair_restore_job import bind as bind_original,SCHEMA as ORIGINAL_SCHEMA
from native_key_interval_model import KeyIntervalModel
from native_scene_contacts import SceneContacts,fields
from native_scene_norms import NormRows
from native_scene_conic import direction as minimax,solver_identity
from native_scene_conic_sum import direction as aggregate
from strep import ROOT,read,save,sha256,now

SCHEMA='strep-native-interval-pair-retry-v1'
FILES=('request.json','result.json','restore-recipe.json','recipe.json','start-observations.npz','current-observations.npz','source-reference.json','linearization.json','affine-observations.npz','jacobian.npz','search-reserves.npz','actor-order.json','layouts.json')


def frozen(recipe_path,output):
    path=Path(recipe_path).resolve();output=Path(output).resolve();recipe_hash=sha256(path);r=read(path)
    fields(r,('schema','parent','rate_headroom','objective'),'frozen paired retry')
    if r['schema']!=SCHEMA or output.exists() or r['objective'] not in ('minimax','sum-positive-excess'):raise ValueError('Explicit retry schema, objective and fresh output required')
    p=r['parent'];fields(p,('path','sha256'),'pinned parent request')
    if type(p['path']) is not str or not p['path'] or type(p['sha256']) is not str or len(p['sha256'])!=64 or any(c not in '0123456789abcdef' for c in p['sha256']):raise ValueError('Pinned parent request required')
    request_path=(path.parent/p['path']).resolve()
    if not request_path.is_file() or request_path.name!='request.json' or sha256(request_path)!=p['sha256']:raise ValueError('Parent request changed')
    parent=request_path.parent;original_path=parent/'restore-recipe.json';original_hash=sha256(original_path)
    original,source,cp,gp,actors,roles,pins=bind_original(original_path,output)
    if pins[str(original_path)]!=original_hash:raise ValueError('Original validated binding changed')
    def keep(target,h):
        key=str(target)
        if key in pins and pins[key]!=h:raise ValueError('Previously validated binding changed')
        pins[key]=h
    keep(path,recipe_hash);keep(request_path,p['sha256'])
    for name in FILES:
        target=parent/name
        if not target.is_file():raise ValueError('Complete frozen restoration files required')
        keep(target,sha256(target))
    for target in list(pins):
        if Path(target).is_relative_to(output) or any((a/'result.json').is_file() and output.is_relative_to(a) for a in Path(target).parents):raise ValueError('Retry must remain outside immutable input populations')
    request=read(request_path);result=read(parent/'result.json')
    if request['schema']!=ORIGINAL_SCHEMA or result['schema']!=ORIGINAL_SCHEMA or result['status']!='complete' or not result['original_source_reference_exact'] or not result['original_selected'] or result['quality_approved'] or result['release_approved']:raise ValueError('Completed unselected original-source restoration required')
    guard=parent.parent/'guard/pipeline.json'
    if guard.is_file():
        audit=parent.parent/'resource-replay.json'
        if read(guard)['status']!='complete' or not audit.is_file() or not read(audit)['all_archived_bindings_match']:raise ValueError('Parent guarded job and independent resource replay must be complete')
        pins[str(guard)]=sha256(guard);pins[str(audit)]=sha256(audit)
    for name,h in request['implementation_sha256'].items():
        local=ROOT/'scripts'/name;archived=parent/'implementation'/name
        if Path(name).name!=name or not local.is_file() or not archived.is_file() or sha256(local)!=h or sha256(archived)!=h:raise ValueError('Frozen matrix producer implementation changed')
        pins[str(archived)]=h
    for target,h in request['inputs_sha256'].items():
        if sha256(target)!=h:raise ValueError('Original frozen input changed')
        if target in pins and pins[target]!=h:raise ValueError('Conflicting original source pin')
        pins[target]=h
    for target in pins:
        if Path(target).is_relative_to(output) or any((a/'result.json').is_file() and output.is_relative_to(a) for a in Path(target).parents):raise ValueError('Retry must remain outside immutable input populations')
    if sha256(parent/'start-observations.npz')!=sha256(roles['reference']) or read(parent/'recipe.json')!=source:raise ValueError('Original source reference or recipe changed')
    headroom=r['rate_headroom']
    if type(headroom) not in (int,float) or not np.isfinite(headroom) or not original['rate_headroom']<=headroom<=.01:raise ValueError('Search headroom can only tighten inside the declared bound')
    identity=read(parent/'linearization.json');n=identity['native_rows'];c=identity['contact_rows'];f=identity['floor_rows'];hard=identity['hard_rows'];value=np.asarray(original['value'],float)
    proof=read(parent/'source-reference.json')
    if not proof['original_source_reference_exact'] or proof['native_rows']!=n or not request['original_source_epoch'] or not request['linearization_at_current']:raise ValueError('Original source reference replay required')
    order=read(parent/'actor-order.json');expected_layouts={};sizes=[]
    for name,a in actors.items():
        declaration=read(a['request']);nodes=[v['node'] for v in declaration['rotations']];degrees=[v['maximum_degrees'] for v in declaration['rotations']]
        expected_layouts[name]=dict(nodes=nodes,degrees=degrees,active_keys=a['active_keys']);sizes.append(len(a['active_keys'])*len(nodes)*3)
    if order!=dict(actors=list(actors),offsets=np.r_[0,np.cumsum(sizes)].tolist()) or read(parent/'layouts.json')!=expected_layouts:raise ValueError('Original actor and control order changed')
    with np.load(parent/'affine-observations.npz',allow_pickle=False) as z:system=NormRows(z['vectors'],z['caps'],z['scales'])
    jac=sparse.load_npz(parent/'jacobian.npz').tocsc()
    if (hard!=n+c+f or identity['guide_rows']!=0 or identity['contact_objective_rows']!=c or identity['controls']!=len(value)
            or identity['total_rows']!=len(system.caps) or len(system.caps)!=hard+c+identity['surface_rows']
            or jac.shape!=(3*len(system.caps),len(value)) or jac.nnz!=identity['combined_nonzeros']
            or jac.nnz>original['maximum_nonzeros'] or not np.isfinite(jac.data).all()):raise ValueError('Complete unchanged frozen matrix layout required')
    responsive=np.diff(jac[:3*n].tocsr().indptr).reshape(n,3).sum(1)>0
    with np.load(parent/'start-observations.npz',allow_pickle=False) as source_ref,np.load(parent/'current-observations.npz',allow_pickle=False) as actual,np.load(parent/'search-reserves.npz',allow_pickle=False) as previous:
        caps=source_ref['native_caps'];scales=source_ref['native_scales']
        old=np.minimum(original['rate_headroom']*scales,.01*caps);old[~responsive]=0.
        checks=[(actual['controls'],value),(actual['native_vectors'],system.vectors[:n]),(actual['native_caps'],caps),(actual['native_scales'],scales),(previous['original_native_caps'],caps),(previous['native_reserve'],old),(system.caps[:n],caps-old),(system.scales[:n],scales),
            (actual['contact_caps'],source_ref['contact_caps']),(system.vectors[n:n+c],actual['contact_vectors']),(system.vectors[hard:hard+c],actual['contact_vectors']),(system.caps[hard:hard+c],source_ref['contact_caps']),(system.scales[n:n+c],source_ref['contact_scales']),(system.scales[hard:hard+c],source_ref['contact_scales'])]
        if n!=len(caps) or any(not np.array_equal(a,b) for a,b in checks) or np.any(system.caps[n:n+c]>source_ref['protected_contact_caps']):raise ValueError('Frozen original bounds, observations or search reserve changed')
        new=np.minimum(headroom*scales,.01*caps);new[~responsive]=0.
        if np.any(new<old):raise ValueError('Search caps cannot loosen')
        system.caps[:n]=caps-new
    return r,parent,original,source,cp,gp,actors,roles,pins,system,jac,identity,value,new


def _run(recipe_path,output):
    output=Path(output).resolve();r,parent,original,source,cp,gp,actors,roles,pins,system,jac,identity,value,reserve=frozen(recipe_path,output)
    with worker_lock(),threadpool_limits(limits=1):
        output.mkdir(parents=True);archive=output/'implementation';archive.mkdir();methods={p.name:sha256(p) for p in (ROOT/'scripts').glob('*.py')}
        for name in methods:shutil.copyfile(ROOT/'scripts'/name,archive/name)
        save(output/'retry-recipe.json',r);save(output/'recipe.json',source)
        for name in ('start-observations.npz','actor-order.json','layouts.json'):shutil.copyfile(parent/name,output/name)
        request=dict(schema=SCHEMA,inputs_sha256=pins.copy(),implementation_sha256=methods,parent_implementation_sha256=read(parent/'request.json')['implementation_sha256'],solver=solver_identity(),geometry_sample_indices=source['surface_samples'],frozen_matrix_reused=True,original_selected=True,quality_approved=False,release_approved=False)
        save(output/'request.json',request)
        save(output/'pipeline.json',dict(status='processing',phase='frozen-solve',at=now()))
        np.savez_compressed(output/'search-reserves.npz',native_reserve=reserve)
        hard=identity['hard_rows'];solver=minimax if r['objective']=='minimax' else aggregate
        step,info=solver(system,jac,value,-np.ones(len(value)),np.ones(len(value)),original['trust'],hard_rows=hard)
        save(output/'solver.json',info);passed=False;candidate_path=None;contacts=None
        if step is not None:
            point=value+step;residual=system.residual(jac,step)
            np.savez_compressed(output/'proposed-direction.npz',controls=point,step=step,affine_residual=residual)
            box=bool(np.all(abs(point)<=1) and np.all(abs(step)<=original['trust']+1e-9))
            passed=bool(box and np.all(residual[:hard]<=1e-8));save(output/'affine-postcheck.json',dict(passed=passed,original_boxes_and_trust_pass=box,hard_rows=hard,failed_rows=int((residual[:hard]>1e-8).sum()),maximum_normalized_excess=float(residual[:hard].max()),comparison=1e-8))
        del system,jac;gc.collect()
        if passed:
            order=read(parent/'actor-order.json');names=order['actors'];offsets=order['offsets']
            if set(names)!=set(actors) or len(offsets)!=len(names)+1 or offsets[0]!=0 or offsets[-1]!=len(value):raise ValueError('Original complete control order required')
            folder=output/'probe-00';folder.mkdir();candidate=copy.deepcopy(read(cp))
            for i,name in enumerate(names):
                a=actors[name];paths=dict(contacts=cp,geometry=gp,request=a['request'],controls=a['controls'])
                model=KeyIntervalModel.from_inputs(**paths,active_keys=a['active_keys'],output=output/name/'source-seed',expected_sha256={k:pins[str(p)] for k,p in paths.items()})
                if model.name!=name or model.size!=offsets[i+1]-offsets[i]:raise ValueError('Original control layout changed')
                path=folder/f'{name}.glb';index=model.export(point[offsets[i]:offsets[i+1]],path);candidate['actors'][name].update(glb=str(path),sha256=sha256(path),animation_index=index);model.check();pins.update(model.pins);del model;gc.collect()
            candidate_path=folder/'contacts.json';save(candidate_path,candidate);np.savez_compressed(output/'direction.npz',delta=point);np.savez_compressed(output/'controls.npz',controls=point,step=step)
            scene=SceneContacts(candidate,cp.parent);contacts,arrays=scene.evaluate();save(folder/'contacts-audit.json',contacts);np.savez_compressed(folder/'contact-observations.npz',**arrays);scene.check_inputs()
        if any(sha256(p)!=h for p,h in pins.items()) or methods!={p.name:sha256(p) for p in (ROOT/'scripts').glob('*.py')}:raise ValueError('Frozen input or implementation changed')
        request['inputs_sha256']=pins.copy();save(output/'request.json',request)
        result=dict(schema=SCHEMA,status='complete',solver_status=info['status'],objective=r['objective'],rate_headroom=r['rate_headroom'],affine_pass=passed,candidate_contacts=str(candidate_path) if candidate_path else None,decoded_authored_contacts_pass=None if contacts is None else contacts['passed'],frozen_matrix_reused=True,original_source_reference_reused=True,original_selected=True,quality_approved=False,release_approved=False,scope='Same original current-point matrix, original trust box and stricter search caps. Original acceptance limits unchanged. Actual full native/floor/contact/mesh and engine/semantic/human checks still required.')
        save(output/'result.json',result);save(output/'pipeline.json',dict(status='complete',phase='complete',at=now()));return result


def run(recipe_path,output):
    existed=Path(output).exists()
    try:return _run(recipe_path,output)
    except Exception as exc:
        output=Path(output).resolve()
        if not existed and (output/'request.json').is_file() and not (output/'result.json').exists():save(output/'pipeline.json',dict(status='failed',phase='failed',error=str(exc),at=now(),original_selected=True,quality_approved=False,release_approved=False))
        raise


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('recipe',type=Path);p.add_argument('output',type=Path);a=p.parse_args();run(a.recipe,a.output)
