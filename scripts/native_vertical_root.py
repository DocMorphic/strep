"""Native-key vertical-root proposals with original four-bin motion caps.

The scalar LP is a proposal model. Only full exported readback can pass the
declared sampled conditions; contact, balance and naturalness stay unapproved.
"""
import argparse
import copy
from pathlib import Path
import shutil
import numpy as np
from scipy import sparse
from scipy.optimize import linprog
from threadpoolctl import threadpool_limits
from action_worker_lock import worker_lock
from rig_asset import RigAsset
from native_support_clock import NativeSupportSampler
from root_plane_contact_bounds import translation_coefficients
from sampled_motion_caps import SampledMotionCaps,features,measures
from engine_contact_sampling import frame_populations
from gltf_tools import append_accessor,write_glb
from rig_floor_comparison import compare
from strep import ROOT,read,save,sha256,now
from native_vertical_storage import solve as solve_storage

SCHEMA='strep-native-vertical-root-v1'
METHODS=('native_vertical_root.py','native_vertical_storage.py','root_plane_contact_bounds.py','sampled_motion_caps.py','engine_contact_sampling.py',
    'rig_floor_comparison.py','rig_asset.py','gltf_tools.py','rig_clip_import.py','native_support_clock.py','action_worker_lock.py','strep.py')
FLAGS=dict(original_selected=True,quality_approved=False,training_admitted=False,release_approved=False)


def require(value,message):
    if not value:raise ValueError(message)


def basis(clock,queries):
    """Sparse LINEAR weights with the actual native sampler endpoint branches."""
    clock=np.asarray(clock);queries=np.asarray(queries,float)
    require(clock.ndim==queries.ndim==1 and len(clock)>=2 and np.isfinite(clock).all() and np.all(np.diff(clock)>0)
        and np.isfinite(queries).all() and np.all(queries>=0),'Finite native clock and queries required')
    rows=[];columns=[];values=[]
    for row,time in enumerate(queries):
        exact=int(np.searchsorted(clock,time,side='left'))
        if exact<len(clock) and float(clock[exact])==float(time):left=right=exact;fraction=0.
        elif time<=clock[0]:left=right=0;fraction=0.
        elif time>=clock[-1]:left=right=len(clock)-1;fraction=0.
        else:
            left=int(np.searchsorted(clock,time,side='right')-1);right=left+1
            fraction=(time-float(clock[left]))/float(clock[right]-clock[left])
        rows.append(row);columns.append(left);values.append(1-fraction)
        if right!=left:rows.append(row);columns.append(right);values.append(fraction)
    return sparse.csr_matrix((values,(rows,columns)),shape=(len(queries),len(clock)))


def vertical_intervals(vectors,caps,tolerance=1e-5):
    """Intersect every joint norm ball with a shared world-Y derivative."""
    vectors=np.asarray(vectors,float);caps=np.asarray(caps,float)
    require(vectors.ndim==3 and vectors.shape[2]==3 and caps.shape==vectors.shape[:2]
        and np.isfinite(vectors).all() and np.isfinite(caps).all() and np.all(caps>=0)
        and type(tolerance) in (int,float) and 0<=tolerance<=1e-5,'Complete finite original vector/cap population required')
    remainder=(caps+tolerance)**2-vectors[:,:,0]**2-vectors[:,:,2]**2
    require(np.all(remainder>=0),'Original horizontal motion already exceeds norm caps')
    span=np.sqrt(remainder);lower=-vectors[:,:,1]-span;upper=-vectors[:,:,1]+span
    low_ids=lower.argmax(axis=1);high_ids=upper.argmin(axis=1);row=np.arange(len(vectors))
    return lower[row,low_ids],upper[row,high_ids],low_ids,high_ids


