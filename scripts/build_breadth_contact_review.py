"""Package completed paired corrections without changing the running study."""
import argparse
import os
from pathlib import Path
import shutil
import zipfile
from strep import ROOT,read,save,sha256,now


def build(study,output):
    study,output=Path(study).resolve(),Path(output).resolve()
    from study_breadth_contact import validate
    protocol=validate(study);results=read(study/'results.json')
    if output.exists():raise ValueError('Preserve earlier review snapshot')
    output.mkdir(parents=True);cases=[];exports=[];packages=[];population=[]
    for case in protocol['cases']:
        rows={r['method']:r for r in results['rows'] if r['case']==case['id']}
        group=next((g for g in results['engine_groups'] if g['case']==case['id']),None)
        ready=all(rows[m]['status']=='complete' for m in protocol['methods']) and group and group['status']=='complete'
        population.append(dict(id=case['id'],seed=case['motion']['seed'],rig=case['rig'],statuses={m:r['status'] for m,r in rows.items()},paired_engine_checked=bool(ready)))
        if not ready:continue
        folder=output/case['id'];folder.mkdir()
        baseline=Path(case['source']);report=read(baseline/'report.json');variants={}
        proof=group['proof'];engine_ids={c['id']:c for c in proof['checks']}
        if set(engine_ids)!={case['id']+'-'+s for s in ['input',*protocol['methods']]}:raise ValueError('Engine population mismatch')
        save(folder/'engine-verification.json',proof)
        source=folder/'source';source.mkdir();shutil.copyfile(report['source'],source/'motion.npz')
        if sha256(source/'motion.npz')!=case['motion']['source_sha256']:raise ValueError('Native source changed')
        fixture=ROOT/'reports/breadth-transfer-v1/rigs'/case['rig'];shutil.copytree(fixture,source/'character')
        for name in ['protocol.json','freeze.json']:
            shutil.copyfile(study/name,source/('study-'+name))
        shutil.copytree(study/'implementation',source/'implementation')
        paired={}
        for method in protocol['methods']:
            run=study/'takes'/(case['id']+'-'+method);verify=read(run/'verification.json')
            if verify!=rows[method]['verification']:raise ValueError('Result verification changed')
            if sha256(run/'candidate/character.glb')!=verify['candidate_sha256'] or sha256(run/'input/character.glb')!=verify['source_sha256']:raise ValueError('Candidate/source changed')
            paired[method]=verify
            for name in ['request.json','spec.json','solver.json','fit-summary.json','verification.json']:
                dest=folder/'evidence'/method;dest.mkdir(parents=True,exist_ok=True);shutil.copyfile(run/name,dest/name)
        save(folder/'comparison.json',dict(methods=paired,quality_approved=False,human_review=None))
        sources={'input':baseline,**{m:study/'takes'/(case['id']+'-'+m)/'candidate' for m in protocol['methods']}}
        labels={'input':'Original transfer','clearance':'Clearance only','support':'Clearance + predicted support'}
        for key,src in sources.items():
            dest=folder/key;dest.mkdir()
            for name in ['character.glb','root-motion.json','contacts.json','rig-profile.json','inventory.json']:
                shutil.copyfile(src/name,dest/name)
            shutil.copyfile(src/'report.json',dest/'original-report.json')
            metrics=paired['clearance']['metrics']['input'] if key=='input' else paired[key]['metrics']['candidate']
            digest=sha256(dest/'character.glb')
            if engine_ids[case['id']+'-'+key]['source_sha256']!=digest:raise ValueError('Engine proof not bound to packaged clip')
            # Baseline report fields copied by the experiment can describe the
            # old clip. Ship a small canonical summary from the decoded audit.
            save(dest/'report.json',dict(schema='strep-correction-review-v1',glb_sha256=digest,frames=report['frames'],fps=30,
                root_node=report['root_node'],source_motion_sha256=case['motion']['source_sha256'],source_character_sha256=report['character_sha256'],
                method=key,metrics=metrics,engine_transform_check=engine_ids[case['id']+'-'+key],quality_approved=False,human_review=None,
                original_report='original-report.json',original_report_warning='Preserved historical report may include inherited pre-correction floor/contact diagnostics. Use this report and evidence/*/verification.json for actual decoded measurements.'))
            relative=(dest/'character.glb').relative_to(output).as_posix()
            variants[key]=dict(label=labels[key],path=relative,sha256=digest,metrics=metrics)
            exports.append(dict(id=case['id']+'-'+key,path=relative,sha256=digest,frames=report['frames'],fps=30))
        package=output/(case['id']+'.zip');files=[p for p in folder.rglob('*') if p.is_file()]
        note='Experimental paired correction, not animator-approved. Original source motion and licensed character fixtures, both fitted candidates and all solver/audit evidence are included. Canonical stage report.json uses decoded measurements; original-report.json retains historical metadata and may contain stale baseline metrics. Model weights are not included. No whole-study, semantic, physics or commercial redistribution permission is implied.\n'
        with zipfile.ZipFile(package,'w',zipfile.ZIP_DEFLATED) as archive:
            for file in files:archive.write(file,file.relative_to(folder).as_posix())
            archive.writestr('README.txt',note)
        with zipfile.ZipFile(package) as archive:
            if archive.testzip() is not None:raise ValueError('Archive CRC failed')
            for file in files:
                if archive.read(file.relative_to(folder).as_posix())!=file.read_bytes():raise ValueError('Package byte mismatch')
        packages.append(dict(case=case['id'],path=package.name,sha256=sha256(package),entries=len(files)+1))
        sweeps={m:read(folder/'evidence'/m/'fit-summary.json')['convergence']['sweeps'] for m in protocol['methods']}
        status=f'Experimental clip; source motion and both corrections retained. Solver sweeps: clearance {sweeps["clearance"]}, support {sweeps["support"]}, with a six-sweep budget; no stationary-point or realism claim. Support predictions remain unconfirmed. This paired result cannot establish reliability across other seeds or rigs.'
        rig_label=next(r['label'] for r in read(ROOT/'reports/breadth-transfer-v1/protocol.json')['rigs'] if r['id']==case['rig'])
        cases.append(dict(id=case['id'],label=rig_label+' · jab-cross-retreat · seed '+str(case['motion']['seed']),frames=report['frames'],root_node=report['root_node'],camera_height_m=.9,variants=variants,status=status,
            audit=case['id']+'/comparison.json',package=package.name,engine=case['id']+'/engine-verification.json',license=case['id']+'/source/character/LICENSE.md'))
    if not cases:raise ValueError('No completed engine-verified pairs in snapshot')
    save(output/'population.json',dict(at=now(),planned_pairs=len(protocol['cases']),planned_candidates=protocol['planned_candidates'],completed_pairs=len(cases),cases=population,quality_approved=False))
    save(output/'review.json',dict(at=now(),cases=cases,population=population,planned_pairs=len(protocol['cases']),quality_approved=False))
    save(output/'manifest.json',dict(cases=exports));save(output/'package-verification.json',dict(packages=packages,all_entries_byte_verified=True))
    shutil.copyfile(ROOT/'scripts/breadth-contact-review.html',output/'viewer.html')
    return len(cases)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--study',type=Path,default=ROOT/'reports/breadth-contact-v1');p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();print(build(a.study,a.output))
