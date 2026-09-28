"""Finalize source/output hash labeling and verify versioned animation packs."""
import argparse
import zipfile
from pathlib import Path
import numpy as np
from strep import ROOT,read,save,sha256,now
from inspect_motion import validate_motion,contact_events
from build_soma_preview import ASSET
from floor_contact import correct as limb_correct


def verify(folder):
    summary=read(folder/'summary.json');skin=dict(np.load(ASSET));rows=[]
    previous={}
    for name in ['floor-contact-v1-reviewed','floor-contact-holdout-v1']:
        for t in read(ROOT/'reports'/name/'summary.json')['trials']:
            previous[t['source_sha256']]=ROOT/'reports'/name/'takes'/t['id']/'motion.npz'
    for t in summary['trials']:
        path=folder/'takes'/t['id'];origin=ROOT/'reports'/t['source_collection']/'takes'/t['source_original_id']
        for file,digest in t['raw_trial']['hashes'].items():assert sha256(origin/file)==digest
        for file,digest in t['hashes'].items():assert sha256(path/file)==digest,(t['id'],file)
        # Early candidate evidence inherited the raw trial's top-level hashes.
        # Source hashes already live under raw_trial; remove the ambiguous copy.
        evidence=read(path/'evidence.json')
        limb_evidence=read(path/'limb/evidence.json')
        inherited_limb_hashes='hashes' in limb_evidence
        if inherited_limb_hashes:
            limb_evidence.pop('hashes');save(path/'limb/evidence.json',limb_evidence)
            t['hashes']['limb/evidence.json']=sha256(path/'limb/evidence.json')
        t['limb_trial'].pop('hashes',None)
        evidence['limb_trial'].pop('hashes',None)
        processing=('Experimental whole-body clearance; vertical root and torso edited; compare all three versions' if t['body_correction']['applied'] else 'Body stage unchanged; hands/feet correction only')
        t['processing']=processing
        if 'hashes' in evidence or evidence['processing']!=processing or inherited_limb_hashes:
            evidence.pop('hashes',None);evidence['processing']=processing;save(path/'evidence.json',evidence)
            with zipfile.ZipFile(path/'animation-pack.zip') as z:members=z.namelist()
            with zipfile.ZipFile(path/'animation-pack.zip','w',zipfile.ZIP_DEFLATED) as z:
                for file in members:
                    z.write(ROOT/'vendor/kimodo/LICENSE' if file=='LICENSE.txt' else path/file,file)
            t['hashes']['evidence.json']=sha256(path/'evidence.json')
            t['hashes']['animation-pack.zip']=sha256(path/'animation-pack.zip')
        for file in ['motion.npz','motion.bvh','soma.glb','root-motion.json','contacts.json','evidence.json']:
            assert sha256(path/'raw'/file)==sha256(origin/file)
        raw=dict(np.load(path/'raw/motion.npz'));base=dict(np.load(path/'limb/motion.npz'));candidate=dict(np.load(path/'motion.npz'))
        if t['source_sha256'] in previous:expected=dict(np.load(previous[t['source_sha256']]))
        else:expected,_=limb_correct(raw,skin)
        assert set(base)==set(expected)
        for key in base:np.testing.assert_array_equal(base[key],expected[key])
        np.testing.assert_array_equal(candidate['root_positions'][:,[0,2]],raw['root_positions'][:,[0,2]])
        np.testing.assert_allclose(candidate['global_rot_mats'][:,0],raw['global_rot_mats'][:,0],atol=1e-6)
        np.testing.assert_array_equal(candidate['foot_contacts'],raw['foot_contacts'])
        recipe=read(path/'recipe.json')['body']
        np.testing.assert_allclose(candidate['root_positions'][:,1]-raw['root_positions'][:,1],recipe['root_lift_m'],atol=2e-7)
        if not recipe['applied']:
            for key in base:np.testing.assert_array_equal(base[key],candidate[key])
        elif 'smooth_root_pos' in candidate:raise AssertionError('Stale root feature in edited output')
        for motion,directory in [(candidate,path),(base,path/'limb')]:
            root=read(directory/'root-motion.json');np.testing.assert_array_equal(root['positions_m'],motion['root_positions'])
            np.testing.assert_allclose(root['times_s'],np.arange(len(motion['root_positions']))/30,atol=1e-12)
            _,_,feet=validate_motion(motion,30)
            assert read(directory/'contacts.json')['intervals']==contact_events(motion['foot_contacts'],feet,30)
        with zipfile.ZipFile(path/'animation-pack.zip') as z:
            for file in z.namelist():
                if file=='LICENSE.txt':assert z.read(file)==(ROOT/'vendor/kimodo/LICENSE').read_bytes()
                else:assert z.read(file)==(path/file).read_bytes()
        rows.append(dict(id=t['id'],source_hashes_preserved=True,limb_baseline_exact=True,horizontal_root_and_contact_labels_exact=True,
                         root_tracks_and_pack_members_exact=True,validation=t['validation']))
    summary['metadata_finalizer_sha256']=sha256(__file__);save(folder/'summary.json',summary)
    report=dict(verified_at=now(),trials=rows,verifier_sha256=sha256(__file__),
                total=len(rows),passes=sum(not t['flags'] for t in summary['trials']),
                human_approved=False,engine_import=None)
    save(folder/'verification.json',report);print(folder.name,report['total'],'verified;',report['passes'],'numerical passes')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('folders',nargs='+',type=Path)
    for folder in p.parse_args().folders:verify(folder)
