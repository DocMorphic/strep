"""Measured target-rig composition review, with original failed sources retained."""
import os
import shutil
import zipfile
from strep import ROOT,read,save,sha256


def build():
    out=ROOT/'reports/corrected-rig-transfer-v1';cases=[];packages=[]
    for case in read(out/'design.json')['cases']:
        folder=out/case;check=read(folder/'transfer-verification.json');clearance=read(folder/'verification.json');record=read(folder/'transfer-record.json');report=read(folder/'candidate/report.json');variants={}
        for key,label,stage in [('raw_splice','Raw generation + splice','raw-splice'),('pose_splice','Exact native poses + splice','input'),('candidate','Exact poses + mesh correction','candidate')]:
            file=folder/stage/'character.glb';variants[key]=dict(label=label,path=file.relative_to(out).as_posix(),sha256=sha256(file),metrics=check['stages'][key])
        prior=ROOT/'reports/rig-clearance-v3'/('ui-jump-205' if case=='jump-205' else case)
        if (prior/'verification.json').exists():
            file=prior/'candidate/character.glb';variants['previous']=dict(label='Earlier mesh correction',path=os.path.relpath(file,out).replace('\\','/'),sha256=sha256(file),metrics=read(prior/'verification.json')['metrics']['candidate'])
        status='Native boundary poses are accurately fitted; target mapped rotations agree within 0.001°. Target joint positions can differ because transfer uses reference bone offsets instead of the source’s animated translations. '
        if clearance['fixed_frames_prove_whole_clip_floor_infeasible']:status+='The frozen surrounding source frames still penetrate the floor; preserving them makes the whole-clip floor requirement infeasible. '
        convergence=read(folder/'fit-summary.json')['convergence']
        status+=('Solver stopped on a small update; optimality is unproven. ' if convergence['small_update_stopping_rule'] else 'Solver reached its six-sweep limit; convergence is unproven. ')
        status+='Floor and transition checks are separate. No semantic, contact, dynamics or animator approval.'
        files={}
        for directory in ('raw-splice','input','unblended','candidate','implementation'):
            files.update({p.relative_to(folder).as_posix():p for p in (folder/directory).rglob('*') if p.is_file()})
        for name in ('corrected-native.npz','aligned-native.npz','fit.npz','request.json','raw-request.json','spec.json','solver.json','fit-summary.json','verification.json','transfer-verification.json','transfer-record.json'):
            files[name]=folder/name
        files['original-authoring.zip']=ROOT/'reports/rig-jobs'/record['job']/'character-animation.zip'
        note='Experimental pose fitting and target-mesh clearance. No animator, semantic, contact or dynamics approval. Frozen source floor failures and motion regressions remain. Original assets, licenses, raw model output and prompt are retained in original-authoring.zip. Read both verification JSON files before use. Model weights and native extension binaries are not bundled.\n'
        archive=folder/'animation.zip'
        with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
            for name,path in files.items():z.write(path,name)
            z.writestr('README.txt',note)
        with zipfile.ZipFile(archive) as z:
            assert z.testzip() is None
            for name,path in files.items():assert z.read(name)==path.read_bytes()
        packages.append(dict(case=case,entries=len(files)+1,sha256=sha256(archive),source_authoring_sha256=sha256(files['original-authoring.zip'])))
        cases.append(dict(id=case,label=case,frames=report['frames'],root_node=report['root_node'],camera_height_m=.65 if 'jump' in case else .9,variants=variants,status=status,audit=case+'/transfer-verification.json',package=case+'/animation.zip',studio='http://127.0.0.1:8768/studio?rig_job='+record['job']))
    save(out/'review.json',dict(cases=cases,quality_approved=False))
    page=(ROOT/'scripts/clearance-review.html').read_text(encoding='utf8').replace('Strep · Surface clearance study','Strep · Pose fitting and rig clearance')
    page=page.replace('Surface clearance on your character','Pose fitting and mesh clearance on your character')
    page=page.replace('Same generated motion, different correction objectives. Compare foot clearance and sliding together. Failed raw pose guides and original frames outside the editable section remain unchanged.','Compare the original splice, explicit native pose fitting, and bounded target-mesh correction. All stages reuse the same generated motion and preserve the original edit envelope.')
    page=page.replace('Case package','Candidate bundle').replace('../godot-rig-clearance-v3/verification.json','../godot-corrected-rig-transfer-v1/verification.json')
    page=page.replace('Original character licenses and source files are retained in each case package. Grey material is preview-only. No independent animator approval.','Original character licenses and source files remain in the original Studio jobs and their packages. Grey material is preview-only. No independent animator approval.')
    (out/'viewer.html').write_text(page,encoding='utf8')
    save(out/'package-verification.json',dict(packages=packages,all_entries_identical=True))


if __name__=='__main__':build()
