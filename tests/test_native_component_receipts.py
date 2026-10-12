"""Passive mixed receipt layouts, multi-actor counts and immutable bindings."""
from pathlib import Path
import copy,hashlib,json,struct,sys,tempfile,unittest,zipfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_component_receipts import diagnose,numeric
from native_rate_receipts import digest


def save(path,data):Path(path).write_text(json.dumps(data)+'\n',encoding='utf-8')


def npy(values,shape=None,*,fortran=False,dtype='<f8'):
    header=repr(dict(descr=dtype,fortran_order=fortran,shape=shape or (len(values),)))+'\n'
    return b'\x93NUMPY\x01\x00'+struct.pack('<H',len(header))+header.encode()+struct.pack('<'+str(len(values))+'d',*values)


def fixture(folder,actors=('A',),*,suffix=False,fortran=False):
    asset=folder/'rig.glb';clock=[0.,1/120,2/120,3/120];binary=struct.pack('<4f',*clock)
    document=dict(nodes=[dict(name='Root',children=[1]),dict(name='Foot')],skins=[dict(joints=[0,1])],
        buffers=[dict(byteLength=len(binary))],bufferViews=[dict(buffer=0,byteOffset=0,byteLength=len(binary))],
        accessors=[dict(bufferView=0,componentType=5126,type='SCALAR',count=4)],
        animations=[dict(channels=[dict(sampler=0,target=dict(node=0,path='translation'))],samplers=[dict(input=0,interpolation='LINEAR')])])
    raw=json.dumps(document).encode();raw+=b' '*(-len(raw)%4)
    total=12+8+len(raw)+8+len(binary);asset.write_bytes(struct.pack('<4sII',b'glTF',2,total)+struct.pack('<II',len(raw),0x4e4f534a)+raw+struct.pack('<II',len(binary),0x004e4942)+binary)
    source=folder/'contacts.json';duration=struct.unpack('<f',binary[-4:])[0]
    save(source,dict(duration_s=duration,actors={a:dict(glb=str(asset),sha256=digest(asset),animation_index=0) for a in actors},contacts=[]))
    declarations={a:dict(window_s=[0.,duration],protected_s=[],knots_s=[0.,duration/2,duration],
        tracks=[dict(node=0,path='translation',maximum_change=.02)],maximum_joint_displacement_m=.02) for a in actors}
    boundary=folder/'boundary.json';request=dict(schema='strep-native-scene-boundary-edit-v1',
        permissions=dict(schema='strep-native-scene-edit-v1',contacts_sha256=digest(source),actors=declarations),
        boundary_keys={a:dict(start='preserve',end='preserve') for a in actors},acknowledge_changed_boundary_compatibility=False)
    save(boundary,request);authoring=hashlib.sha256(json.dumps(request,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
    policy_path=folder/'policy.json';policy=dict(schema='strep-native-component-storage-repair-v1',authoring_sha256=authoring,allowed_paths=['rotation','translation'],maximum_component_steps=1,maximum_corrections=64,acknowledge_storage_adjustment=True);save(policy_path,policy)
    sizes=[2,8,6,4,6,4];caps=[];scales=[];native=[]
    for a in actors:
        caps+=[1.]*2+[.02]*8+[.50001]*20;scales+=[1.]*2+[.02]*8+[.5]*20
        actor_values=[-1.]*30;actor_values[16]=.001;actor_values[29]=.002;native+=actor_values
    if suffix:caps+=[.01];scales+=[.01];native+=[.005]
    intended=[-1.]*len(native);controls=[0.,0.,0.]*len(actors)
    cap_path=folder/'source-rate-caps.npz'
    with zipfile.ZipFile(cap_path,'w') as z:
        z.writestr('times_s.npy',npy(clock))
        for a in actors:
            for m,n in enumerate((3,2,3,2)):z.writestr(a+'_metric_'+str(m)+'.npy',npy([.5]*(n*2),(n,2),fortran=fortran))
    raw=folder/'storage-search/start';raw.mkdir(parents=True)
    array_path=raw/'observations.npz';continuous=folder/'unrounded-observations.npz'
    for path,residual in ((array_path,native),(continuous,intended)):
        with zipfile.ZipFile(path,'w') as z:
            for key,values in dict(residual=residual,caps=caps,scales=scales,controls=controls,uniform_times_s=clock).items():z.writestr(key+'.npy',npy(values))
    files={}
    for i,a in enumerate(actors):
        target=raw/f'actor-{i}.glb';target.write_bytes(asset.read_bytes());files[a]=dict(path=target.name,sha256=digest(target))
    probe=raw/'probe.json';save(probe,dict(native_conditions=len(native),native_failed=sum(v>0 for v in native),observations_sha256=digest(array_path),
        files=files,edit_audits={a:dict(storage_adjustment=policy,passed=True) for a in actors}))
    report=folder/'storage-repair.json';save(report,dict(selected_native_label='start',original_authoring_sha256=authoring,
        storage_policy_sha256=hashlib.sha256(json.dumps(policy,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest(),
        native_probe_receipts_sha256={'start':digest(probe)},unrounded_observations_sha256=digest(continuous),unrounded_failed=0,
        geometry_assessed=False,quality_approved=False,release_approved=False))
    return source,boundary,cap_path,policy_path,report


class ComponentReceipts(unittest.TestCase):
    def test_complete_known_rows_and_translation_coverage(self):
        with tempfile.TemporaryDirectory() as name:
            args=fixture(Path(name));result=diagnose(*args)
            self.assertEqual((result['conditions'],result['native_failed'],result['intended_failed']),(30,2,0))
            self.assertEqual([r['conditions'] for r in result['groups']],[2,8,6,4,6,4])
            p,a=result['details'];self.assertEqual((p['node'],p['metric'],p['rate_frame']),(0,'position_acceleration',0))
            self.assertEqual(p['permitted_support'],[dict(node=0,path='translation',editable_support_keys=[1,2])])
            self.assertEqual((a['node'],a['metric']),(1,'angular_acceleration'));self.assertEqual(a['permitted_support'],[])
            self.assertTrue(result['all_rate_details_included']);self.assertFalse(result['quality_approved'])

    def test_multi_actor_and_suffix_counts_remain_complete(self):
        with tempfile.TemporaryDirectory() as name:
            result=diagnose(*fixture(Path(name),actors=('B','A'),suffix=True))
            self.assertEqual(result['native_failed'],5);self.assertEqual(result['rate_failure_count'],4)
            self.assertEqual([r['actor'] for r in result['details']],['B','B','A','A'])
            self.assertEqual(result['uninterpreted_suffix_conditions'],1);self.assertEqual(result['uninterpreted_suffix_native_failed'],1)

    def test_detail_limit_does_not_change_counts(self):
        with tempfile.TemporaryDirectory() as name:
            args=fixture(Path(name));one=diagnose(*args,maximum_details=1);all_rows=diagnose(*args)
            self.assertEqual(one['groups'],all_rows['groups']);self.assertEqual(one['native_failed'],2)
            self.assertEqual(len(one['details']),1);self.assertFalse(one['all_rate_details_included'])
            for bad in (True,0,10001):
                with self.assertRaises(ValueError):diagnose(*args,maximum_details=bad)

    def test_fortran_matrix_is_read_in_logical_row_order(self):
        with tempfile.TemporaryDirectory() as name:
            path=Path(name)/'matrix.npz'
            with zipfile.ZipFile(path,'w') as z:z.writestr('matrix.npy',npy([1.,3.,2.,4.],(2,2),fortran=True))
            with zipfile.ZipFile(path) as z:self.assertEqual(list(numeric(z,'matrix')[1]),[1.,2.,3.,4.])
        with tempfile.TemporaryDirectory() as name:self.assertEqual(diagnose(*fixture(Path(name),fortran=True))['native_failed'],2)

    def test_source_clock_and_caps_changes_are_rejected(self):
        for fault in ('clock','cap','shape'):
            with self.subTest(fault=fault),tempfile.TemporaryDirectory() as name:
                args=fixture(Path(name));path=args[2]
                with zipfile.ZipFile(path) as z:data={n:z.read(n) for n in z.namelist()}
                if fault=='clock':data['times_s.npy']=npy([0.,.01,.02,.03])
                elif fault=='cap':data['A_metric_0.npy']=npy([.6]*6,(3,2))
                else:data['A_metric_0.npy']=npy([.5]*6,(2,3))
                with zipfile.ZipFile(path,'w') as z:
                    for key,value in data.items():z.writestr(key,value)
                with self.assertRaises(ValueError):diagnose(*args)

    def test_bound_array_receipt_asset_and_policy_changes_reject(self):
        for fault in ('probe','array','unrounded','source','output','policy','label'):
            with self.subTest(fault=fault),tempfile.TemporaryDirectory() as name:
                folder=Path(name);args=fixture(folder)
                if fault=='label':
                    with self.assertRaises(ValueError):diagnose(*args,native_label='../outside')
                    continue
                path={'probe':folder/'storage-search/start/probe.json','array':folder/'storage-search/start/observations.npz',
                    'unrounded':folder/'unrounded-observations.npz','source':folder/'rig.glb','output':folder/'storage-search/start/actor-0.glb','policy':args[3]}[fault]
                path.write_bytes(path.read_bytes()+b'changed')
                with self.assertRaises((ValueError,json.JSONDecodeError)):diagnose(*args)


if __name__=='__main__':unittest.main()
