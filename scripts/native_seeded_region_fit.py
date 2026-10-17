"""Original-bound native-key region proposals from a complete nonzero seed.

Explicit permissions and observations only; no action whitelist, automatic
contact intent, collision clearance or animation acceptance. Call in a guarded
worker and independently validate complete saved motion before selection.
"""
import copy
import numpy as np
from scipy.optimize import minimize
from scipy.spatial.transform import Rotation
from native_partitioned_affine_pose import PartitionedAffineKeyPose
from native_key_pose_map import KeyPoseMap
from native_affine_region_pose import RegionPoseRows
from native_key_contact_initializer import encode

MAXIMUM_ROWS=100000
MAXIMUM_JACOBIAN_BYTES=64*1024**2
MAXIMUM_OBSERVATIONS=128


class SeededRegionProblem:
    def __init__(self,actor,nodes,degrees,clock,seed_controls,active_pairs,
                 frozen_keys,world_caps_m,observations,*,maximum_rows=MAXIMUM_ROWS,
                 maximum_jacobian_bytes=MAXIMUM_JACOBIAN_BYTES):
        if (not isinstance(nodes,list) or not nodes or not isinstance(active_pairs,list)
                or not active_pairs or any(not isinstance(p,(list,tuple)) or len(p)!=2
                    or any(type(v) is not int for v in p) for p in active_pairs)
                or not isinstance(frozen_keys,list) or any(type(k) is not int for k in frozen_keys)
                or len(set(frozen_keys))!=len(frozen_keys)
                or not isinstance(observations,list) or not 1<=len(observations)<=MAXIMUM_OBSERVATIONS
                or type(maximum_rows) is not int or not 1<=maximum_rows<=MAXIMUM_ROWS
                or type(maximum_jacobian_bytes) is not int
                or not 1<=maximum_jacobian_bytes<=MAXIMUM_JACOBIAN_BYTES):
            raise ValueError('Explicit complete seed, permissions, frozen keys and bounded observations required')
        times=np.asarray(clock)
        if (times.dtype.kind not in 'fiu' or times.ndim!=1 or not 3<=len(times)<=4096
                or not np.isfinite(times).all() or np.any(np.diff(times)<=0)
                or any(not 0<=k<len(times) for k in frozen_keys)
                or not {0,len(times)-1}.issubset(frozen_keys)
                or any(k in frozen_keys for k,_ in active_pairs)):
            raise ValueError('Increasing complete native clock, frozen true endpoints and nonfrozen edit keys required')
        selected=list(dict.fromkeys(n for _,n in active_pairs));self.samples=[];groups={};offsets=[0]
        count=0;size=3*len(active_pairs)
        for observation in copy.deepcopy(observations):
            if not isinstance(observation,dict) or set(observation)!={'time_s','regions'}:
                raise ValueError('Explicit observation time and complete region list required')
            stamp=observation['time_s']
            if type(stamp) not in (int,float) or not np.isfinite(stamp):
                raise ValueError('Explicit finite observation time required')
            if stamp not in groups:
                model=PartitionedAffineKeyPose(actor,stamp,nodes,degrees,maximum_derivative_controls=3*len(selected))
                mapper=KeyPoseMap(model,stamp,seed_controls,active_pairs)
                if not np.array_equal(mapper.clock,times):
                    raise ValueError('Supplied clock must exactly equal every original controlled channel')
                groups[stamp]=(mapper,[])
            mapper,indices=groups[stamp];model=mapper.model
            full=mapper.controls(mapper.initial)
            problem=RegionPoseRows(model,stamp,full,selected,world_caps_m,observation['regions'])
            count+=problem.report['rows']+len(active_pairs)
            if count>maximum_rows or count*size*8>maximum_jacobian_bytes:
                raise ValueError('Complete multi-time rows/Jacobian exceed declared budget; no observations discarded')
            indices.append(len(self.samples));self.samples.append((mapper,problem));offsets.append(count)
        self.groups=tuple((mapper,tuple(indices)) for mapper,indices in groups.values())
        self.offsets=tuple(offsets)
        self.initial=self.samples[0][0].initial.copy();self.initial.setflags(write=False)
        self.seed=self.samples[0][0].seed.copy();self.seed.setflags(write=False)
        self.clock=times.astype(float).copy();self.clock.setflags(write=False)
        self.actor=actor;self.nodes=tuple(nodes);self.degrees=tuple(degrees)
        self.pairs=tuple(map(tuple,active_pairs));self.frozen=tuple(frozen_keys)
        self.size=size;self.rows=count
        self.report=dict(schema='strep-native-seeded-region-problem-v1',observations=len(self.samples),
            unique_pose_times=len(self.groups),evaluation_reuse='One fresh map and native frame per distinct time per evaluation; original row order retained',
            controlled_joints=len(nodes),active_native_pairs=len(active_pairs),controls=size,
            frozen_keys=list(frozen_keys),complete_rows=count,jacobian_bytes=count*size*8,
            maximum_rows=maximum_rows,maximum_jacobian_bytes=maximum_jacobian_bytes,
            original_reference_preserved=True,quality_approved=False,release_approved=False,
            scope='Explicit sampled region proposal from complete original-relative seed; not full-clock, '
                  'contact, self/partner/object collision, rate, engine or human acceptance.')

    def evaluate(self,value):
        rows=np.empty(self.rows);matrix=np.empty((self.rows,self.size))
        for mapper,indices in self.groups:
            full,mapping=mapper.evaluate(value);native,native_jac=mapper.native_rows(value)
            first=self.samples[indices[0]][1]
            frame=mapper.model.evaluate_columns(full,first.coordinates)
            for i in indices:
                problem=self._checked_problem(mapper,i,full,first.coordinates)
                pose,jac,*_=problem._rows(full,frame)
                start,end=self.offsets[i:i+2]
                rows[start:end]=np.r_[pose,native]
                matrix[start:end]=np.vstack([jac@mapping[problem.coordinates],native_jac])
        return rows,matrix

    def _checked_problem(self,mapper,index,full,coordinates):
        bound,problem=self.samples[index]
        required={3*int(mapper.track_ids[p])+axis for p in mapper.dependent for axis in range(3)}
        if (bound is not mapper or problem.model is not mapper.model
                or problem.report['time_s']!=mapper.time_s
                or not np.array_equal(problem.coordinates,coordinates)
                or not required.issubset(set(problem.coordinates.tolist()))):
            raise ValueError('Constructor-bound observation model/coordinates changed')
        actual=problem._controls(full[problem.coordinates])
        if not np.array_equal(actual,full):raise ValueError('Fixed original-relative seed changed')
        return problem

    def quantized_rows(self,value):
        """Actual Float32 endpoint encoding; no derivative of quantization claimed."""
        rows=np.empty(self.rows)
        for mapper,indices in self.groups:
            full=mapper.controls(value,quantized=True)
            first=self.samples[indices[0]][1];frame=mapper.model.evaluate_columns(full,first.coordinates);native=[]
            # A native key outside this observation's bracket still needs its
            # actual encoded angle checked: Float32 can overshoot a unit ball.
            for (key,node),vector in zip(self.pairs,np.asarray(value).reshape(-1,3)):
                track=self.nodes.index(node);original=mapper.original_quaternions[track,key]
                q=original.copy()
                if np.any(vector):
                    q=(Rotation.from_quat(original)*Rotation.from_rotvec(vector*mapper.caps[track])).as_quat()
                    if q@original<0:q=-q
                q=q.astype(np.float32).astype(float)
                fraction=(Rotation.from_quat(original).inv()*Rotation.from_quat(q)).magnitude()/mapper.caps[track]
                native.append(1-fraction*fraction)
            for i in indices:
                problem=self._checked_problem(mapper,i,full,first.coordinates)
                pose=problem._rows(full,frame)[0]
                rows[self.offsets[i]:self.offsets[i+1]]=np.r_[pose,native]
        return rows

    def controls(self,value):
        # The public map validates the unchanged source and proposal domain.
        for mapper,_ in self.groups:mapper.controls(value)
        result=self.seed.copy();values=np.asarray(value,float).reshape(-1,3)
        if np.any(np.linalg.norm(values,axis=1)>1):
            raise ValueError('Every proposed native rotation must fit its original unit ball')
        for (key,node),vector in zip(self.pairs,values):result[key,self.nodes.index(node)]=vector
        np.testing.assert_array_equal(result[list(self.frozen)],self.seed[list(self.frozen)])
        return result

    def export(self,value,path):
        """Append an unselected proposal clip, preserving original binary/animations."""
        from pathlib import Path
        path=Path(path)
        if path.exists():raise ValueError('Fresh separate candidate path required')
        values=self.controls(value);model=self.samples[0][0].model
        channels=[next(c for c in self.actor['sampler'].channels if c[:2]==(node,'rotation')) for node in self.nodes]
        return encode(model.rig,self.actor['animation_index'],list(self.nodes),channels,values,list(self.degrees),path)


