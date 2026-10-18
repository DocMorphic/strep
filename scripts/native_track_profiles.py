"""Original-relative temporal track directions with complete pose derivatives.

One amplitude per declared node scales its supplied complete temporal direction.
This is a search subspace, never a new source epoch or authoring permission.
Native balls and original raw/saved/scene acceptance remain caller obligations.
"""
import copy
import hashlib
import numpy as np
from native_key_basis import NativeKeyBasis
from native_key_pose_map import KeyPoseMap
from native_basis_pose_norm_rows import BasisPoseNormRows

MAXIMUM_BYTES=64*1024**2
digest=lambda a:hashlib.sha256(np.asarray(a,dtype='<f8').tobytes()).hexdigest()


class NativeTrackProfiles:
    def __init__(self,clock,nodes,seed_controls,directions,editable_keys,frozen_keys,*,maximum_bytes=MAXIMUM_BYTES):
        t=np.asarray(clock);s=np.asarray(seed_controls);d=np.asarray(directions)
        if (type(maximum_bytes) is not int or not 1<=maximum_bytes<=MAXIMUM_BYTES
                or not isinstance(nodes,list) or not 1<=len(nodes)<=256
                or any(type(n) is not int or n<0 for n in nodes) or len(set(nodes))!=len(nodes)
                or t.ndim!=1 or not 3<=len(t)<=4096 or t.dtype.kind not in 'fiu' or t.dtype.itemsize>8
                or not np.isfinite(t).all() or np.any(np.diff(t.astype(float))<=0)
                or not np.isfinite(float(t[-1])-float(t[0]))):
            raise ValueError('Complete finite original clock, distinct declared nodes and bounded storage required')
        shape=(len(t),len(nodes),3)
        for a in [s,d]:
            if a.shape!=shape or a.dtype.kind not in 'fiu' or a.dtype.itemsize>8 or not np.isfinite(a).all():
                raise ValueError('Complete matching finite seed and temporal-direction grids required')
        owned=(len(t)+2*np.prod(shape))*8
        if owned+3*np.prod(shape)*8>maximum_bytes:
            raise ValueError('Complete owned grids and full export exceed storage budget before copying')
        if np.any(np.abs(s)>1) or np.any(np.sum(s.astype(float)**2,axis=2)>1) or np.any(np.abs(d)>1):
            raise ValueError('Original seed must satisfy native balls; temporal directions must be bounded')
        for keys in [editable_keys,frozen_keys]:
            if (not isinstance(keys,list) or not keys or any(type(k) is not int or not 0<=k<len(t) for k in keys)
                    or keys!=sorted(set(keys))):
                raise ValueError('Explicit sorted distinct existing editable and frozen native keys required')
        if not {0,len(t)-1}.issubset(frozen_keys) or set(editable_keys)&set(frozen_keys):
            raise ValueError('Original endpoints frozen; editable and frozen domains must be disjoint')
        outside=np.ones(len(t),bool);outside[editable_keys]=False
        if np.any(d[outside]):raise ValueError('Direction changes an undeclared or frozen key; no support is discarded')
        self._clock=t.astype(float,copy=True);self._seed=s.astype(float,copy=True);self._direction=d.astype(float,copy=True)
        self._nodes=tuple(nodes);self._editable=tuple(editable_keys);self._frozen=tuple(frozen_keys)
        self._maximum_bytes=maximum_bytes;self._owned=int(owned);self.size=len(nodes)
        for a in [self._clock,self._seed,self._direction]:a.setflags(write=False)
        self._report=dict(schema='strep-native-track-profiles-v1',native_keys=len(t),modeled_nodes=len(nodes),variables=self.size,
            nodes=nodes.copy(),editable_keys=editable_keys.copy(),frozen_keys=frozen_keys.copy(),
            clock_sha256=digest(self._clock),seed_sha256=digest(self._seed),direction_sha256=digest(self._direction),
            owned_array_bytes=self._owned,maximum_bytes=maximum_bytes,parameter_order='one amplitude per declared node, including zero profiles',
            original_selected=True,quality_approved=False,release_approved=False,
            scope='Complete original-relative cumulative controls plus supplied temporal directions. Amplitudes are search coordinates, not new permissions. No clipping, quaternion/source rebasing, solver, saved-file or quality approval.')

    @property
    def report(self):return copy.deepcopy(self._report)

    def _value(self,value):
        v=np.asarray(value)
        if v.dtype.kind not in 'fiu' or v.dtype.itemsize>8 or v.shape!=(self.size,) or not np.isfinite(v).all() or np.any(np.abs(v)>1):
            raise ValueError('Complete finite profile amplitudes within the declared [-1,1] search box required')
        return v.astype(float,copy=True)

    def coefficients(self,value):
        v=self._value(value)
        result=self._seed.copy()
        # Inactive keys/components, including signed zero, retain original bytes.
        delta=self._direction*v[None,:,None]
        np.add(self._seed,delta,out=result,where=delta!=0)
        return result

    def endpoint_map(self,value,keys,*,jacobian=True):
        v=self._value(value)
        if (type(jacobian) is not bool or not isinstance(keys,list) or not 1<=len(keys)<=64
                or any(type(k) is not int or not 0<=k<len(self._clock) for k in keys) or len(set(keys))!=len(keys)):
            raise ValueError('Complete distinct bounded native keys and explicit derivative mode required')
        count=len(keys)*self.size*3; extra=8*(4*count+(count*self.size if jacobian else 0)+self.size)
        if self._owned+extra>self._maximum_bytes:raise ValueError('Complete endpoint map exceeds storage budget; no keys/columns removed')
        result=self._seed[keys].copy();direction=self._direction[keys]
        delta=direction*v[None,:,None]
        np.add(result,delta,out=result,where=delta!=0)
        matrix=None
        if jacobian:
            matrix=np.zeros((len(keys),self.size,3,self.size))
            for j in range(self.size):matrix[:,j,:,j]=direction[:,j,:]
            matrix=matrix.reshape(count,self.size)
        return result,matrix

    def native_chunk(self,value,start,count,*,jacobian=True):
        if type(start) is not int or type(count) is not int or not 0<=start<len(self._clock) or not 1<=count<=64 or start+count>len(self._clock):
            raise ValueError('Complete bounded consecutive native-key chunk required')
        rows=count*self.size
        extra=8*(9*rows+(4*rows*self.size if jacobian else 0)+self.size+4*rows)
        if self._owned+extra>self._maximum_bytes:raise ValueError('Complete native rows and derivatives exceed storage budget')
        c,j=self.endpoint_map(value,list(range(start,start+count)),jacobian=jacobian)
        rows=1-np.sum(c*c,axis=2).ravel()
        return rows,None if j is None else -2*np.einsum('ri,ric->rc',c.reshape(-1,3),j.reshape(-1,3,self.size))

    def export_coefficients(self,value):
        c=self.coefficients(value)
        if np.any(1-np.sum(c*c,axis=2)<0):raise ValueError('Proposed native balls fail; no projection or clipping applied')
        return c