def prepare(recipe,base):
    fields={'schema','source','floor_reference','maximum_displacement_m','floor_reserve_m','frozen_keys'}
    require(isinstance(recipe,dict) and set(recipe) in (fields,fields|{'storage_mode'}) and recipe['schema']==SCHEMA,'Explicit vertical-root recipe required')
    require(recipe.get('storage_mode','continuous') in ('continuous','float32-axis-grid'),'Explicit supported storage mode required')
    source=recipe['source'];reference=recipe['floor_reference']
    require(isinstance(source,dict) and set(source)=={'path','sha256','animation_index','root_node'}
        and isinstance(reference,dict) and set(reference)=={'path','sha256','side'},'Exact source and floor bindings required')
    for item in (source,reference):
        require(isinstance(item['path'],str) and isinstance(item['sha256'],str),'Explicit file path/digest required')
        path=(base/item['path']).resolve();require(sha256(path)==item['sha256'],'Source or floor reference changed')
    require(reference['side'] in ('source','target') and type(source['animation_index']) is int and type(source['root_node']) is int,'Explicit clip/root/reference side required')
    limit=recipe['maximum_displacement_m'];reserve=recipe['floor_reserve_m']
    require(type(limit) in (int,float) and np.isfinite(limit) and 0<limit<=.22
        and type(reserve) in (int,float) and np.isfinite(reserve) and reserve>=0,'Bounded original root movement and floor reserve required')
    path=(base/source['path']).resolve();rig=RigAsset.load(path);reader=NativeSupportSampler(rig.document,rig.binary,source['animation_index'])
    root=source['root_node'];coefficients,affected=translation_coefficients(rig,root)
    require(np.all(np.isin(rig.joints,affected)) and np.isfinite(coefficients).all() and np.all(coefficients>0),'Complete positive skin/root-subtree translation response required')
    ancestors=set();node=rig.parents[root]
    while node>=0:ancestors.add(int(node));node=rig.parents[node]
    require(not any(c[0] in ancestors for c in reader.channels),'Animated root ancestors require a different correction representation')
    channels=[c for c in reader.channels if c[:2]==(root,'translation')]
    require(len(channels)==1 and channels[0][4]=='LINEAR','One existing LINEAR root translation track required')
    channel=channels[0];clock=channel[2]
    require(len(clock)<=8192 and clock[0]==0 and float(clock[-1])==reader.duration,'Complete bounded root key clock required')
    frozen=recipe['frozen_keys'];require(isinstance(frozen,list) and bool(frozen) and all(type(i) is int and 0<=i<len(clock) for i in frozen) and len(set(frozen))==len(frozen),'Explicit distinct frozen native root keys required')
    floor=read((base/reference['path']).resolve());side=floor[reference['side']]
    require(floor['schema']=='strep-rig-floor-comparison-v1' and floor['status']=='complete' and side['sha256']==source['sha256'] and side['animation_index']==source['animation_index'],'Matching original floor comparison required')
    times=np.asarray(floor['times_s'],float);heights=np.asarray(side['minimum_y_m'],float)
    require(times.ndim==1 and len(times)==floor['samples']==len(heights) and 2<=len(times)<=20000
        and np.isfinite(times).all() and np.isfinite(heights).all() and times[0]==0 and times[-1]==reader.duration and np.all(np.diff(times)>0)
        and type(floor['floor_y_m']) in (int,float) and np.isfinite(floor['floor_y_m'])
        and type(floor['tolerance_m']) in (int,float) and np.isfinite(floor['tolerance_m']) and 0<=reserve<floor['tolerance_m']
        and floor['quality_approved'] is False and floor['human_approved'] is False,'Complete finite unapproved floor clock and original tolerance required')
    expected=np.unique(np.concatenate([np.array([0.,reader.duration])]+[p['times_s'] for p in frame_populations([0.,reader.duration])]
        +[v for c in reader.channels for v in (c[2],(c[2][:-1].astype(float)+c[2][1:].astype(float))/2)]))
    require(np.isin(expected,times).all(),'Floor reference omits original keys, midpoints or fixed frame populations')
    parent=rig.parents[root];rotation=rig.reference[parent,:3,:3] if parent>=0 else np.eye(3)
    axis=np.linalg.solve(rotation,np.array([0.,1.,0.]));require(abs(np.linalg.norm(axis)-1)<1e-10,'Rigid world-Y root translation required')
    return path,rig,reader,channel,axis,coefficients,times,heights,floor


