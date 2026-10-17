"""Complete declared native/pose populations, streamed without row or column loss.

Actor-local raw guidance only. Callers bind the authoritative observation list,
source files and encoded/pair/rate/mesh/engine/human acceptance separately.
"""
import copy,hashlib
import numpy as np
from native_basis_pose_rows import BasisPoseRows
from native_complete_max_rows import CompleteMaxRows,MAXIMUM_GROUPS

MAXIMUM_BYTES=64*1024**2
MAXIMUM_ROWS=2000000
MAXIMUM_OBSERVATIONS=4096
COMPATIBLE=('columns','rotation_nodes','world_joints','rotation_caps_sha256','source_curves_sha256','native_keys','native_rows','complete_world_nodes')
BASIS_BINDING=('native_keys','modeled_nodes','variable_knots','frozen_keys','knots','variables','clock_sha256','seed_sha256','parameter_order')


def sampler_digest(actor):
    sampler=actor['sampler'];h=hashlib.sha256();h.update(float(sampler.duration).hex().encode())
    for node,path,clock,values,mode in sampler.channels:
        h.update(repr((node,path,mode)).encode())
        for value in [clock,values]:
            a=np.asarray(value)
            if a.dtype.kind not in 'fiu' or a.dtype.itemsize>8 or not np.isfinite(a).all():raise ValueError('Finite complete source channels required')
            h.update(repr((a.dtype.str,a.shape)).encode());h.update(a.tobytes())
    return h.hexdigest()