class TrackProfilePoseRows:
    """Compose a qualified bracket-pose adapter with all profile columns.

    Local key variables only transport the exact profile endpoints at this time.
    They do not replace the complete profile's domain or native-bound checks.
    """
    def __init__(self,mapper,profiles,world_caps_m,*,maximum_bytes=MAXIMUM_BYTES):
        if not isinstance(mapper,KeyPoseMap) or not isinstance(profiles,NativeTrackProfiles):
            raise ValueError('Original pose map and complete declared track profiles required')
        if type(maximum_bytes) is not int or not 1<=maximum_bytes<=MAXIMUM_BYTES:raise ValueError('Complete bounded adapter storage required')
        r=profiles.report
        if (r['clock_sha256']!=digest(mapper.clock) or r['seed_sha256']!=digest(mapper.seed)
                or tuple(r['nodes'])!=mapper.nodes or mapper.pairs!=tuple((int(k),n) for k in mapper.bracket for n in mapper.nodes)):
            raise ValueError('Original clock, seed, every bracket/node pair and node order must match')
        self._profiles=copy.deepcopy(profiles);self._keys=[int(k) for k in mapper.bracket];self.columns=profiles.size
        frozen=r['frozen_keys'];knots=sorted(set(frozen+self._keys))
        if not set(knots)-set(frozen):knots=sorted(set(knots+[r['editable_keys'][0]]))
        local=NativeKeyBasis(mapper.clock,list(mapper.nodes),mapper.seed,knots,frozen,maximum_jacobian_bytes=maximum_bytes)
        inner=BasisPoseNormRows(mapper,local,world_caps_m,maximum_jacobian_bytes=maximum_bytes,maximum_working_bytes=maximum_bytes)
        rows=inner.report['rows'];n=len(mapper.model.source);a=local.size;b=self.columns
        extra=8*(a*b+4*rows*b+n*16*b+3*a+6*rows+(4*rows+mapper.model.size)*a)+r['owned_array_bytes']
        if inner.report['estimated_owned_array_bytes']+extra>maximum_bytes:
            raise ValueError('Complete pose and profile chain workspace exceeds budget; no rows/columns removed')
        self._inner=inner;self._local=local;self._maximum_bytes=maximum_bytes
        self._report=dict(schema='strep-native-track-profile-pose-rows-v1',rows=rows,columns=b,local_transport_columns=a,
            time_s=mapper.time_s,profiles=r,all_rows_and_columns_retained=True,estimated_owned_array_bytes=inner.report['estimated_owned_array_bytes']+extra,
            original_selected=True,quality_approved=False,release_approved=False,
            scope='Exact complete profile endpoint chain through original qualified key/pose/norm adapter. Local transport knots grant no edit permission. Encoded mode is value-only, not saved-file approval. Full native/raw/saved/scene gates remain external.')

    @property
    def report(self):return copy.deepcopy(self._report)

    def evaluate_vectors(self,value,*,jacobian=True,encoded=False):
        if type(jacobian) is not bool or type(encoded) is not bool or jacobian and encoded:
            raise ValueError('Explicit raw derivatives or value-only encoded mode required')
        v=self._profiles._value(value);p=self._profiles;point=[];chain=np.zeros((self._local.size,self.columns)) if jacobian else None
        for i,(key,node,axis) in enumerate(self._local.parameters):
            j=p._nodes.index(node);d=p._direction[key,j,axis];point.append(d*v[j])
            if jacobian:chain[i,j]=d
        result=self._inner.evaluate_vectors(np.asarray(point),jacobian=jacobian,encoded=encoded)
        if jacobian:
            result['jacobian']=result['jacobian']@chain
            shape=result['world_jacobian'].shape
            result['world_jacobian']=(result['world_jacobian'].reshape(-1,self._local.size)@chain).reshape(shape[:-1]+(self.columns,))
        result['report']=dict(self.report,encoded=encoded,canonical_margins_byte_identical=True)
        return result
