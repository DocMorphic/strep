"""Explicit bounded temporal basis for original normalized native rotations.

This field changes edit permissions only when a caller declares a new domain.
It never changes source/caps, infers nodes, approves a clip or quantizes a rig.
"""
import copy
import hashlib
import numpy as np

MAXIMUM_CONTROLS=768
MAXIMUM_KEYS=4096
MAXIMUM_NODES=256
MAXIMUM_JACOBIAN_BYTES=64*1024**2


class NativeKeyBasis:
    def __init__(self,clock,nodes,seed_controls,knots,frozen_keys,*,maximum_jacobian_bytes=MAXIMUM_JACOBIAN_BYTES):
        times=np.asarray(clock);seed=np.asarray(seed_controls)
        if (times.dtype.kind not in 'fiu' or times.dtype.itemsize>8 or times.ndim!=1 or not 3<=len(times)<=MAXIMUM_KEYS
                or not np.isfinite(times).all() or np.any(np.diff(times.astype(float))<=0)
                or not isinstance(nodes,list) or not 1<=len(nodes)<=MAXIMUM_NODES or any(type(n) is not int or n<0 for n in nodes) or len(set(nodes))!=len(nodes)
                or seed.dtype.kind not in 'fiu' or seed.dtype.itemsize>8 or seed.shape!=(len(times),len(nodes),3)
                or not np.isfinite(seed).all() or np.any(np.abs(seed.astype(float))>1)):
            raise ValueError('Complete finite original native clock/nodes and source-relative seed grid required')
        seed=seed.astype(float,copy=True);times=times.astype(float,copy=True)
        with np.errstate(over='ignore',invalid='ignore'):
            span=times[-1]-times[0]
        if not np.isfinite(span):raise ValueError('Finite representable original clock span required')
        if np.any(np.sum(seed*seed,axis=2)>1):raise ValueError('Every original seed vector must satisfy its normalized native ball')
        for values,label in [(knots,'knots'),(frozen_keys,'frozen keys')]:
            if not isinstance(values,list) or not values or any(type(k) is not int or not 0<=k<len(times) for k in values) or len(set(values))!=len(values):
                raise ValueError('Distinct explicit existing native '+label+' required')
        if knots!=sorted(knots) or knots[0]!=0 or knots[-1]!=len(times)-1 or not {0,len(times)-1}.issubset(frozen_keys) or not set(frozen_keys).issubset(knots):
            raise ValueError('Original endpoints must be frozen and all frozen keys must be basis knots')
        variable=[key for key in knots if key not in frozen_keys];size=3*len(variable)*len(nodes)
        if not 1<=size<=MAXIMUM_CONTROLS:raise ValueError('Complete declared basis-variable budget exceeded; no nodes/knots dropped')
        if type(maximum_jacobian_bytes) is not int or not 1<=maximum_jacobian_bytes<=MAXIMUM_JACOBIAN_BYTES:raise ValueError('Bounded complete Jacobian budget required')
        weights=np.zeros((len(times),len(variable)));lookup={key:i for i,key in enumerate(variable)}
        for first,last in zip(knots[:-1],knots[1:]):
            fraction=(times[first:last+1]-times[first])/(times[last]-times[first])
            if first in lookup:weights[first:last+1,lookup[first]]=1-fraction
            if last in lookup:weights[first:last+1,lookup[last]]=fraction
        assert np.all(weights>=0) and np.all(weights.sum(axis=1)<=1) and not np.any(weights[frozen_keys])
        self._clock=times;self._nodes=tuple(nodes);self._seed=seed;self._weights=weights
        self._frozen=tuple(frozen_keys);self._knots=tuple(knots);self._variable=tuple(variable);self._maximum_bytes=maximum_jacobian_bytes
        self.size=size
        for array in [self._clock,self._seed,self._weights]:array.setflags(write=False)
        self._report=dict(schema='strep-native-key-basis-v1',native_keys=len(times),modeled_nodes=len(nodes),variable_knots=variable,
            frozen_keys=frozen_keys.copy(),knots=knots.copy(),variables=size,maximum_jacobian_bytes=maximum_jacobian_bytes,
            clock_sha256=hashlib.sha256(times.astype('<f8').tobytes()).hexdigest(),seed_sha256=hashlib.sha256(seed.astype('<f8').tobytes()).hexdigest(),
            parameter_order='variable-knot, declared-node, xyz',source_caps_supplied_by_caller=True,
            original_selected=True,quality_approved=False,release_approved=False)

    @property
    def report(self):return copy.deepcopy(self._report)
    @property
    def parameters(self):return tuple((key,node,axis) for key in self._variable for node in self._nodes for axis in range(3))
    @property
    def weights(self):return self._weights.copy()

    def _value(self,value):
        array=np.asarray(value)
        if array.dtype.kind not in 'fiu' or array.dtype.itemsize>8 or array.shape!=(self.size,) or not np.isfinite(array).all() or np.any(np.abs(array.astype(float))>1):
            raise ValueError('Complete finite declared latent vector within its scalar search box required')
        return array.astype(float,copy=True)

    def _keys(self,keys):
        if not isinstance(keys,list) or not 1<=len(keys)<=64 or any(type(k) is not int or not 0<=k<len(self._clock) for k in keys) or len(set(keys))!=len(keys):
            raise ValueError('Complete distinct bounded native key request required')
        return keys

    def coefficients(self,value):
        value=self._value(value);delta=self._weights@value.reshape(len(self._variable),-1)
        result=self._seed+delta.reshape(self._seed.shape)
        result[list(self._frozen)]=self._seed[list(self._frozen)]
        return result

    def endpoint_map(self,value,keys,*,jacobian=True):
        value=self._value(value);keys=self._keys(keys)
        if type(jacobian) is not bool:raise ValueError('Explicit derivative mode required')
        count=len(keys)*len(self._nodes)*3
        if jacobian and count*self.size*8>self._maximum_bytes:raise ValueError('Complete endpoint Jacobian exceeds budget; no keys/columns discarded')
        weights=self._weights[keys];result=self._seed[keys]+(weights@value.reshape(len(self._variable),-1)).reshape(len(keys),len(self._nodes),3)
        for index,key in enumerate(keys):
            if key in self._frozen:result[index]=self._seed[key]
        matrix=np.kron(weights,np.eye(len(self._nodes)*3)) if jacobian else None
        return result,matrix

    def native_chunk(self,value,start,count,*,jacobian=True):
        if type(start) is not int or type(count) is not int or not 0<=start<len(self._clock) or not 1<=count<=64 or start+count>len(self._clock):
            raise ValueError('Complete bounded consecutive native-key chunk required')
        coefficients,matrix=self.endpoint_map(value,list(range(start,start+count)),jacobian=jacobian)
        rows=1-np.sum(coefficients*coefficients,axis=2).ravel()
        derivative=-2*np.einsum('ri,ric->rc',coefficients.reshape(-1,3),matrix.reshape(-1,3,self.size)) if jacobian else None
        return rows,derivative

    def export_coefficients(self,value):
        result=self.coefficients(value)
        if np.any(1-np.sum(result*result,axis=2)<0):raise ValueError('Native coefficient ball failed; proposal is not clipped')
        return result
