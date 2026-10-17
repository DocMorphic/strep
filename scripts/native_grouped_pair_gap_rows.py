"""Complete grouped directional pair rows, independent of rigs and actions.

Each instance binds one pair of point populations, context, direction and
threshold. Callers retain source/clock/permission bindings, complete physical
postchecks and independent saved-mesh/motion validation. No contact is inferred.
"""
import numpy as np
from native_pair_gap_groups import triangle_gap_groups
from native_region_support_gap import region_support_gap,MAXIMUM_VERTICES
from native_support_gap import triangle_support_gaps

MAXIMUM_JACOBIAN_BYTES=64*1024**2
MAXIMUM_INPUT_JACOBIAN_BYTES=128*1024**2
MAXIMUM_CONTROLS=768


class GroupedPairGapRows:
    def __init__(self,left_triangles,right_triangles,left_vertex_count,
                 right_vertex_count,normal_world,*,minimum_gap_m=2e-5,
                 length_scale_m=.01,temperature_m=1e-5,
                 maximum_jacobian_bytes=MAXIMUM_JACOBIAN_BYTES):
        counts=(left_vertex_count,right_vertex_count)
        if any(type(n) is not int or not 1<=n<=MAXIMUM_VERTICES for n in counts):
            raise ValueError('Complete bounded vertex population counts required')
        normal=np.asarray(normal_world)
        if (normal.dtype.kind not in 'fiu' or normal.shape!=(3,)
                or not np.isfinite(normal).all()
                or np.any(np.abs(normal.astype(float,copy=False))>2)
                or not np.isclose(np.linalg.norm(normal),1.,rtol=0,atol=1e-8)):
            raise ValueError('Explicit finite unit world direction required')
        for value,low,high in [(minimum_gap_m,0.,.1),(length_scale_m,1e-6,1.),(temperature_m,1e-9,.1)]:
            if type(value) not in (int,float) or not low<=value<=high:
                raise ValueError('Finite bounded gap, scale and temperature required')
        if (type(maximum_jacobian_bytes) is not int
                or not 1<=maximum_jacobian_bytes<=MAXIMUM_JACOBIAN_BYTES):
            raise ValueError('Output Jacobian budget may not exceed64MiB')
        grouped=triangle_gap_groups(left_triangles,right_triangles)
        self._triangles=tuple(np.array(v,dtype=np.int64,copy=True) for v in (left_triangles,right_triangles))
        if any(np.any(ids>=count) for ids,count in zip(self._triangles,counts)):
            raise ValueError('Triangle references must belong to the declared populations')
        self._groups=tuple((np.array(g['left_vertices'],dtype=np.int64),np.array(g['right_vertices'],dtype=np.int64)) for g in grouped['groups'])
        self._normal=normal.astype(float,copy=True);self._counts=counts
        self._gap=float(minimum_gap_m);self._scale=float(length_scale_m);self._temperature=float(temperature_m)
        self._maximum_bytes=maximum_jacobian_bytes
        for value in (*self._triangles,self._normal,*(a for g in self._groups for a in g)):value.setflags(write=False)
        self._report=dict(schema='strep-native-grouped-pair-gap-rows-v1',pair_references=grouped['pair_references'],
            pair_references_sha256=grouped['pair_references_sha256'],vertex_relations=grouped['vertex_relations'],
            rows=len(self._groups),left_vertices=counts[0],right_vertices=counts[1],normal_world=tuple(self._normal),
            minimum_gap_m=self._gap,length_scale_m=self._scale,temperature_m=self._temperature,
            maximum_jacobian_bytes=self._maximum_bytes,quality_approved=False,release_approved=False,
            scope='Exact common-context vertex-comparison relation and conservative smooth guidance only; no mesh, motion or contact-intent approval')

    @property
    def report(self):return dict(self._report)

    def _points(self,left,right):
        result=[]
        for value,count in zip((left,right),self._counts):
            raw=np.asarray(value)
            if raw.dtype.kind not in 'fiu' or raw.shape!=(count,3):
                raise ValueError('Complete matching real point populations required')
            array=raw.astype(float,copy=False)
            if not np.isfinite(array).all() or np.any(np.abs(array)>1e6):
                raise ValueError('Finite complete point populations within one million metres required')
            result.append(array)
        return result

    def _derivative(self,value,count):
        if value is None:return None,0
        raw=np.asarray(value)
        if (raw.dtype.kind not in 'fiu' or raw.ndim!=3 or raw.shape[:2]!=(count,3)
                or not 0<=raw.shape[2]<=MAXIMUM_CONTROLS
                or raw.size*8>MAXIMUM_INPUT_JACOBIAN_BYTES):
            raise ValueError('Complete bounded vertex derivatives required; no coordinates discarded')
        array=raw.astype(float,copy=False)
        if not np.isfinite(array).all():raise ValueError('Finite complete vertex derivatives required')
        return array,array.shape[2]

    def evaluate(self,left,right,*,left_jacobian=None,right_jacobian=None,smooth=True):
        if type(smooth) is not bool:raise ValueError('Explicit boolean smooth mode required')
        has_jac=left_jacobian is not None or right_jacobian is not None
        if has_jac and not smooth:raise ValueError('Exact extrema are physical checks, not smooth derivatives')
        points=self._points(left,right)
        data=[self._derivative(v,n) for v,n in zip((left_jacobian,right_jacobian),self._counts)]
        required=len(self._groups)*sum(n for a,n in data)*8
        if required>self._maximum_bytes:
            raise ValueError('Complete grouped Jacobian exceeds declared budget; no groups discarded')
        matrices=[np.zeros((len(self._groups),n)) for a,n in data] if has_jac else [None,None]
        rows=np.empty(len(self._groups))
        for index,ids in enumerate(self._groups):
            result=region_support_gap(points[0][ids[0]],points[1][ids[1]],self._normal,temperature_m=self._temperature)
            rows[index]=(result['smooth_gap_m' if smooth else 'projected_gap_m']-self._gap)/self._scale
            if has_jac:
                for side,name in enumerate(('left','right')):
                    array,size=data[side]
                    if size:matrices[side][index]=np.einsum('vi,vic->c',result[name+'_gradient'],array[ids[side]])/self._scale
        if not np.isfinite(rows).all() or any(m is not None and not np.isfinite(m).all() for m in matrices):
            raise ValueError('Nonfinite grouped rows or derivatives')
        return rows,*matrices

    def exact_pairs(self,left,right):
        a,b=self._points(left,right)
        gaps=triangle_support_gaps(a[self._triangles[0]],b[self._triangles[1]],
            np.tile(self._normal,(len(self._triangles[0]),1)))['projected_gap_m']
        return dict(projected_gaps_m=gaps,passed=bool(np.all(gaps>=self._gap)),
            pair_references=len(gaps),minimum_gap_m=self._gap,quality_approved=False,release_approved=False)
