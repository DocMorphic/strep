"""Two supplied native rigs: explicit coupled pair guidance and hard pose rows.

This evaluator does not infer contacts, select edit permissions, run an engine
or approve motion. Callers bind complete source assets/versions, guard runtime
resources and independently audit actual saved curves, full meshes and quality.
"""
import numpy as np
from scipy.spatial.transform import Rotation
from native_partitioned_affine_pose import PartitionedAffineKeyPose
from native_key_pose_map import KeyPoseMap
from native_affine_pose_bounds import PoseBoundsRows
from native_grouped_pair_gap_rows import GroupedPairGapRows
from native_pair_gap_groups import MAXIMUM_PAIR_REFERENCES
from native_scene_geometry import faces_for
from native_support_clock import NativeSupportSampler

MAXIMUM_ROWS=100000
MAXIMUM_JACOBIAN_BYTES=64*1024**2
MAXIMUM_CONTROLS=768
MAXIMUM_OBSERVATIONS=512


class CoupledKeyPairRows:
    def __init__(self,left,right,observations,*,maximum_observations=128,
                 maximum_rows=MAXIMUM_ROWS,maximum_jacobian_bytes=MAXIMUM_JACOBIAN_BYTES):
        for value,limit in [(maximum_observations,MAXIMUM_OBSERVATIONS),(maximum_rows,MAXIMUM_ROWS),(maximum_jacobian_bytes,MAXIMUM_JACOBIAN_BYTES)]:
            if type(value) is not int or not 1<=value<=limit:raise ValueError('Bounded complete problem settings required')
        if not isinstance(observations,list) or not 1<=len(observations)<=maximum_observations:
            raise ValueError('One to the declared maximum complete observations required')
        self._specs=[];self._offsets=[];cursor=0
        fields={'actor','nodes','degrees','clock','seed_controls','active_pairs','frozen_keys','world_caps_m'}
        for spec in (left,right):
            if not isinstance(spec,dict) or set(spec)!=fields:raise ValueError('Complete explicit native actor specification required')
            actor=spec['actor'];degrees=np.asarray(spec['degrees'])
            if (not isinstance(actor,dict) or not {'rig','sampler','placement','animation_index'}<=set(actor)
                    or not isinstance(actor['sampler'],NativeSupportSampler)):
                raise ValueError('Original supplied native actor required')
            nodes=spec['nodes'];pairs=spec['active_pairs'];frozen=spec['frozen_keys'];clock=np.asarray(spec['clock'])
            if (not isinstance(nodes,list) or not nodes or any(type(n) is not int for n in nodes)
                    or len(set(nodes))!=len(nodes) or not isinstance(pairs,list) or not pairs
                    or any(not isinstance(p,(list,tuple)) or len(p)!=2 or any(type(v) is not int for v in p) for p in pairs)
                    or len(set(map(tuple,pairs)))!=len(pairs)
                    or not isinstance(frozen,list) or any(type(k) is not int for k in frozen) or len(set(frozen))!=len(frozen)
                    or clock.dtype.kind not in 'fiu' or clock.ndim!=1 or not 3<=len(clock)<=4096
                    or not np.isfinite(clock).all() or np.any(np.diff(clock)<=0)
                    or any(not 0<=k<len(clock) for k in frozen) or not {0,len(clock)-1}.issubset(frozen)
                    or any(k in frozen or not 0<=k<len(clock) or n not in nodes for k,n in pairs)):
                raise ValueError('Complete native clock, distinct explicit edit pairs and frozen true endpoints required')
            if degrees.dtype.kind not in 'fiu' or degrees.shape!=(len(nodes),) or not np.isfinite(degrees).all():raise ValueError('One explicit finite real rotation band per node required')
            copied=dict(spec,nodes=nodes.copy(),degrees=degrees.tolist(),clock=clock.astype(float).copy(),
                        seed_controls=np.array(spec['seed_controls'],copy=True),active_pairs=[tuple(p) for p in pairs],
                        frozen_keys=frozen.copy(),world_caps_m=np.array(spec['world_caps_m'],copy=True))
            size=3*len(pairs);self._offsets.append((cursor,cursor+size));cursor+=size;self._specs.append(copied)
        if not 1<=cursor<=MAXIMUM_CONTROLS:raise ValueError('Complete combined native-control budget exceeded; no pairs discarded')
        self.size=cursor;self._samples=[];self._layout=[];count=0;initial=[];first_mappers=[]
        topology=[faces_for(spec['actor']['rig'])[0].copy() for spec in self._specs]
        duration=[spec['actor']['sampler'].duration for spec in self._specs]
        if duration[0]!=duration[1]:raise ValueError('Shared exact duration required; retime explicitly first')
        previous=-np.inf
        for observation in observations:
            if not isinstance(observation,dict) or set(observation)!={'time_s','gaps'}:raise ValueError('Explicit observation time and complete gap list required')
            stamp=observation['time_s'];gaps=observation['gaps']
            if (type(stamp) not in (int,float) or not np.isfinite(stamp) or not 0<=stamp<=duration[0] or stamp<=previous
                    or not isinstance(gaps,list) or len(gaps)>32):raise ValueError('Increasing distinct shared times and at most32 complete gap contexts required')
            previous=stamp;contexts=[]
            for side,spec in enumerate(self._specs):
                active=list(dict.fromkeys(n for k,n in spec['active_pairs']))
                model=PartitionedAffineKeyPose(spec['actor'],stamp,spec['nodes'],spec['degrees'],maximum_derivative_controls=3*len(active))
                mapper=KeyPoseMap(model,stamp,spec['seed_controls'],spec['active_pairs'])
                if not np.array_equal(mapper.clock,spec['clock']):raise ValueError('Complete supplied clock must equal original controlled channels')
                helper=PoseBoundsRows(model,stamp,mapper.controls(mapper.initial),active,spec['world_caps_m'])
                contexts.append((mapper,helper));self._layout.append(('pose',float(stamp),side,count,count+helper.hard_rows,not bool(mapper.dependent)));count+=helper.hard_rows
                if len(self._samples)==0:initial.extend(mapper.initial.tolist());first_mappers.append(mapper)
            grouped=[]
            for gap in gaps:
                if (not isinstance(gap,dict) or not {'pairs','normal_world','minimum_gap_m'}<=set(gap)
                        or set(gap)-{'pairs','normal_world','minimum_gap_m','length_scale_m','temperature_m','actor_sides'}):raise ValueError('Complete explicit paired-triangle gap context required')
                sides=gap.get('actor_sides',[0,1])
                if not isinstance(sides,list) or len(sides)!=2 or any(type(side) is not int or side not in (0,1) for side in sides):
                    raise ValueError('Explicit pair of actor indices0 or1 required')
                sides=tuple(sides)
                pairs=np.asarray(gap['pairs'])
                if (pairs.dtype.kind not in 'iu' or pairs.ndim!=2 or pairs.shape[1:]!=(2,)
                        or not 1<=len(pairs)<=MAXIMUM_PAIR_REFERENCES or np.any(pairs<0)
                        or any(np.any(pairs[:,column]>=len(topology[side])) for column,side in enumerate(sides))):raise ValueError('Complete bounded existing paired triangle references required')
                item=GroupedPairGapRows(topology[sides[0]][pairs[:,0]],topology[sides[1]][pairs[:,1]],
                    len(contexts[sides[0]][0].model.skin.nodes),len(contexts[sides[1]][0].model.skin.nodes),gap['normal_world'],
                    minimum_gap_m=gap['minimum_gap_m'],length_scale_m=gap.get('length_scale_m',.01),temperature_m=gap.get('temperature_m',1e-5))
                grouped.append((sides,item));rows=item.report['rows'];self._layout.append(('gap',float(stamp),len(grouped)-1,count,count+rows,not any(contexts[side][0].dependent for side in sides)));count+=rows
            if count*self.size*8>maximum_jacobian_bytes or count>maximum_rows:raise ValueError('Complete coupled row/Jacobian budget exhausted; no observations discarded')
            self._samples.append((float(stamp),tuple(contexts),tuple(grouped)))
        for side,mapper in enumerate(first_mappers):
            rows=len(mapper.pairs);self._layout.append(('native',None,side,count,count+rows,False));count+=rows
        if count>maximum_rows or count*self.size*8>maximum_jacobian_bytes:raise ValueError('Complete coupled row/Jacobian budget exhausted; no native constraints discarded')
        self.rows=count;self.initial=np.array(initial);self.initial.setflags(write=False)
        self._report=dict(schema='strep-native-coupled-key-pair-rows-v1',observations=len(self._samples),
            native_controls=self.size,rows=count,jacobian_bytes=count*self.size*8,
            maximum_jacobian_bytes=maximum_jacobian_bytes,original_pair_references=sum(g.report['pair_references'] for t,c,groups in self._samples for sides,g in groups),
            self_gap_contexts=sum(sides[0]==sides[1] for t,c,groups in self._samples for sides,g in groups),
            partner_gap_contexts=sum(sides[0]!=sides[1] for t,c,groups in self._samples for sides,g in groups),
            quality_approved=False,release_approved=False,
            scope='Selected original-bound native pose and variable-key balls plus explicit paired-triangle contexts only; fixed seed/whole-curve saved geometry/engine/human validation remain caller responsibilities')

    @property
    def report(self):return dict(self._report)

    @property
    def layout(self):return tuple(self._layout)

    def _value(self,value):
        array=np.asarray(value)
        if array.dtype.kind not in 'fiu' or array.shape!=(self.size,) or not np.isfinite(array).all():raise ValueError('Complete finite combined native proposal required')
        return array.astype(float,copy=False)

    def check_binding(self,value):
        value=self._value(value)
        for stamp,contexts,gaps in self._samples:
            for side,(mapper,helper) in enumerate(contexts):mapper.controls(value[slice(*self._offsets[side])])

    def _evaluate(self,value,*,encoded=False,smooth=True,jacobian=True,original_pairs=False):
        if any(type(v) is not bool for v in (encoded,smooth,jacobian,original_pairs)) or jacobian and (encoded or not smooth):
            raise ValueError('Explicit boolean modes; derivatives require raw smooth rows')
        value=self._value(value);blocks=[];matrices=[];pairs=[]
        for stamp,contexts,gaps in self._samples:
            frames=[]
            for side,(mapper,helper) in enumerate(contexts):
                first,last=self._offsets[side];local=value[first:last]
                if jacobian:full,mapping=mapper.evaluate(local)
                else:full=mapper.controls(local,quantized=encoded);mapping=None
                np.testing.assert_array_equal(helper._controls(full[helper.coordinates]),full)
                frame=mapper.model.evaluate_columns(full,helper.coordinates if jacobian else [])
                if jacobian:
                    rows,jac,*_=helper._rows(full,frame);matrix=np.zeros((len(rows),self.size));matrix[:,first:last]=jac@mapping[helper.coordinates];matrices.append(matrix)
                else:
                    world=frame[0];balls=full.reshape(-1,3);delta=world[mapper.model.rig.joints,:3,3]-helper.source[mapper.model.rig.joints,:3,3]
                    rows=np.r_[1-np.sum(balls*balls,axis=1),1-np.sum(delta*delta,axis=1)/helper.caps**2]
                blocks.append(rows)
                position,rotation=mapper.model.actor['placement'];points=frame[1]@rotation.T+position
                frames.append((points,np.einsum('ij,vjc->vic',rotation,frame[2]) if jacobian else None,mapping[helper.coordinates] if jacobian else None))
            for sides,gap in gaps:
                left,right=(frames[side] for side in sides)
                rows,ja,jb=gap.evaluate(left[0],right[0],left_jacobian=left[1] if jacobian else None,right_jacobian=right[1] if jacobian else None,smooth=smooth)
                blocks.append(rows)
                if jacobian:
                    matrix=np.zeros((len(rows),self.size))
                    # A self pair has two geometry chains into the same native
                    # variables. Accumulate both; assignment would lose one.
                    for side,derivative in zip(sides,(ja,jb)):matrix[:,slice(*self._offsets[side])]+=derivative@frames[side][2]
                    matrices.append(matrix)
                if original_pairs:
                    exact=gap.exact_pairs(left[0],right[0]);info=gap.report
                    pairs.append((exact['projected_gaps_m']-info['minimum_gap_m'])/info['length_scale_m'])
        for side,(mapper,helper) in enumerate(self._samples[0][1]):
            first,last=self._offsets[side];local=value[first:last];rows,jac=mapper.native_rows(local)
            if encoded:
                rows=[]
                for (key,node),vector in zip(mapper.pairs,local.reshape(-1,3)):
                    track=mapper.nodes.index(node);old=mapper.original_quaternions[track,key];q=old.copy()
                    if np.any(vector):
                        q=(Rotation.from_quat(old)*Rotation.from_rotvec(vector*mapper.caps[track])).as_quat()
                        if q@old<0:q=-q
                    q=q.astype(np.float32).astype(float);fraction=(Rotation.from_quat(old).inv()*Rotation.from_quat(q)).magnitude()/mapper.caps[track];rows.append(1-fraction*fraction)
            blocks.append(np.asarray(rows))
            if jacobian:
                matrix=np.zeros((len(rows),self.size));matrix[:,first:last]=jac;matrices.append(matrix)
        rows=np.concatenate(blocks);matrix=np.vstack(matrices) if jacobian else None
        if rows.shape!=(self.rows,) or not np.isfinite(rows).all() or matrix is not None and (matrix.shape!=(self.rows,self.size) or not np.isfinite(matrix).all()):raise ValueError('Incomplete or nonfinite coupled rows/Jacobian')
        pair_rows=np.concatenate(pairs) if pairs else np.empty(0)
        if original_pairs and (len(pair_rows)!=self._report['original_pair_references'] or not np.isfinite(pair_rows).all()):raise ValueError('Incomplete or nonfinite original pair checks')
        return rows,matrix,pair_rows

    def evaluate(self,value):
        rows,matrix,_=self._evaluate(value);return rows,matrix

    def values(self,value,*,encoded=False,smooth=True):
        return self._evaluate(value,encoded=encoded,smooth=smooth,jacobian=False)[0]

    def postcheck(self,value):
        raw,_,raw_pairs=self._evaluate(value,smooth=False,jacobian=False,original_pairs=True)
        encoded,_,encoded_pairs=self._evaluate(value,encoded=True,smooth=False,jacobian=False,original_pairs=True)
        passed=all(np.all(a>=0) for a in (raw,encoded,raw_pairs,encoded_pairs))
        return dict(raw_rows=raw,encoded_rows=encoded,raw_pair_rows=raw_pairs,encoded_pair_rows=encoded_pairs,
            declared_conditions_pass=bool(passed),original_selected=True,quality_approved=False,release_approved=False)

    def controls(self,side,value):
        if type(side) is not int or side not in (0,1):raise ValueError('Explicit left0 or right1 actor index required')
        value=self._value(value);self.check_binding(value)
        if np.any(np.linalg.norm(value.reshape(-1,3),axis=1)>1):raise ValueError('Every proposed native vector must fit its original unit ball')
        mapper=self._samples[0][1][side][0];result=mapper.seed.copy();local=value[slice(*self._offsets[side])]
        for (key,node),vector in zip(mapper.pairs,local.reshape(-1,3)):result[key,mapper.nodes.index(node)]=vector
        frozen=self._specs[side]['frozen_keys'];np.testing.assert_array_equal(result[frozen],mapper.seed[frozen]);return result
