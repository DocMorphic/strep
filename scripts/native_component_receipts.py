"""Inspect saved mixed repair rows and permitted key support without NumPy/model execution."""
import argparse,array,ast,bisect,hashlib,json,math,re,struct,sys,zipfile
from pathlib import Path
from native_rate_receipts import digest,read,rig_joints,vector

METRICS=('position_speed','position_acceleration','angular_speed','angular_acceleration')


def numeric(archive,name):
    member=name+'.npy'
    if archive.namelist().count(member)!=1:raise ValueError('Distinct complete numeric array required')
    info=archive.getinfo(member)
    if info.file_size>16_020_000:raise ValueError('Inspection array budget exceeded')
    raw=archive.read(member)
    if len(raw)<10 or raw[:8]!=b'\x93NUMPY\x01\x00':raise ValueError('Little-endian Float64 NPY v1 array required')
    length=struct.unpack_from('<H',raw,8)[0]
    if not 1<=length<=16384 or 10+length>len(raw):raise ValueError('Complete NPY header required')
    h=ast.literal_eval(raw[10:10+length].decode('latin1'))
    if not isinstance(h,dict):raise ValueError('Numeric array header required')
    shape=h.get('shape')
    if (h.get('descr')!='<f8' or type(h.get('fortran_order')) is not bool or not isinstance(shape,tuple)
            or not 1<=len(shape)<=2 or any(type(n) is not int or n<1 for n in shape)
            or math.prod(shape)>2_000_000 or len(raw)-10-length!=math.prod(shape)*8):
        raise ValueError('Complete finite row-major scalar/matrix population required')
    data=array.array('d');data.frombytes(raw[10+length:])
    if sys.byteorder!='little':data.byteswap()
    if not all(math.isfinite(v) for v in data):raise ValueError('Finite saved values required')
    if h['fortran_order'] and len(shape)==2:
        data=array.array('d',(data[r+c*shape[0]] for r in range(shape[0]) for c in range(shape[1])))
    return shape,data


def clocks(path,index,tracks):
    with Path(path).open('rb') as stream:
        head=stream.read(20);_,_,_,size,_=struct.unpack('<4sIIII',head)
        document=json.loads(stream.read(size));bin_header=stream.read(8)
        if len(bin_header)!=8:raise ValueError('Source binary chunk required')
        bin_size,kind=struct.unpack('<II',bin_header);origin=stream.tell()
        if kind!=0x004E4942 or origin+bin_size>Path(path).stat().st_size:raise ValueError('Complete source binary required')
        animation=document['animations'][index];result={}
        for track in tracks:
            matched=[c for c in animation['channels'] if c['target']==dict(node=track['node'],path=track['path'])]
            if len(matched)!=1:raise ValueError('Distinct authored source track required')
            sampler=animation['samplers'][matched[0]['sampler']]
            if sampler.get('interpolation','LINEAR')!='LINEAR':raise ValueError('Authored LINEAR track required')
            accessor=document['accessors'][sampler['input']];view=document['bufferViews'][accessor['bufferView']]
            count=accessor['count'];stride=view.get('byteStride',4);offset=view.get('byteOffset',0)+accessor.get('byteOffset',0)
            if (accessor.get('type')!='SCALAR' or accessor.get('componentType')!=5126 or 'sparse' in accessor
                    or type(count) is not int or not 2<=count<=20000 or type(stride) is not int or not 4<=stride<=252
                    or stride%4 or view.get('buffer')!=0 or offset<0 or offset+(count-1)*stride+4>bin_size
                    or accessor.get('byteOffset',0)+(count-1)*stride+4>view['byteLength']):
                raise ValueError('Bounded complete native Float32 clock required')
            stream.seek(origin+offset);raw=stream.read((count-1)*stride+4)
            clock=[struct.unpack_from('<f',raw,i*stride)[0] for i in range(count)]
            if not all(math.isfinite(v) for v in clock) or clock[0]<0 or any(b<=a for a,b in zip(clock,clock[1:])):
                raise ValueError('Increasing finite native clock required')
            result[track['node'],track['path']]=clock
    return result


def editable(clock,window,protected,edges,duration):
    ids=[i for i in range(1,len(clock)-1) if clock[i-1]>=window[0] and clock[i+1]<=window[1]
        and not any(clock[i-1]<b and clock[i+1]>a for a,b in protected)]
    for edge,index in (('start',0),('end',len(clock)-1)):
        if edges[edge]!='edit':continue
        before,after=(clock[0],clock[1]) if index==0 else (clock[-2],clock[-1]);t=clock[index]
        if (t!=(0. if edge=='start' else duration) or not window[0]<=before<after<=window[1]
                or any(a<=t<=b or before<b and after>a for a,b in protected)):
            raise ValueError('Declared native edge is missing/protected')
        ids.append(index)
    return sorted(set(ids))


