"""Bound archive identities, full populations and known rate-row/ancestor mapping."""
from pathlib import Path
import copy
import json
import math
import struct
import sys
import tempfile
import unittest
import warnings
import zipfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_rate_receipts import diagnose,digest,read,vector


def save(path,data):
    Path(path).write_text(json.dumps(data)+'\n',encoding='utf-8')


def npy(values,*,dtype='<f8',shape=None,fortran=False):
    header=repr(dict(descr=dtype,fortran_order=fortran,shape=shape or (len(values),)))+'\n'
    return b'\x93NUMPY\x01\x00'+struct.pack('<H',len(header))+header.encode()+struct.pack('<'+str(len(values))+'d',*values)


def fixture(root):
    rig=root/'rig.glb';document=dict(nodes=[dict(name='Root',children=[1]),dict(name='Hip',children=[2]),
        dict(name='Foot',children=[3]),dict(name='Toe')],skins=[dict(joints=[3])])
    raw=json.dumps(document).encode();raw+=b' '*(-len(raw)%4)
    rig.write_bytes(struct.pack('<4sIIII',b'glTF',2,20+len(raw),len(raw),0x4e4f534a)+raw)
    source=root/'contacts.json';save(source,dict(actors=dict(A=dict(glb=str(rig),sha256=digest(rig)))))
    # Four rate samples and one joint: two key bounds, four displacements,
    # three speed rows and two acceleration rows in each rate representation.
    sizes=[2,4,3,2,3,2];names=['track_bound','joint_displacement','position_speed',
        'position_acceleration','angular_speed','angular_acceleration']
    stored=[-1.]*16;stored[10]=.0005;stored[14]=.002
    continuous=[-1.]*16
    vectors=dict(stored_residual=stored,unrounded_residual=continuous,native_caps=[.50001]*16,
        native_scales=[.5]*16,uniform_times_s=[0.,.01,.02,.03])
    observations=root/'observations.npz'
    with zipfile.ZipFile(observations,'w') as z:
        for name,values in vectors.items():z.writestr(name+'.npy',npy(values))
    groups=[];offset=0
    for name,size in zip(names,sizes):
        groups.append(dict(metric=name,conditions=size,stored_failed=sum(v>0 for v in stored[offset:offset+size]),unrounded_failed=0));offset+=size
    receipt=dict(mode='fine',label='1-4',conditions=16,groups=groups,stored_failed=2,unrounded_failed=0,
        stored_pass=False,unrounded_pass=True,observations_sha256=digest(observations))
    rp=root/'receipt.json';save(rp,receipt)
    binding=root/'binding.json';save(binding,dict(status='complete',cases=[receipt],
        source_bindings_sha256={str(source):digest(source),str(rig):digest(rig)}))
    return rp,observations,source,binding