class BasisPosePopulation:
    def __init__(self,native_helper,pose_helpers,*,temperature=1e-5,maximum_jacobian_bytes=MAXIMUM_BYTES,maximum_working_bytes=MAXIMUM_BYTES):
        if not isinstance(native_helper,BasisPoseRows) or not isinstance(pose_helpers,list) or not 1<=len(pose_helpers)<=MAXIMUM_OBSERVATIONS or any(not isinstance(h,BasisPoseRows) for h in pose_helpers):raise ValueError('One complete native domain and every declared pose helper required')
        for budget in [maximum_jacobian_bytes,maximum_working_bytes]:
            if type(budget) is not int or not 1<=budget<=MAXIMUM_BYTES:raise ValueError('Explicit complete matrix and owned-array budgets required')
        if type(temperature) not in (int,float) or not np.isfinite(temperature) or not 1e-9<=temperature<=.1:raise ValueError('Finite bounded normalized temperature required')
        native_helper._check();reference=native_helper.report;actor=native_helper._model.actor
        reports=[]
        for helper in pose_helpers:
            helper._check();r=helper.report
            if helper._model.actor is not actor or any(r[k]!=reference[k] for k in COMPATIBLE) or any(r['basis'][k]!=reference['basis'][k] for k in BASIS_BINDING):raise ValueError('One unchanged actor, native source/clock/basis/node order and rotation caps required')
            reports.append(r)
        columns=native_helper.columns;groups=[];cursor=0
        for key in range(reference['native_keys']):
            count=reference['rotation_rows'];groups.append(dict(id='n'+str(key),kind='native',key=key,observation=None,rows=count,first=cursor,last=cursor+count));cursor+=count
        for ordinal,r in enumerate(reports):
            for kind,count in [('rotation',r['rotation_rows']),('joint',r['joint_rows'])]:
                groups.append(dict(id='p'+str(ordinal)+'-'+kind,kind=kind,key=None,observation=ordinal,rows=count,first=cursor,last=cursor+count));cursor+=count
        jacobian_bytes=len(groups)*columns*8;child=max(r['estimated_owned_array_bytes'] for r in [reference,*reports]);working=child+4*jacobian_bytes+2*cursor*8+4*reference['native_rows']*8+len(groups)*20*8
        if cursor>MAXIMUM_ROWS or jacobian_bytes>maximum_jacobian_bytes or working>maximum_working_bytes:raise ValueError('Complete declared population exceeds row/Jacobian/array budget; no observations or columns discarded')
        self._native=native_helper;self._poses=tuple(pose_helpers);self._actor=actor;self._reports=[reference,*reports];self._source=sampler_digest(actor)
        self._groups=groups;self._columns=columns;self._rows=cursor;self._temperature=float(temperature);self._maximum_bytes=maximum_jacobian_bytes
        self._report=dict(schema='strep-native-basis-pose-population-v1',raw_rows=cursor,groups=len(groups),columns=columns,
            native_rows=reference['native_rows'],pose_rows=cursor-reference['native_rows'],native_keys=reference['native_keys'],pose_observations=len(reports),
            observation_times_s=[r['time_s'] for r in reports],observation_world_caps_sha256=[r['world_caps_sha256'] for r in reports],
            row_order='Complete native key/node grid, then caller-ordered poses: all interpolated rotation balls followed by all original joint bands; duplicates retained',
            backend_partitions=(len(groups)+MAXIMUM_GROUPS-1)//MAXIMUM_GROUPS,grouped_jacobian_bytes=jacobian_bytes,estimated_owned_array_bytes=working,
            native_scalar_anchor='Every raw ball from the complete declared coefficient grid; chunk arithmetic compared numerically, never used to change the physical zero threshold',
            maximum_jacobian_bytes=maximum_jacobian_bytes,maximum_working_bytes=maximum_working_bytes,temperature=self._temperature,source_channels_sha256=self._source,
            original_selected=True,quality_approved=False,release_approved=False,
            scope='Every supplied actor-local native/pose inequality and every declared basis column. Exact grouped margins preserve all original signs; smooth rows are stronger guidance, not infeasibility. Source/basis/rotation units shared; explicit joint bands may vary by observation. Caller binds complete authoritative observations and source files. Encoded motion, pairs, rates, geometry, engine and human acceptance remain separate. Array admission excludes caller-owned input helpers and is not an RSS guarantee; use a guarded worker.')

    @property
    def report(self):return copy.deepcopy(self._report)

    @property
    def layout(self):return copy.deepcopy(self._groups)

    def _check(self):
        if sampler_digest(self._actor)!=self._source:raise ValueError('Original full source channel population changed')
        for helper,report in zip((self._native,*self._poses),self._reports):
            helper._check()
            if helper._model.actor is not self._actor or helper.report!=report:raise ValueError('Bound original helper/domain/observation changed')

    def evaluate(self,value,*,jacobian=True):
        if type(jacobian) is not bool:raise ValueError('Explicit raw derivative mode required')
        raw=np.asarray(value)
        if raw.dtype.kind not in 'fiu' or raw.dtype.itemsize>8 or raw.shape!=(self._columns,) or not np.isfinite(raw).all():raise ValueError('Complete finite declared basis point required')
        point=raw.astype(float,copy=True)
        if np.any(np.abs(point)>1):raise ValueError('Complete finite declared basis point within its original box required')
        self._check();margins=np.empty(self._rows);reducers=[]
        coefficients=self._native._basis.coefficients(point);native_margins=1-np.sum(coefficients*coefficients,axis=2);maximum_native_value_difference=0.
        for start in range(0,len(self._groups),MAXIMUM_GROUPS):
            partition=[dict(id=g['id'],rows=g['rows']) for g in self._groups[start:start+MAXIMUM_GROUPS]]
            reducers.append(CompleteMaxRows(partition,derivative_columns=self._columns if jacobian else 0,temperature=self._temperature,maximum_jacobian_bytes=self._maximum_bytes))
        cursor=0
        def feed(index,values,matrix):
            group=self._groups[index];values=np.asarray(values)
            if values.shape!=(group['rows'],) or not np.isfinite(values).all() or (jacobian and (matrix is None or np.asarray(matrix).shape!=(len(values),self._columns))):raise ValueError('Complete original group and every derivative column required')
            margins[group['first']:group['last']]=values
            for start in range(0,len(values),4096):
                reducers[index//MAXIMUM_GROUPS].append(index%MAXIMUM_GROUPS,start,-values[start:start+4096],jacobian=-matrix[start:start+4096] if jacobian else None)
        for key in range(self._reports[0]['native_keys']):
            rows,matrix=self._native.native_chunk(point,key,1,jacobian=jacobian);difference=float(np.abs(rows-native_margins[key]).max());maximum_native_value_difference=max(maximum_native_value_difference,difference)
            if difference>2e-12:raise ValueError('Native chunk arithmetic differs from the complete original coefficient grid')
            feed(cursor,native_margins[key],matrix);cursor+=1
        for helper,report in zip(self._poses,self._reports[1:]):
            response=helper.evaluate(point,jacobian=jacobian);rows=response['margins'];matrix=response['jacobian'];split=report['rotation_rows']
            feed(cursor,rows[:split],None if matrix is None else matrix[:split]);cursor+=1
            feed(cursor,rows[split:],None if matrix is None else matrix[split:]);cursor+=1
        if cursor!=len(self._groups):raise ValueError('Incomplete original population; no result')
        finished=[r.finalize() for r in reducers];self._check()
        return dict(original_margins=margins,exact_margins=np.concatenate([r['exact_margins'] for r in finished]),smooth_margins=np.concatenate([r['smooth_margins'] for r in finished]),
            smooth_jacobian=np.vstack([r['smooth_jacobian'] for r in finished]) if jacobian else None,
            maximum_smoothing_error=np.concatenate([r['maximum_smoothing_error'] for r in finished]),
            report=dict(self.report,groups_report=[g for r in finished for g in r['report']['groups']],complete_declared_population=True,
                failed_original_rows=int(np.count_nonzero(margins<0)),failed_exact_groups=sum(r['report']['failed_exact_groups'] for r in finished),
                maximum_native_chunk_value_comparison_difference=maximum_native_value_difference,
                original_scalar_conditions_pass=bool(np.all(margins>=0)),raw_derivatives=jacobian))
