"""Finalize experimental review flags and independently check exported packs."""
import argparse
import zipfile
import numpy as np
from strep import ROOT,read,save,sha256,now
from build_soma_preview import ASSET
from gltf_tools import read_glb,accessor
from inspect_motion import contact_events,validate_motion


def verify(folder):
    summary=read(folder/'summary.json');skin=dict(np.load(ASSET));rows=[]
    for t in summary['trials']:
        path=folder/'takes'/t['id'];raw=t['raw_trial'];origin=ROOT/'reports'/t['source_collection']/'takes'/raw['id']
        for file,digest in raw['hashes'].items():
            assert sha256(origin/file)==digest,(t['id'],file,'raw altered')
        source=dict(np.load(path/'raw/motion.npz'));corrected=dict(np.load(path/'motion.npz'))
        assert sha256(path/'raw/motion.npz')==t['source_sha256']
        for file in ['soma.glb','motion.npz','motion.bvh','evidence.json','root-motion.json','contacts.json']:
            assert sha256(path/'raw'/file)==sha256(origin/file)
        assert np.array_equal(source['root_positions'],corrected['root_positions'])
        assert np.array_equal(source['foot_contacts'],corrected['foot_contacts'])
        doc,binary=read_glb(path/'soma.glb');attrs=doc['meshes'][0]['primitives'][0]['attributes']
        weights=np.concatenate([accessor(doc,binary,attrs[f'WEIGHTS_{i}']) for i in range(2)],axis=1)
        indices=np.concatenate([accessor(doc,binary,attrs[f'JOINTS_{i}']) for i in range(2)],axis=1)
        assert np.array_equal(weights,skin['lbs_weights']) and np.array_equal(indices,skin['lbs_indices'])
        root=read(path/'root-motion.json');np.testing.assert_array_equal(root['positions_m'],corrected['root_positions'])
        np.testing.assert_allclose(root['times_s'],np.arange(t['frames'])/30,atol=1e-12)
        _,_,feet=validate_motion(corrected,30)
        assert read(path/'contacts.json')['intervals']==contact_events(corrected['foot_contacts'],feet,30)
        # Early exports retained raw flags in the top-level field. Separate them
        # explicitly; corrected screens are always in floor_correction.flags.
        t['raw_flags']=raw['flags'];t['flags']=t['floor_correction']['flags']
        evidence=read(path/'evidence.json');evidence.update(raw_flags=t['raw_flags'],flags=t['flags'])
        save(path/'evidence.json',evidence)
        files=[n for n in t['hashes'] if n!='animation-pack.zip']
        with zipfile.ZipFile(path/'animation-pack.zip','w',zipfile.ZIP_DEFLATED) as z:
            for file in files:z.write(path/file,file)
            z.write(ROOT/'vendor/kimodo/LICENSE','LICENSE.txt')
        t['hashes']={file:sha256(path/file) for file in files+['animation-pack.zip']}
        with zipfile.ZipFile(path/'animation-pack.zip') as z:
            for file in files:assert z.read(file)==(path/file).read_bytes()
        rows.append(dict(id=t['id'],raw_hashes_preserved=True,all_eight_weights_and_indices_exact=True,
                         root_and_contacts_exact=True,zip_members_exact=True,**t['validation']))
    save(folder/'summary.json',summary)
    result=dict(verified_at=now(),verifier_sha256=sha256(__file__),trials=rows,
                passes=sum(not t['floor_correction']['flags'] for t in summary['trials']),total=len(rows),
                independent_human_review=False,engine_import=None)
    save(folder/'verification.json',result)
    print(folder.name,len(rows),'verified;',result['passes'],'provisional passes')


if __name__=='__main__':
    from pathlib import Path
    p=argparse.ArgumentParser();p.add_argument('folders',nargs='+',type=Path)
    for folder in p.parse_args().folders:verify(folder)
