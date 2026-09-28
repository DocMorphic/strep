"""Package measured correction candidates and create a synchronized review."""
import os
import shutil
import zipfile
from strep import ROOT,read,save,sha256


def build():
    out=ROOT/'reports/rig-clearance-v3';cases=[];manifest=[];packages=[]
    for name,job in read(out/'design.json')['cases'].items():
        folder=out/name;check=read(folder/'verification.json');request=read(folder/'request.json');report=read(folder/'candidate/report.json')
        variants={}
        def add(key,label,file,metrics):
            variants[key]=dict(label=label,path=os.path.relpath(file,out).replace('\\','/'),sha256=sha256(file),metrics=metrics)
            manifest.append(dict(id=name+'-'+key,path=variants[key]['path'],sha256=sha256(file),frames=report['frames'],fps=30))
        add('input','Before correction',folder/'input/character.glb',check['metrics']['input'])
        old=ROOT/'reports/rig-clearance-v2'/name
        if (old/'verification.json').exists():
            add('height_only','Height only · sliding regression',old/'candidate/character.glb',read(old/'verification.json')['metrics']['candidate'])
        add('candidate','Height + horizontal surface fit',folder/'candidate/character.glb',check['metrics']['candidate'])
        archive=folder/'animation.zip';original=ROOT/'reports/rig-jobs'/job/'character-animation.zip'
        expected={}
        for directory in ('candidate','implementation'):
            expected.update({p.relative_to(folder).as_posix():p for p in (folder/directory).rglob('*') if p.is_file()})
        for filename in ('request.json','spec.json','solver.json','fit-summary.json','verification.json'):
            expected[filename]=folder/filename
        expected['source-authoring.zip']=original
        note='Experimental surface-clearance candidate. No motion quality approval. Original source, model generation, character licenses and unchanged source clip are in source-authoring.zip. Read verification.json and fit-summary.json: frozen-frame floor failures, raw guide failures and solver limits remain. Model weights are not included.\n'
        with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
            for name_in_zip,path in expected.items():z.write(path,name_in_zip)
            z.writestr('README.txt',note)
        with zipfile.ZipFile(archive) as z:
            assert z.testzip() is None
            for name_in_zip,path in expected.items():assert z.read(name_in_zip)==path.read_bytes()
        packages.append(dict(case=name,path=archive.relative_to(out).as_posix(),sha256=sha256(archive),entries=len(expected)+1,source_authoring_sha256=sha256(original)))
        status='Experimental candidate: raw model boundary guides still fail. '
        if check['fixed_frames_prove_whole_clip_floor_infeasible']:
            status+='The fixed surrounding frames penetrate the floor by '+f"{check['metrics']['candidate']['frozen_floor_depth_max_m']*1000:.2f} mm"+'; clearing the whole clip requires changing those frames or choosing another source. '
        else:status+='Sampled floor screen passes, but this does not establish acceptable action or transition quality. '
        status+='Solver bounds and preserved frames verified; animator review is pending.'
        cases.append(dict(id=name,label=('Jump · Cesium · seed '+name.split('-')[-1]) if 'jump' in name else 'Dance · Quaternius · seed 203',frames=report['frames'],root_node=report['root_node'],camera_height_m=.65 if 'jump' in name else .9,variants=variants,status=status,audit=name+'/verification.json',package=name+'/animation.zip',studio='http://127.0.0.1:8768/studio?rig_job='+job))
    save(out/'manifest.json',dict(cases=manifest));save(out/'review.json',dict(cases=cases,quality_approved=False));save(out/'package-verification.json',dict(packages=packages,all_entries_identical=True))
    shutil.copyfile(ROOT/'scripts/clearance-review.html',out/'viewer.html')


if __name__=='__main__':build()