def run(recipe_path,output):
    recipe_path,output=Path(recipe_path).resolve(),Path(output).resolve();require(not output.exists(),'Fresh root correction output required')
    with worker_lock(),threadpool_limits(limits=1):
        recipe=read(recipe_path);path,rig,reader,channel,axis,coefficients,times,heights,floor=prepare(recipe,recipe_path.parent)
        pins={str(p):sha256(p) for p in (recipe_path,path,(recipe_path.parent/recipe['floor_reference']['path']).resolve())}
        require(all(not Path(p).is_relative_to(output) for p in pins),'Original inputs must remain outside output')
        output.mkdir(parents=True);archive=output/'implementation';archive.mkdir();methods={n:sha256(ROOT/'scripts'/n) for n in METHODS}
        for n in methods:shutil.copyfile(ROOT/'scripts'/n,archive/n)
        save(output/'request.json',dict(recipe=recipe,source_bindings_sha256=pins,implementation_sha256=methods,**FLAGS))
        clock=channel[2];uniform=np.arange(int(np.floor(reader.duration*120))+1)/120
        world=np.array([reader.sample(float(t)) for t in uniform]);payload=features(world,rig.joints)
        original=SampledMotionCaps(payload,uniform,np.linspace(0,reader.duration,5),tolerance=1e-5)
        rows=[];rhs=[];intervals={};b=basis(clock,uniform)
        for order in (1,2):
            delta=np.diff(payload['positions'],n=order,axis=0)/original.dt**order
            lo,hi,low_ids,high_ids=vertical_intervals(delta,original.caps[order-1])
            d=(b[1:]-b[:-1])/original.dt if order==1 else (b[2:]-2*b[1:-1]+b[:-2])/original.dt**2
            rows.extend([d,-d]);rhs.extend([hi,-lo]);intervals[str(order)]=dict(lower=lo,upper=hi,lower_joints=low_ids,upper_joints=high_ids)
        lower=(floor['floor_y_m']-floor['tolerance_m']+recipe['floor_reserve_m']-heights)/float(coefficients.min())
        rows.append(-basis(clock,times));rhs.append(-lower)
        matrix=sparse.vstack(rows,format='csr');limits=np.concatenate(rhs)
        bounds=[(0.,0.) if i in recipe['frozen_keys'] else (0.,recipe['maximum_displacement_m']) for i in range(len(clock))]
        storage=None
        if recipe.get('storage_mode','continuous')=='float32-axis-grid':
            fit,storage=solve_storage(matrix,limits,channel[3],axis,recipe['maximum_displacement_m'],recipe['frozen_keys'])
            save(output/'storage.json',storage)
        else:
            fit=linprog(np.ones(len(clock)),A_ub=matrix,b_ub=limits,bounds=bounds,method='highs',options=dict(primal_feasibility_tolerance=1e-9,dual_feasibility_tolerance=1e-9,threads=1))
        sparse.save_npz(output/'linear-system.npz',matrix)
        np.savez_compressed(output/'reference.npz',uniform_times_s=uniform,geometry_times_s=times,source_world=world,
            rhs=limits,root_times_s=clock,root_axis_local=axis,**{f'cap_{i}':c for i,c in enumerate(original.caps)},
            **{f'order_{k}_{n}':v for k,d in intervals.items() for n,v in d.items()})
        from importlib.metadata import version
        result=dict(dependencies={name:version(name) for name in ('numpy','scipy','threadpoolctl')},solver_method='scipy-highs-lp' if storage is None else storage['method'],storage_mode=recipe.get('storage_mode','continuous'),solver_threads=1,schema=SCHEMA,status='complete',at=now(),solver_success=bool(fit.success),solver_status=int(fit.status),solver_message=str(fit.message),
            scalar_controls=len(clock),linear_rows=matrix.shape[0],full_original_rate_rows=sum(c.size for c in original.caps),source_sha256=sha256(path),
            original_caps_preserved=True,contact_verified=False,engine_verified=False,sampled_conditions_pass=False,**FLAGS)
        if fit.success:
            value=fit.x;save(output/'controls.json',dict(world_y_offsets_m=value.tolist(),frozen_keys=recipe['frozen_keys']))
            result['linear_maximum_violation']=float(np.maximum(matrix@value-limits,0).max())
            document=copy.deepcopy(rig.document);binary=bytearray(rig.binary);animation=copy.deepcopy(document['animations'][recipe['source']['animation_index']]);animation['name']='Strep_native_vertical_root'
            chosen=next(c for c in animation['channels'] if c['target']==dict(node=recipe['source']['root_node'],path='translation'))
            sampler=copy.deepcopy(animation['samplers'][chosen['sampler']]);values=channel[3].copy();active=value!=0;values[active]+=value[active,None]*axis
            sampler['output']=append_accessor(document,binary,values,'VEC3');chosen['sampler']=len(animation['samplers']);animation['samplers'].append(sampler)
            index=len(document['animations']);document['animations'].append(animation);candidate=output/'character.glb';write_glb(candidate,document,binary)
            decoded=RigAsset.load(candidate);after=NativeSupportSampler(decoded.document,decoded.binary,index)
            edit_times=np.unique(np.r_[uniform,times,clock]);rate_ids=np.searchsorted(edit_times,uniform)
            all_before=np.array([reader.sample(float(t)) for t in edit_times]);all_after=np.array([after.sample(float(t)) for t in edit_times])
            actual=all_after[rate_ids];measured=measures(features(actual,rig.joints),original.dt)
            failures=[int(np.sum(v>c+original.tolerance)) for v,c in zip(measured,original.caps)]
            audit=compare(path,candidate,times,source_animation=recipe['source']['animation_index'],target_animation=index,floor_y_m=floor['floor_y_m'],tolerance_m=floor['tolerance_m'])
            require(np.array_equal(audit['source']['minimum_y_m'],heights),'Bound source floor observations did not reproduce');save(output/'floor-comparison.json',audit)
            differences=all_after[:,rig.joints,:3,3]-all_before[:,rig.joints,:3,3];displacement=float(np.linalg.norm(differences,axis=-1).max());horizontal=float(np.abs(differences[:,:,[0,2]]).max())
            original_channels={(c[0],c[1]):c for c in reader.channels};unchanged=set(original_channels)=={c[:2] for c in after.channels}
            for c in after.channels:
                old=original_channels[(c[0],c[1])]
                unchanged &= np.array_equal(c[2],old[2]) and (np.array_equal(c[3][recipe['frozen_keys']],old[3][recipe['frozen_keys']]) if c[:2]==channel[:2] else np.array_equal(c[3],old[3]))
            np.savez_compressed(output/'decoded-observations.npz',edit_times_s=edit_times,source_world=all_before,candidate_world=all_after,**{f'metric_{i}':v for i,v in enumerate(measured)})
            result.update(output_animation_index=index,glb_sha256=sha256(candidate),rate_failures=failures,maximum_joint_displacement_m=displacement,
                maximum_horizontal_joint_drift_m=horizontal,horizontal_preservation_tolerance_m=1e-7,minimum_vertical_joint_shift_m=float(differences[:,:,1].min()),
                frozen_keys_and_other_tracks_preserved=bool(unchanged),floor_failed_samples=audit['target']['failed_samples'],peak_floor_depth_m=audit['target']['maximum_depth_m'],
                sampled_conditions_pass=bool(unchanged and displacement<=recipe['maximum_displacement_m'] and differences[:,:,1].min()>=0 and horizontal<=1e-7 and not any(failures) and audit['target']['sampled_floor_pass']))
        else:result['scope_failure']='No proposal from this sampled vertical-root model; not a global motion infeasibility certificate.'
        require(all(sha256(p)==h for p,h in pins.items()) and all(sha256(ROOT/'scripts'/n)==h==sha256(archive/n) for n,h in methods.items()),'Original input or method changed')
        result['scope']='Vertical root-only proposal, complete original four-bin rate and stored floor-clock readback. Geometry guidance uses a bound source floor receipt. No support, scene interaction, balance, continuous collision, engine, semantic or human approval.'
        result['artifacts']={str(p.relative_to(output)):sha256(p) for p in output.rglob('*') if p.is_file()};save(output/'result.json',result);return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('recipe',type=Path);parser.add_argument('output',type=Path);args=parser.parse_args();run(args.recipe,args.output)