def fit(problem,*,iterations=32,search_reserve=None,on_evaluation=None):
    if (not isinstance(problem,SeededRegionProblem) or type(iterations) is not int
            or not 1<=iterations<=64 or (on_evaluation is not None and not callable(on_evaluation))):
        raise ValueError('Qualified complete seeded problem and 1-64 proposal iterations required')
    reserve=np.zeros(problem.rows) if search_reserve is None else np.asarray(search_reserve)
    if (reserve.dtype.kind not in 'fiu' or reserve.shape!=(problem.rows,) or not np.isfinite(reserve).all()
            or np.any(reserve<0) or np.any(reserve>.1)):
        raise ValueError('Complete finite nonnegative normalized search reserves up to 0.1 required')
    reserve=reserve.astype(float,copy=True)
    initial=problem.initial.copy();history=[];cache=None
    def evaluate(value):
        nonlocal cache
        # Even a repeated point must reject a changed source/seed binding.
        for mapper,_ in problem.groups:mapper.controls(value)
        if cache is None or not np.array_equal(cache[0],value):
            rows,jac=problem.evaluate(value);cache=(value.copy(),rows,jac)
            history.append(dict(evaluation=len(history),controls=value.tolist(),minimum_row=float(rows.min()),
                                failed_rows=int(np.count_nonzero(rows<0)),search_failed_rows=int(np.count_nonzero(rows<reserve))))
            if on_evaluation is not None:
                on_evaluation(dict(history[-1],controls=value.copy(),rows=rows.copy()))
        return cache[1],cache[2]
    result=minimize(lambda x:.5*float((x-initial)@(x-initial)),initial,
        jac=lambda x:x-initial,method='SLSQP',bounds=[(-1.,1.)]*problem.size,
        constraints=[dict(type='ineq',fun=lambda x:evaluate(x)[0]-reserve,jac=lambda x:evaluate(x)[1])],
        options=dict(maxiter=iterations,ftol=1e-12))
    raw=problem.evaluate(result.x)[0];quantized=problem.quantized_rows(result.x)
    return result.x,dict(schema='strep-native-seeded-region-fit-v1',solver='scipy SLSQP',
        solver_success=bool(result.success),solver_status=int(result.status),solver_message=str(result.message),
        iterations=int(result.nit),maximum_iterations=iterations,evaluations=history,
        raw_failed_rows=int(np.count_nonzero(raw<0)),quantized_failed_rows=int(np.count_nonzero(quantized<0)),
        minimum_raw_row=float(raw.min()),minimum_quantized_row=float(quantized.min()),
        search_reserve=reserve.tolist(),search_failed_rows=int(np.count_nonzero(raw<reserve)),
        declared_raw_conditions_pass=bool(np.all(raw>=0)),declared_quantized_conditions_pass=bool(np.all(quantized>=0)),
        physical_comparison='All declared rows >= 0, with no acceptance tolerance',
        original_selected=True,quality_approved=False,release_approved=False,
        scope='Distance-to-seed proposal under complete explicit sampled rows. Solver success is not '
              'condition acceptance; saved assets need independent complete motion/geometry/engine/human review.')