class RateReceipts(unittest.TestCase):
    def test_detail_pages_keep_complete_counts_and_source_order(self):
        with tempfile.TemporaryDirectory() as folder:
            paths=fixture(Path(folder));a=diagnose(*paths,'A',maximum_details=1)
            b=diagnose(*paths,'A',detail_offset=1,maximum_details=1)
            self.assertEqual(a['rate_failure_count'],2);self.assertEqual(a['groups'],b['groups'])
            self.assertEqual(a['rate_failures'][0]['row'],10);self.assertEqual(b['rate_failures'][0]['row'],14)
            self.assertFalse(a['all_rate_failure_details_included']);self.assertFalse(b['all_rate_failure_details_included'])
            self.assertEqual(diagnose(*paths,'A',detail_offset=2)['rate_failures'],[])
            with self.assertRaises(ValueError):diagnose(*paths,'A',detail_offset=3)
            for options in (dict(detail_offset=True),dict(detail_offset=-1),dict(maximum_details=True),dict(maximum_details=0),dict(maximum_details=10001)):
                with self.assertRaises(ValueError):diagnose(*paths,'A',**options)

    def test_complete_counts_and_exact_known_rate_support(self):
        with tempfile.TemporaryDirectory() as folder:
            paths=fixture(Path(folder));r=diagnose(*paths,'A')
            self.assertEqual(r['recorded_native_conditions'],16)
            self.assertEqual([g['conditions'] for g in r['groups']],[2,4,3,2,3,2])
            p,a=r['rate_failures'];self.assertEqual(p['metric'],'position_acceleration')
            self.assertEqual((p['row'],p['node'],p['rate_frame'],p['joint_slot']),(10,3,1,0))
            self.assertEqual(p['sample_times_s'],[.01,.02,.03])
            self.assertEqual([n['node'] for n in p['influencing_rotation_nodes']],[2,1,0])
            self.assertEqual(a['sample_times_s'],[0.,.01,.02])
            self.assertEqual([n['node'] for n in a['influencing_rotation_nodes']],[3,2,1,0])
            self.assertEqual(p['stored_absolute_excess_from_receipt'],.00025)
            self.assertFalse(r['stored_pass']);self.assertTrue(r['unrounded_pass'])
            self.assertFalse(r['quality_approved']);self.assertFalse(r['training_admitted']);self.assertFalse(r['release_approved'])

    def test_unrounded_only_failure_is_not_hidden(self):
        with tempfile.TemporaryDirectory() as folder:
            paths=fixture(Path(folder));receipt=read(paths[0]);binding=read(paths[3])
            with zipfile.ZipFile(paths[1]) as z:members={n:z.read(n) for n in z.namelist()}
            values=[-1.]*16;values[6]=.03;members['unrounded_residual.npy']=npy(values)
            with zipfile.ZipFile(paths[1],'w') as z:
                for n,v in members.items():z.writestr(n,v)
            receipt['observations_sha256']=digest(paths[1]);receipt['unrounded_failed']=1;receipt['unrounded_pass']=False
            receipt['groups'][2]['unrounded_failed']=1;save(paths[0],receipt);binding['cases']=[receipt];save(paths[3],binding)
            report=diagnose(*paths,'A');first=report['rate_failures'][0]
            self.assertEqual(first['metric'],'position_speed');self.assertEqual(first['sample_times_s'],[0.,.01])
            self.assertFalse(first['stored_failed']);self.assertTrue(first['unrounded_failed'])

    def test_changed_or_incomplete_provenance_cannot_be_reported(self):
        for fault in ('archive','receipt','source','rig','duplicate-case','missing-source-binding','wrong-actor'):
            with self.subTest(fault=fault),tempfile.TemporaryDirectory() as folder:
                paths=fixture(Path(folder));binding=read(paths[3]);actor='A'
                if fault=='archive':paths[1].write_bytes(paths[1].read_bytes()+b'changed')
                elif fault=='receipt':r=read(paths[0]);r['label']='other';save(paths[0],r)
                elif fault=='source':paths[2].write_bytes(paths[2].read_bytes()+b' ')
                elif fault=='rig':(Path(folder)/'rig.glb').write_bytes((Path(folder)/'rig.glb').read_bytes()+b'x')
                elif fault=='duplicate-case':binding['cases'].append(copy.deepcopy(binding['cases'][0]));save(paths[3],binding)
                elif fault=='missing-source-binding':binding['source_bindings_sha256'].pop(str(paths[2]));save(paths[3],binding)
                else:actor='B'
                with self.assertRaises(ValueError):diagnose(*paths,actor)

    def test_full_recorded_populations_and_decisions_are_required(self):
        for fault in ('short-vector','wrong-group-size','wrong-group-order','failed-count','bool-count','passed-claim','scale','clock','negative-clock','nan'):
            with self.subTest(fault=fault),tempfile.TemporaryDirectory() as folder:
                paths=fixture(Path(folder));receipt=read(paths[0]);binding=read(paths[3])
                with zipfile.ZipFile(paths[1]) as z:members={n:z.read(n) for n in z.namelist()}
                if fault=='short-vector':members['stored_residual.npy']=npy([-1.]*15)
                elif fault=='wrong-group-size':receipt['groups'][1]['conditions']=3
                elif fault=='wrong-group-order':receipt['groups'].reverse()
                elif fault=='failed-count':receipt['groups'][3]['stored_failed']=0
                elif fault=='bool-count':receipt['groups'][3]['stored_failed']=True
                elif fault=='passed-claim':receipt['stored_pass']=True
                elif fault=='scale':members['native_scales.npy']=npy([0.]*16)
                elif fault=='clock':members['uniform_times_s.npy']=npy([0.,.01,.01,.03])
                elif fault=='negative-clock':members['uniform_times_s.npy']=npy([-.01,0.,.01,.02])
                else:members['stored_residual.npy']=npy([math.nan]*16)
                with zipfile.ZipFile(paths[1],'w') as z:
                    for n,v in members.items():z.writestr(n,v)
                receipt['observations_sha256']=digest(paths[1]);save(paths[0],receipt)
                binding['cases']=[receipt];save(paths[3],binding)
                with self.assertRaises(ValueError):diagnose(*paths,'A')

    def test_npy_objects_multidimensional_payloads_and_duplicate_members_reject(self):
        for fault in ('object','matrix','fortran','duplicate','missing','truncated'):
            with self.subTest(fault=fault),tempfile.TemporaryDirectory() as folder:
                path=Path(folder)/'archive.npz'
                with zipfile.ZipFile(path,'w') as z:
                    if fault!='missing':
                        raw=npy([1.,2.],dtype='|O' if fault=='object' else '<f8',
                            shape=(1,2) if fault=='matrix' else None,fortran=fault=='fortran')
                        if fault=='truncated':raw=raw[:-1]
                        z.writestr('values.npy',raw)
                        if fault=='duplicate':
                            with warnings.catch_warnings():
                                warnings.simplefilter('ignore',UserWarning);z.writestr('values.npy',raw)
                with zipfile.ZipFile(path) as z,self.assertRaises(ValueError):vector(z,'values')


if __name__=='__main__':unittest.main()
