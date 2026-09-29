"""Publish an audited single-actor scene fit to the existing Studio scene viewer.

Failed contact/clearance checks remain visible. Packaging is not human review.
"""
import argparse
import copy
import shutil
from pathlib import Path
import numpy as np
from strep import ROOT,read,save,sha256,now
from build_soma_preview import ASSET
from scene_constraints import evaluate
from scene_region_job import JOBS,audit_summary,bundle


def include_rate_diagnostics(summary, report):
    """Keep local increases visible even when global maxima both decrease."""
    diagnostics={}
    for rate,item in report['rates'].items():
        windows=item['windows'];whole=next(w for w in windows if w['window']=='whole_clip')
        local=sum(j['candidate_peak']>j['source_peak']+1e-5 for j in whole['joints'])
        increased=[w['window'] for w in windows if w['samples'] and w['candidate_peak']>w['source_peak']+1e-5]
        diagnostics[rate]=dict(increased_joint_peaks=local,increased_window_peaks=increased)
        if local:summary['motion_regressions'].append('per_joint_peak_'+rate)
        if increased:summary['motion_regressions'].append('phase_or_boundary_peak_'+rate)
    summary['rate_diagnostics']=diagnostics
    summary['rate_diagnostic_scope']='1e-5 reporting allowance in the recorded rate units; no calibrated quality acceptance threshold.'
    return summary


def verified_study(study,audit_path,engine_path):
    study=Path(study);result=read(study/'result.json');audit=read(audit_path);engine=read(engine_path)
    if result.get('status')!='complete' or audit['result_sha256']!=sha256(study/'result.json'):
        raise ValueError('Completed fit and matching independent audit required')
    for name,key in [('protocol.json','protocol_sha256'),('authored-scene.json','authored_scene_sha256'),
                     ('recipe.json','recipe_sha256'),('source.glb','source_glb_sha256'),
                     ('candidate.glb','candidate_glb_sha256'),('motion.npz','candidate_sha256')]:
        if sha256(study/name)!=result[key]:raise ValueError('Audited fit artifact changed: '+name)
    if audit['protocol_sha256']!=result['protocol_sha256']:raise ValueError('Audit protocol mismatch')
    scene=read(study/'authored-scene.json')
    for label in ['source','candidate']:
        digest=result[label+'_glb_sha256']
        if audit['variants'][label]['glb_sha256']!=digest:raise ValueError('Audit export mismatch')
        if not any(c['source_sha256']==digest and c['frames']==scene['frame_count'] and c['bones']==77 for c in engine['checks']):
            raise ValueError('Missing matching full-frame engine evidence')
    protocol=read(study/'protocol.json');actor=protocol['actor']
    if set(scene['actors'])!={actor}:raise ValueError('This review publisher requires an independently audited single-actor scene')
    source=ROOT/scene['actors'][actor]['motion']
    if sha256(study/'source-motion.npz')!=sha256(source):raise ValueError('Preserved source motion changed')
    if scene['actors'][actor].get('source_sha256')!=sha256(source):raise ValueError('Authored source hash mismatch')
    for path,digest in protocol['inputs'].items():
        if sha256(path)!=digest:raise ValueError('Original fit input changed')
    return scene,actor,audit


def build(study,audit_path,engine_path,output,label,rates_path=None):
    study,audit_path,engine_path,output=map(lambda p:Path(p).resolve(),[study,audit_path,engine_path,output])
    if output.parent!=JOBS.resolve() or output.exists():raise ValueError('Fresh scene-region-jobs review directory required')
    if not isinstance(label,str) or not 1<=len(label.strip())<=120:raise ValueError('Review label required')
    scene,actor,audit=verified_study(study,audit_path,engine_path)
    if rates_path is not None:
        rates_path=Path(rates_path).resolve()
        if read(rates_path)['result_sha256']!=sha256(study/'result.json'):raise ValueError('Joint-rate report belongs to another fit')
    skin=dict(np.load(ASSET,allow_pickle=False));summary=audit_summary(audit)
    if rates_path is not None:include_rate_diagnostics(summary,read(rates_path))
    output.mkdir(parents=True);scenes=[]
    for version,motion_file in [('source','source-motion.npz'),('candidate','motion.npz')]:
        folder=output/version;folder.mkdir()
        shutil.copyfile(study/motion_file,folder/'motion.npz');shutil.copyfile(study/(version+'.glb'),folder/'actor.glb')
        authored=copy.deepcopy(scene);entry=authored['actors'][actor]
        entry.update(motion=(folder/'motion.npz').relative_to(ROOT).as_posix(),source_sha256=sha256(folder/'motion.npz'),
                     preview_glb=version+'/actor.glb')
        assessment=evaluate(authored,skin);data=bundle(authored,assessment,skin)
        if version=='candidate':data['region_fit']=summary
        save(output/(version+'.json'),data)
        note=('Preserved original input.' if version=='source' else
              ('Sampled contact/clearance pass.' if summary['contact_geometry_passed'] else 'Contact or clearance checks fail.'))
        note+=' Developer review pending; no motion-quality approval.'
        scenes.append(dict(id=version,label=label.strip()+' · '+version.title(),variants=dict(palm=version+'.json'),review_note=note,
                           downloads=[dict(label='Animated GLB',path=version+'/actor.glb'),
                                      dict(label='Native motion',path=version+'/motion.npz'),
                                      dict(label='Independent geometry audit',path='geometry-audit.json'),
                                      dict(label='Godot import checks',path='engine-audit.json')]))
    if rates_path is not None:
        shutil.copyfile(rates_path,output/'joint-rates.json')
        for row in scenes:row['downloads'].append(dict(label='Per-joint and boundary rates',path='joint-rates.json'))
    shutil.copyfile(audit_path,output/'geometry-audit.json');shutil.copyfile(engine_path,output/'engine-audit.json')
    shutil.copyfile(ROOT/'vendor/kimodo/LICENSE',output/'SOMA-preview-LICENSE.txt')
    save(output/'manifest.json',dict(scenes=scenes,quality_approved=False,review_mode='unblinded_developer_comparison'))
    shutil.copyfile(__file__,output/'package_scene_fit_review.py')
    save(output/'provenance.json',dict(at=now(),study=str(study),result_sha256=sha256(study/'result.json'),
         geometry_audit_sha256=sha256(audit_path),engine_audit_sha256=sha256(engine_path),packager_sha256=sha256(__file__),
         files={p.relative_to(output).as_posix():sha256(p) for p in sorted(output.rglob('*')) if p.is_file()},
         quality_approved=False,scope='Copied source and candidate assets with unchanged object tracks, contact targets and limits. Developer comparison, not blind human evidence or a new fit.'))
    save(output/'pipeline.json',dict(status='complete',stage='Ready for developer comparison',assessment=summary,quality_approved=False))
    print(dict(collection=output.relative_to(ROOT/'reports').as_posix(),assessment=summary),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('study',type=Path);p.add_argument('audit',type=Path);p.add_argument('engine',type=Path)
    p.add_argument('output',type=Path);p.add_argument('--label',required=True)
    p.add_argument('--rates',type=Path)
    a=p.parse_args();build(a.study,a.audit,a.engine,a.output,a.label,a.rates)