def diagnose(contacts_path,boundary_path,caps_path,policy_path,report_path,*,native_label=None,maximum_details=512):
    if type(maximum_details) is not int or not 1<=maximum_details<=10000:raise ValueError('Bounded detail count required')
    paths=[Path(p).resolve() for p in (contacts_path,boundary_path,caps_path,policy_path,report_path)]
    contacts_path,boundary_path,caps_path,policy_path,report_path=paths;pins={str(p):digest(p) for p in paths}
    for p in (Path(__file__),Path(__file__).with_name('native_rate_receipts.py')):pins[str(p.resolve())]=digest(p)
    scene,boundary,policy,report=[read(p) for p in (contacts_path,boundary_path,policy_path,report_path)]
    authoring=hashlib.sha256(json.dumps(boundary,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
    if (boundary.get('schema')!='strep-native-scene-boundary-edit-v1' or policy.get('schema')!='strep-native-component-storage-repair-v1'
            or boundary['permissions']['contacts_sha256']!=pins[str(contacts_path)] or policy['authoring_sha256']!=authoring
            or report['original_authoring_sha256']!=authoring):raise ValueError('Exact original authoring binding required')
    policy_digest=hashlib.sha256(json.dumps(policy,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
    allowed=policy.get('allowed_paths')
    if (not isinstance(allowed,list) or not allowed or any(type(p) is not str or p not in ('rotation','translation') for p in allowed)
            or len(set(allowed))!=len(allowed) or type(policy.get('maximum_component_steps')) is not int or policy['maximum_component_steps']!=1
            or type(policy.get('maximum_corrections')) is not int or not 1<=policy['maximum_corrections']<=64
            or policy.get('acknowledge_storage_adjustment') is not True):raise ValueError('Explicit bounded component policy required')
    if report['storage_policy_sha256']!=policy_digest or any(report[k] is not False for k in ('geometry_assessed','quality_approved','release_approved')):
        raise ValueError('Bound unapproved component receipt required')
    label=report['selected_native_label'] if native_label is None else native_label
    if not isinstance(label,str) or not re.fullmatch(r'start|storage-[0-7]-(?:[0-9]|[1-5][0-9]|6[0-3])',label) or label not in report['native_probe_receipts_sha256']:
        raise ValueError('Contained recorded native label required')
    folder=report_path.parent;raw=folder/'storage-search'/label;receipt_path=raw/'probe.json'
    if digest(receipt_path)!=report['native_probe_receipts_sha256'][label]:raise ValueError('Native probe receipt changed')
    receipt=read(receipt_path);npz=raw/'observations.npz';unrounded=folder/'unrounded-observations.npz'
    if digest(npz)!=receipt['observations_sha256'] or digest(unrounded)!=report['unrounded_observations_sha256']:raise ValueError('Bound complete arrays required')
    pins.update({str(receipt_path):digest(receipt_path),str(npz):digest(npz),str(unrounded):digest(unrounded)})
    with zipfile.ZipFile(npz) as archive:
        native,ncaps,nscales,times,controls=[vector(archive,n) for n in ('residual','caps','scales','uniform_times_s','controls')]
    with zipfile.ZipFile(unrounded) as archive:
        intended,icaps,iscales,icontrols=[vector(archive,n) for n in ('residual','caps','scales','controls')]
    if (len(native)!=receipt['native_conditions'] or len(native)!=len(intended) or ncaps!=icaps or nscales!=iscales
            or len(ncaps)!=len(native) or len(nscales)!=len(native) or controls!=icontrols or any(s<=0 for s in nscales)
            or sum(v>0 for v in native)!=receipt['native_failed'] or sum(v>0 for v in intended)!=report['unrounded_failed']):
        raise ValueError('Complete matching native/intended population and decisions required')
    if len(times)<3 or any(abs((b-a)-(times[1]-times[0]))>1e-12 for a,b in zip(times,times[1:])) or times[0]!=0:
        raise ValueError('Original uniform rate clock required')
    groups=[];details=[];failures=0;offset=0;actors=boundary['permissions']['actors']
    if not isinstance(actors,dict) or not actors or set(actors)-set(scene['actors']):raise ValueError('Existing original edited actors required')
    with zipfile.ZipFile(caps_path) as archive:
        original_times=vector(archive,'times_s')
        if times!=original_times:raise ValueError('Source-rate clock changed')
        expected_arrays={'times_s.npy'}|{name+'_metric_'+str(m)+'.npy' for name in actors for m in range(4)}
        if set(archive.namelist())!=expected_arrays:raise ValueError('Complete original edited-actor cap population required')
        for name,declaration in actors.items():
            source=scene['actors'][name];asset=(contacts_path.parent/source['glb']).resolve()
            if digest(asset)!=source['sha256']:raise ValueError('Original actor asset changed')
            pins[str(asset)]=digest(asset);nodes,joints,parents=rig_joints(asset)
            track_clocks=clocks(asset,source['animation_index'],declaration['tracks']);edges=boundary['boundary_keys'][name]
            tracks=[dict(t,clock=track_clocks[t['node'],t['path']],ids=editable(track_clocks[t['node'],t['path']],declaration['window_s'],declaration['protected_s'],edges,scene['duration_s'])) for t in declaration['tracks']]
            layout=[('track_bound',sum(len(t['ids']) for t in tracks),None),('joint_displacement',len(times)*len(joints),None)]
            for metric in range(4):
                shape,data=numeric(archive,name+'_metric_'+str(metric));expected=(len(times)-(1 if metric in (0,2) else 2),len(joints))
                if shape!=expected or any(c<0 for c in data):raise ValueError('Complete original rate-cap dimensions required')
                layout.append((METRICS[metric],len(data),data))
            for kind,size,original in layout:
                if offset+size>len(native):raise ValueError('Complete actor row population required')
                expected_caps=original if original is not None else None
                for i in range(size):
                    cap=(expected_caps[i]+1e-5) if expected_caps is not None else (1. if kind=='track_bound' else declaration['maximum_joint_displacement_m'])
                    scale=max(expected_caps[i],.001) if expected_caps is not None else cap
                    if ncaps[offset+i]!=cap or nscales[offset+i]!=scale:raise ValueError('Original row caps/scales changed')
                selected=native[offset:offset+size];continuous=intended[offset:offset+size]
                groups.append(dict(actor=name,metric=kind,conditions=size,native_failed=sum(v>0 for v in selected),intended_failed=sum(v>0 for v in continuous)))
                if kind in METRICS:
                    metric=METRICS.index(kind);width=2 if metric in (0,2) else 3
                    for i,(stored,smooth) in enumerate(zip(selected,continuous)):
                        if stored<=0 and smooth<=0:continue
                        failures+=1
                        if len(details)>=maximum_details:continue
                        frame,slot=divmod(i,len(joints));node=joints[slot];ancestors=[];current=node
                        while current>=0:ancestors.append(current);current=parents[current]
                        eligible=[]
                        for t in tracks:
                            influential=t['path']=='translation' and metric<2 and t['node'] in ancestors or t['path']=='rotation' and t['node'] in (ancestors[1:] if metric<2 else ancestors)
                            if influential and t['path'] in policy['allowed_paths']:
                                support=times[frame:frame+width];keys=set()
                                for time in support:
                                    j=bisect.bisect_left(t['clock'],time);keys.update([j] if j<len(t['clock']) and t['clock'][j]==time else [max(0,j-1),min(len(t['clock'])-1,j)])
                                eligible.append(dict(node=t['node'],path=t['path'],editable_support_keys=sorted(keys.intersection(t['ids']))))
                        details.append(dict(actor=name,metric=kind,node=node,name=nodes[node].get('name'),row=offset+i,rate_frame=frame,
                            times_s=list(times[frame:frame+width]),native_failed=stored>0,intended_failed=smooth>0,native_residual=stored,intended_residual=smooth,
                            norm_cap=ncaps[offset+i],scale=nscales[offset+i],permitted_support=eligible))
                offset+=size
    suffix_native=sum(v>0 for v in native[offset:]);suffix_intended=sum(v>0 for v in intended[offset:])
    for name,record in receipt['files'].items():
        path=raw/record['path']
        if Path(record['path']).name!=record['path'] or digest(path)!=record['sha256']:raise ValueError('Native actor payload changed')
        pins[str(path)]=digest(path)
        if receipt['edit_audits'][name]['storage_adjustment']!=policy or not receipt['edit_audits'][name]['passed']:raise ValueError('Stored audit policy changed')
    if set(receipt['files'])!=set(actors) or any(digest(p)!=h for p,h in pins.items()):raise ValueError('Complete stable edited actor population required')
    return dict(schema='strep-native-component-receipt-diagnostic-v1',inputs_sha256=pins,native_label=label,conditions=len(native),groups=groups,
        native_failed=sum(v>0 for v in native),intended_failed=sum(v>0 for v in intended),rate_failure_count=failures,details=details,
        all_rate_details_included=len(details)==failures,uninterpreted_suffix_conditions=len(native)-offset,
        uninterpreted_suffix_native_failed=suffix_native,uninterpreted_suffix_intended_failed=suffix_intended,
        original_selected=True,quality_approved=False,training_admitted=False,release_approved=False,
        scope='Passive complete saved-row/cap/scale/count/source/key-support inspection, including edited actors. Contact/authored-speed suffix stays counted without row interpretation. Structural support is not repair feasibility; no pose, source-cap recomputation, geometry, engine, model or quality approval.')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('contacts','boundary','caps','policy','report','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--native-label');p.add_argument('--maximum-details',type=int,default=512);a=p.parse_args()
    if a.output.exists():raise ValueError('Fresh diagnostic output required')
    result=diagnose(a.contacts,a.boundary,a.caps,a.policy,a.report,native_label=a.native_label,maximum_details=a.maximum_details)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
    print(json.dumps({k:result[k] for k in ('native_label','conditions','native_failed','intended_failed','rate_failure_count','all_rate_details_included')}))


if __name__=='__main__':main()
