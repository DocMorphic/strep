"""Complete native-basis pose rows and world derivatives, original epoch retained.

Raw native-key balls are available separately in complete bounded chunks.
Encoded mode is value-only interpolation, not independent saved-file approval.
The caller owns complete clocks, source file receipts, scene/mesh and release checks.
"""
import copy,hashlib
import numpy as np
from native_key_basis import NativeKeyBasis
from native_key_pose_map import KeyPoseMap

MAXIMUM_BYTES=64*1024**2
MAP_ARRAYS=('clock','seed','caps','source','local','track_ids','original_quaternions','fixed_quaternions','bracket','initial')


def digest(value):return hashlib.sha256(np.asarray(value,dtype='<f8').tobytes()).hexdigest()


def equal(a,b):
    a=np.asarray(a);return a.shape==b.shape and a.dtype==b.dtype and a.tobytes()==b.tobytes()


class BasisPoseRows:
    def __init__(self,mapper,basis,world_caps_m,*,maximum_jacobian_bytes=MAXIMUM_BYTES,maximum_working_bytes=MAXIMUM_BYTES):
        if not isinstance(mapper,KeyPoseMap) or not isinstance(basis,NativeKeyBasis):raise ValueError('Original native pose map and complete declared key basis required')
        for value in [maximum_jacobian_bytes,maximum_working_bytes]:
            if type(value) is not int or not 1<=value<=MAXIMUM_BYTES:raise ValueError('Explicit bounded complete matrix/working budgets required')
        mapper._check();model=mapper.model;report=basis.report;columns=basis.size;rows=len(mapper.nodes)+len(model.rig.joints)
        expected=tuple((int(key),node) for key in mapper.bracket for node in mapper.nodes)
        parameters=tuple((key,node,axis) for key in report['variable_knots'] for node in mapper.nodes for axis in range(3))
        if (mapper.pairs!=expected or basis.parameters!=parameters or report['native_keys']!=len(mapper.clock)
                or report['clock_sha256']!=digest(mapper.clock) or report['seed_sha256']!=digest(mapper.seed)
                or report['modeled_nodes']!=len(mapper.nodes) or model.maximum_derivative_controls<model.size):
            raise ValueError('Every original bracket/node pair, matching seed/clock/node order and complete pose derivative budget required')
        caps=np.asarray(world_caps_m);joints=np.asarray(model.rig.joints)
        if (caps.dtype.kind not in 'fiu' or caps.dtype.itemsize>8 or caps.shape!=(len(joints),) or not np.isfinite(caps).all() or np.any(caps<1e-6) or np.any(caps>1)
                or joints.ndim!=1 or not len(joints) or joints.dtype.kind not in 'iu' or len(np.unique(joints))!=len(joints)
                or np.any(joints<0) or np.any(joints>=len(model.source))):raise ValueError('Every original distinct joint and positive finite source-relative band required')
        n=len(model.source);d=model.size;e=mapper.size;m=len(mapper.nodes);j=len(joints)
        products=[rows*columns,n*16*columns,n*16*d,d*columns,e*columns,d*e]
        if max(products)*8>maximum_jacobian_bytes:raise ValueError('Complete pose/world/chain matrices exceed budget before pose allocation')
        model_arrays=self._model_arrays(model)
        binding=sum(np.asarray(getattr(mapper,k)).nbytes for k in MAP_ARRAYS)+sum(np.asarray(v).nbytes for v in model_arrays.values())
        basis_bytes=mapper.seed.nbytes+mapper.clock.nbytes+len(mapper.clock)*len(report['variable_knots'])*8
        working=binding+basis_bytes+(2*n*16*d+n*16*columns+2*rows*columns+3*j*columns+d*columns+e*columns+d*e+n*16+6*d)*8
        if working>maximum_working_bytes:raise ValueError('Complete bound snapshots and pose derivative workspace exceed budget')
        self._mapper=mapper;self._model=model;self._basis=copy.deepcopy(basis);self._caps=caps.astype(float,copy=True);self._joints=joints.copy();self._columns=columns
        self._binding_bytes=binding+basis_bytes;self._maximum_jacobian_bytes=maximum_jacobian_bytes;self._maximum_working_bytes=maximum_working_bytes
        self._map={k:np.asarray(getattr(mapper,k)).copy() for k in MAP_ARRAYS};self._state={k:np.asarray(v).copy() for k,v in model_arrays.items()}
        self._inverse=mapper.original_inverse.as_quat().copy();self._scalars=(mapper.time_s,mapper.size,mapper.step,mapper.maximum_bytes,mapper.duration,mapper.pose_derivative_limit,mapper.nodes,mapper.pairs,mapper.dependent)
        for value in [self._caps,self._joints,self._inverse,*self._map.values(),*self._state.values()]:value.setflags(write=False)
        self._report=dict(schema='strep-native-basis-pose-rows-v1',time_s=mapper.time_s,rows=rows,rotation_rows=m,joint_rows=j,columns=columns,
            rotation_nodes=list(mapper.nodes),world_joints=joints.tolist(),rotation_caps_sha256=digest(mapper.caps),world_caps_sha256=digest(self._caps),
            source_frame_sha256=digest(mapper.source),source_curves_sha256=digest(mapper.original_quaternions),
            native_keys=len(mapper.clock),native_rows=len(mapper.clock)*m,native_chunk_order='native key, declared node',pose_row_order='all declared interpolated rotation balls, then all original joints',
            complete_world_nodes=n,world_jacobian_bytes=n*16*columns*8,pose_jacobian_bytes=rows*columns*8,estimated_owned_array_bytes=working,
            maximum_jacobian_bytes=maximum_jacobian_bytes,maximum_working_bytes=maximum_working_bytes,basis=report,
            encoded_derivatives=False,original_selected=True,quality_approved=False,release_approved=False,
            scope='Complete original-bound pose rotations/joint bands and raw native-basis chunks. World Jacobian retains all supplied basis columns without full-mesh skin derivatives. Encoded mode is value-only interpolation, not saved-file validation. Caller binds source files, complete observation/native clocks, scene/surface/rates/engine/human checks; no optimization, selection or feasibility claim. Array admission is not a process RSS guarantee; use a guarded worker.')

    @staticmethod
    def _model_arrays(model):
        return dict(parents=model.rig.parents,joints=model.rig.joints,order=model.order,affected=model.affected,rotations=model.rotations,scales=model.scales)

    @property
    def report(self):return copy.deepcopy(self._report)

    @property
    def columns(self):return self._columns

    def _check(self):
        mapper=self._mapper;mapper._check()
        scalars=(mapper.time_s,mapper.size,mapper.step,mapper.maximum_bytes,mapper.duration,mapper.pose_derivative_limit,mapper.nodes,mapper.pairs,mapper.dependent)
        if mapper.model is not self._model or scalars!=self._scalars or not equal(mapper.original_inverse.as_quat(),self._inverse):raise ValueError('Bound source pose/map context changed')
        if any(not equal(getattr(mapper,k),v) for k,v in self._map.items()) or any(not equal(self._model_arrays(self._model)[k],v) for k,v in self._state.items()):raise ValueError('Bound original curve, hierarchy, joints or local transform changed')

    def native_chunk(self,value,start,count,*,jacobian=True):
        if type(jacobian) is not bool:raise ValueError('Explicit derivative mode required')
        if type(start) is not int or type(count) is not int or not 0<=start<self._report['native_keys'] or not 1<=count<=64 or start+count>self._report['native_keys']:raise ValueError('Complete bounded consecutive native-key chunk required')
        rows=count*self._report['rotation_rows'];coefficients=3*rows
        if jacobian and coefficients*self.columns*8>self._maximum_jacobian_bytes:raise ValueError('Complete native chunk Jacobian exceeds adapter budget')
        working=self._binding_bytes+8*(coefficients+rows+self.columns+((coefficients+rows)*self.columns if jacobian else 0))
        if working>self._maximum_working_bytes:raise ValueError('Complete native chunk workspace exceeds adapter budget')
        self._check();result=self._basis.native_chunk(value,start,count,jacobian=jacobian);self._check();return result

    def export_coefficients(self,value):
        self._check()
        if self._binding_bytes+self._map['seed'].nbytes>self._maximum_working_bytes:raise ValueError('Complete original-clock export workspace exceeds budget')
        result=self._basis.export_coefficients(value);self._check();return result

    def evaluate(self,value,*,jacobian=True,encoded=False):
        if type(jacobian) is not bool or type(encoded) is not bool or (encoded and jacobian):raise ValueError('Explicit raw derivative mode or value-only encoded mode required')
        self._check();mapper=self._mapper;model=self._model
        endpoints,basis_jac=self._basis.endpoint_map(value,mapper.bracket.tolist(),jacobian=jacobian)
        if jacobian:
            full,local=mapper.evaluate(endpoints.ravel());mapping=local@basis_jac
            world,local_world=model._forward(full,list(range(model.size)))
            world_jac=(local_world.reshape(-1,model.size)@mapping).reshape(world.shape+(self.columns,))
        else:
            full=mapper.controls(endpoints.ravel(),quantized=encoded);world=model._forward(full,[])[0];world_jac=None;mapping=None
        balls=full.reshape(-1,3);delta=world[self._joints,:3,3]-self._map['source'][self._joints,:3,3]
        rows=np.r_[1-np.sum(balls*balls,axis=1),1-np.sum(delta*delta,axis=1)/self._caps**2];matrix=None
        if jacobian:
            matrix=np.vstack([-2*np.einsum('ri,ric->rc',balls,mapping.reshape(len(balls),3,self.columns)),
                -2*np.einsum('ji,jic->jc',delta,world_jac[self._joints,:3,3,:])/self._caps[:,None]**2])
        if rows.shape!=(self._report['rows'],) or not np.isfinite(rows).all() or not np.isfinite(world).all() or (jacobian and (matrix.shape!=(len(rows),self.columns) or not np.isfinite(matrix).all() or not np.isfinite(world_jac).all())):raise ValueError('Incomplete or nonfinite complete pose output')
        self._check()
        return dict(margins=rows,jacobian=matrix,world=world,world_jacobian=world_jac,full_controls=full,encoded=encoded,
            original_selected=True,quality_approved=False,release_approved=False)
