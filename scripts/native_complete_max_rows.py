"""Bounded streaming maxima of complete scalar violation populations.

Exact grouped margins are equivalent to every supplied violation <=0. Smooth
rows are stronger search guidance, never an infeasibility or motion approval.
Callers bind the meaning, source and complete row partition of every group.
"""
import copy
import hashlib
import re
import numpy as np

MAXIMUM_ROWS=2000000
MAXIMUM_GROUPS=512
MAXIMUM_COLUMNS=768
MAXIMUM_CHUNK_ROWS=16384
MAXIMUM_JACOBIAN_BYTES=64*1024**2


class CompleteMaxRows:
    def __init__(self,groups,*,derivative_columns=0,temperature=1e-5,
                 maximum_chunk_rows=4096,maximum_jacobian_bytes=MAXIMUM_JACOBIAN_BYTES):
        if not isinstance(groups,list) or not 1<=len(groups)<=MAXIMUM_GROUPS:
            raise ValueError('Complete nonempty bounded group partition required')
        if type(derivative_columns) is not int or not 0<=derivative_columns<=MAXIMUM_COLUMNS:
            raise ValueError('Explicit complete derivative-column count required')
        if type(temperature) not in (int,float) or not np.isfinite(temperature) or not 1e-9<=temperature<=.1:
            raise ValueError('Finite normalized temperature in [1e-9,.1] required')
        for value,limit in [(maximum_chunk_rows,MAXIMUM_CHUNK_ROWS),(maximum_jacobian_bytes,MAXIMUM_JACOBIAN_BYTES)]:
            if type(value) is not int or not 1<=value<=limit:raise ValueError('Bounded complete chunk and Jacobian budgets required')
        copied=[];identifiers=set();total=0
        for group in groups:
            if (not isinstance(group,dict) or set(group)!={'id','rows'} or not isinstance(group['id'],str)
                    or not re.fullmatch(r'[A-Za-z0-9_.:/-]{1,128}',group['id']) or group['id'] in identifiers
                    or type(group['rows']) is not int or not 1<=group['rows']<=MAXIMUM_ROWS):
                raise ValueError('Distinct bounded group IDs and complete positive row counts required')
            copied.append((group['id'],group['rows']));identifiers.add(group['id']);total+=group['rows']
        if total>MAXIMUM_ROWS or len(copied)*derivative_columns*8>maximum_jacobian_bytes:
            raise ValueError('Complete total-row or grouped-Jacobian budget exceeded')
        self._groups=tuple(copied);self._columns=derivative_columns;self._temperature=float(temperature)
        self._chunk_rows=maximum_chunk_rows;self._maximum_bytes=maximum_jacobian_bytes;self._total=total
        self._seen=[0]*len(copied);self._max=[None]*len(copied);self._mass=np.zeros(len(copied));self._worst=[None]*len(copied)
        self._failed=[0]*len(copied);self._gradient=np.zeros((len(copied),derivative_columns));self._digests=[hashlib.sha256() for _ in copied]
        self._closed=False

    def append(self,group,start,violations,*,jacobian=None):
        if self._closed:raise ValueError('Completed partition is closed')
        if type(group) is not int or not 0<=group<len(self._groups) or type(start) is not int or start!=self._seen[group]:
            raise ValueError('Exact next row offset in an existing declared group required')
        values=np.asarray(violations)
        if (values.dtype.kind not in 'fiu' or values.dtype.itemsize>8 or values.ndim!=1 or not 1<=len(values)<=self._chunk_rows
                or start+len(values)>self._groups[group][1]):
            raise ValueError('Complete bounded finite violation chunk within declared row count required')
        values=values.astype(float,copy=True)
        if not np.isfinite(values).all() or np.any(np.abs(values)>1e6):raise ValueError('Finite violation values within the declared numeric range required')
        if self._columns:
            derivative=np.asarray(jacobian)
            if (derivative.dtype.kind not in 'fiu' or derivative.dtype.itemsize>8 or derivative.shape!=(len(values),self._columns)
                    or derivative.size*8>self._maximum_bytes or not np.isfinite(derivative).all()):
                raise ValueError('Every finite declared derivative column and complete chunk budget required')
            derivative=derivative.astype(float,copy=True)
            if not np.isfinite(derivative).all():raise ValueError('Finite Float64 derivatives required')
        elif jacobian is not None:raise ValueError('Value-only mode does not accept or invent derivatives')
        index=int(np.argmax(values));peak=float(values[index]);previous=self._max[group]
        maximum=peak if previous is None else max(previous,peak)
        with np.errstate(under='ignore',over='ignore',invalid='ignore'):
            factor=0. if previous is None else float(np.exp((previous-maximum)/self._temperature))
            weights=np.exp((values-maximum)/self._temperature);mass=self._mass[group]*factor+float(weights.sum())
            gradient=self._gradient[group]*factor+(weights@derivative if self._columns else np.empty(0))
        if not np.isfinite(mass) or mass<=0 or not np.isfinite(gradient).all():
            raise ValueError('Nonfinite complete streaming aggregate; chunk was not committed')
        # Commit only after complete validation/calculation. Every original
        # value is counted and hashed, including negligible smooth weights.
        self._digests[group].update(values.astype('<f8',copy=False).tobytes())
        self._seen[group]+=len(values);self._max[group]=maximum;self._mass[group]=mass;self._gradient[group]=gradient
        if previous is None or peak>previous:self._worst[group]=start+index
        self._failed[group]+=int(np.count_nonzero(values>0))

    def finalize(self):
        if any(seen!=count for seen,(identifier,count) in zip(self._seen,self._groups)):
            raise ValueError('Incomplete original row population; no aggregate result')
        exact=-np.array(self._max,dtype=float)
        smooth=exact-self._temperature*np.log(self._mass)
        derivative=-self._gradient/self._mass[:,None] if self._columns else None
        if not np.isfinite(smooth).all() or derivative is not None and not np.isfinite(derivative).all():
            raise ValueError('Nonfinite complete grouped rows')
        self._closed=True
        groups=[dict(id=identifier,rows=count,rows_seen=seen,failed_rows=failed,worst_row=worst,values_sha256=digest.hexdigest())
                for (identifier,count),seen,failed,worst,digest in zip(self._groups,self._seen,self._failed,self._worst,self._digests)]
        return dict(exact_margins=exact,smooth_margins=smooth,smooth_jacobian=derivative,
            maximum_smoothing_error=self._temperature*np.log([count for identifier,count in self._groups]),
            report=copy.deepcopy(dict(schema='strep-native-complete-max-rows-v1',groups=groups,total_original_rows=self._total,
                derivative_columns=self._columns,grouped_jacobian_bytes=len(groups)*self._columns*8,
                maximum_jacobian_bytes=self._maximum_bytes,temperature=self._temperature,value_encoding='Float64 little endian',
                complete_original_population=True,failed_original_rows=sum(self._failed),failed_exact_groups=int(np.count_nonzero(exact<0)),
                original_scalar_conditions_pass=not any(self._failed),quality_approved=False,release_approved=False,
                scope='Complete ordered supplied scalar groups only; exact margins retain every original inequality. Smooth guidance may fail while exact conditions pass. No source/semantic binding, inferred groups, exact-max derivative, optimization or motion approval.')))
