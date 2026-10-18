"""Pull complete mesh features through independent or shared control columns."""
import copy
import numpy as np
from mesh_penetration_gradient import MeshPenetration,_digest


class CoupledMeshJacobian(MeshPenetration):
    def linearize(self,source,target,source_jacobian,target_jacobian,source_columns,target_columns,column_count,*,chunk_points=128,maximum_bytes=64*1024**2):
        s,t,sj,tj=[np.asarray(v) for v in (source,target,source_jacobian,target_jacobian)]
        if (s.ndim!=2 or t.ndim!=2 or s.shape[1:]!=(3,) or t.shape[1:]!=(3,) or not 1<=len(s)<=32768 or not 4<=len(t)<=32768
                or sj.ndim!=3 or tj.ndim!=3 or sj.shape[:2]!=s.shape or tj.shape[:2]!=t.shape or not 1<=sj.shape[2]<=384 or not 1<=tj.shape[2]<=384
                or type(column_count) is not int or not 1<=column_count<=384):raise ValueError('Complete bounded vertices and every matching local derivative column required')
        if any(v.dtype.kind not in 'fiu' or not np.isfinite(v).all() or np.any(abs(v)>1e6) for v in (s,t,sj,tj)):raise ValueError('Finite bounded real vertices and Jacobians required')
        maps=[]
        for columns,width in [(source_columns,sj.shape[2]),(target_columns,tj.shape[2])]:
            if not isinstance(columns,(list,tuple)) or len(columns)!=width or any(type(i) is not int or not 0<=i<column_count for i in columns) or len(set(columns))!=width:raise ValueError('Distinct complete local-to-global column map required for each body')
            maps.append(np.array(columns,dtype=int))
        if type(chunk_points) is not int or not 1<=chunk_points<=4096 or type(maximum_bytes) is not int or not 1<=maximum_bytes<=64*1024**2:raise ValueError('Explicit bounded complete allocation policy required')
        estimate=sum(v.size*8 for v in (s,t,sj,tj))+2*len(s)*column_count*8+len(s)*16*8+min(chunk_points,len(s))*3*3*max(sj.shape[2],tj.shape[2])*8*4
        if estimate>maximum_bytes:raise ValueError('Complete mesh-Jacobian allocation budget exceeded; no point/column truncation')
        if len(self._records)>=self.maximum_records:raise ValueError('Complete mesh receipt budget exhausted')
        depth,gradient,triangles,barycentric,report,auditor=self._query(s,t);jac=np.zeros((len(s),column_count))
        for first in range(0,len(s),chunk_points):
            last=min(first+chunk_points,len(s));ids=np.arange(first,last);g=gradient[first:last]
            source_part=np.einsum('vi,vic->vc',g,sj[first:last]);target_part=-np.einsum('vfi,vfic->vc',barycentric[first:last,:,None]*g[:,None,:],tj[triangles[first:last]])
            jac[np.ix_(ids,maps[0])]+=source_part;jac[np.ix_(ids,maps[1])]+=target_part
        if not np.isfinite(jac).all():raise ValueError('Finite complete coupled depth Jacobian required')
        report.update(linearization_schema='strep-coupled-mesh-jacobian-v1',complete_control_columns=column_count,source_control_columns=list(source_columns),target_control_columns=list(target_columns),jacobian_sha256=_digest(jac),all_source_rows_returned=True)
        self._records.append(copy.deepcopy(report));self._last_auditor_depths=auditor.copy()
        return depth,auditor,jac,report
