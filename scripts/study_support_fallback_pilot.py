"""Declared full-clip trial of original-priority support backtracking."""
import argparse
import ast
import gc
from pathlib import Path
import shutil
import sys
import traceback
import numpy as np
import psutil
from scipy.spatial.transform import Rotation
from threadpoolctl import threadpool_limits
from strep import ROOT,read,save,sha256,now
from audit_authoring_intent import check_files
from compare_midpoint_support import verified
from coupled_support_context import context
from midpoint_support_block import MidpointCoupledBlock
from support_backtracking_fallback import solve
from rig_loop import encode
from verify_coupled_support import inspect
from run_godot_rig_import import run as engine
from study_whole_support_breadth import check_engine


def freeze(output):
    dest=output/'implementation';dest.mkdir();pending=[Path(__file__).name];seen=set()
    while pending:
        name=pending.pop()
        if name in seen:continue
        seen.add(name);path=ROOT/'scripts'/name;shutil.copyfile(path,dest/name)
        for node in ast.walk(ast.parse(path.read_text(encoding='utf-8-sig'))):
            modules=[node.module] if isinstance(node,ast.ImportFrom) else [a.name for a in node.names] if isinstance(node,ast.Import) else []
            for module in modules:
                child=(module or '').split('.')[0]+'.py'
                if (ROOT/'scripts'/child).exists():pending.append(child)
    shutil.copyfile(ROOT/'scripts/godot_import_audit.gd',dest/'godot_import_audit.gd');seen.add('godot_import_audit.gd')
    return {n:sha256(dest/n) for n in sorted(seen)}


def planned_cases(protocol,complete,all_targeted=False):
    cases=protocol['cases'];ids=[c['id'] for c in cases]
    rows=complete['rows'];row_ids=[r['id'] for r in rows]
    if len(set(ids))!=len(ids) or row_ids!=ids:
        raise ValueError('Reference population must be complete, unique and in protocol order')
    selected=[c['id'] for c in cases if c['eligible']] if all_targeted else ['motion-036-rig-02','motion-031-rig-02']
    if not selected or any(c not in ids for c in selected):
        raise ValueError('Declared trial cases are absent from reference')
    # Retained and failed reference candidates remain in a full population trial.
    # Their outcome is recorded by the normal per-case path, never silently omitted.
    return selected


def run(source,output,all_targeted=False):
    protocol,complete=verified(source)
    if output.exists():raise ValueError('Preserve prior pilot')
    selected=planned_cases(protocol,complete,all_targeted)
    if protocol['steps_per_block']!=12 or protocol['fractions']!=[1.,.5,.25,.125] or not protocol['midpoint_constraints']:
        raise ValueError('Expected completed twelve-step original-search reference')
    output.mkdir(parents=True);process=psutil.Process()
    save(output/'runner.json',dict(pid=process.pid,created=process.create_time()))
    implementation=freeze(output)
    save(output/'protocol.json',dict(at=now(),source=str(source),source_completion_sha256=sha256(source/'completion.json'),
        population=protocol['cases'],pilot_cases=selected,steps_per_block=12,trusts=protocol['trusts'],
        selection_mode='all_reference_targets' if all_targeted else 'two_case_pilot',
        search_order='original_then_fallback',implementation=implementation,quality_approved=False,
        scope=f'{len(selected)} declared development cases from the complete {len(protocol["cases"])}-row reference; all other cases explicitly unprobed. Recompute conic directions, export whole clips, retain all failures and check all three versions in Godot.'))
    def phase(status,**fields):
        save(output/'pipeline.json',dict(at=now(),status=status,**fields));print(status,fields,flush=True)
    def validate():
        check_files(ROOT/'scripts',implementation);check_files(output/'implementation',implementation)
        if sha256(source/'completion.json')!=read(output/'protocol.json')['source_completion_sha256']:raise ValueError('Reference completion changed')
        if sha256(ROOT/'reports/conic-solver-bootstrap-v1.json')!=protocol['solver_bootstrap_sha256']:raise ValueError('Conic solver binding changed')
    rows=[];engine_cases=[]
    with threadpool_limits(limits=1):
        for case in protocol['cases']:
            row={k:case[k] for k in ['id','family','action','rig']};row['status']='not_probed'
            if case['id'] not in selected:rows.append(row);continue
            folder=output/case['id'];folder.mkdir();base=folder/'base'
            shutil.copytree(source/case['id']/'base',base);check_files(base,case['files'])
            ctx=None
            try:
                if next(r for r in complete['rows'] if r['id']==case['id'])['status']!='candidate_preserved':
                    raise ValueError('Pilot requires a retained earlier candidate')
                validate();phase('context',case=case['id']);ctx=context(base,base/'selected/character.glb')
                reference_selection=read(source/case['id']/'selection.json')
                if reference_selection['blocks']!=ctx['selection']:raise ValueError('Editing windows changed')
                save(folder/'selection.json',reference_selection)
                values=ctx['initial'].copy();logs=[];edited=set()
                for index,target in enumerate(ctx['selection']):
                    phase('fitting',case=case['id'],block=index+1)
                    problem=MidpointCoupledBlock(ctx['fitter'],ctx['oracle'],values,ctx['source_world'],ctx['source_points'],target['frames'],ctx['envelope'],ctx['targets'])
                    values,log=solve(problem,steps=12,trusts=tuple(protocol['trusts']))
                    logs.append(dict(target=target,solver=log));edited.update(target['frames']);save(folder/'solver.json',dict(blocks=logs));del problem
                np.savez_compressed(folder/'parameters.npz',initial=ctx['initial'],parameters=values)
                take=folder/'take';take.mkdir();shutil.copytree(base/'input',take/'input')
                for name in ['spec.json','request.json']:shutil.copyfile(base/name,take/name)
                shutil.copyfile(base/'traces.json',take/'raw-traces.json');dest=take/'candidate';dest.mkdir()
                world=np.array([ctx['fitter'].pose(f,v)[0] for f,v in enumerate(values)])
                phase('exporting',case=case['id']);root=ctx['fitter'].spec['root_node']
                times,export=encode(ctx['fitter'].rig,world,set(ctx['oracle'].animated),root,dest/'character.glb','Original-priority fallback development trial')
                save(dest/'root-motion.json',dict(node=root,times_s=times.tolist(),positions_m=world[:,root,:3,3].tolist(),rotations_xyzw=Rotation.from_matrix(world[:,root,:3,:3]).as_quat().tolist()))
                shutil.copyfile(base/'input/contacts.json',dest/'contacts.json')
                phase('verifying',case=case['id']);audit=inspect(take,base/'selected/character.glb',sorted(edited));save(folder/'audit.json',audit)
                previous=read(source/case['id']/'audit.json')
                if [f['side'] for f in previous['feet']]!=[f['side'] for f in audit['feet']]:raise ValueError('Foot comparison order changed')
                row.update(status='evaluated',candidate_passes_common_input=audit['passed'],candidate_sha256=sha256(dest/'character.glb'),
                    earlier_energy=previous['foot_speed_excess_energy_after'],candidate_energy=audit['foot_speed_excess_energy_after'],
                    energy_delta=audit['foot_speed_excess_energy_after']-previous['foot_speed_excess_energy_after'],export=export,
                    foot_peak_changes={a['side']:b['support_peak_after_m_s']-a['support_peak_after_m_s'] for a,b in zip(previous['feet'],audit['feet'])})
                for label,path in [('common-input',base/'selected/character.glb'),('earlier',source/case['id']/'selected/character.glb'),('candidate',dest/'character.glb')]:
                    engine_cases.append(dict(id=case['id']+'-'+label,path=str(path),sha256=sha256(path),frames=ctx['fitter'].spec['frames'],fps=30,sample_by_time=True))
                check_files(base,case['files'])
            except Exception as error:
                row.update(status='failed',error=str(error),traceback=traceback.format_exc())
            save(folder/'result.json',row);rows.append(row);save(output/'results.json',dict(rows=rows));phase('case_complete',case=case['id'],outcome=row['status'])
            del ctx;gc.collect()
    save(output/'results.json',dict(rows=rows));validate();save(output/'manifest.json',dict(cases=engine_cases))
    frames=0
    if engine_cases:
        phase('engine',clips=len(engine_cases));engine(output,output/'engine');frames=check_engine(read(output/'engine/verification.json'),engine_cases)
    validate();check_files(source,complete['files'])
    save(output/'completion.json',dict(at=now(),rows=rows,protocol_sha256=sha256(output/'protocol.json'),engine_actor_frames=frames,
        engine_verification_sha256=sha256(output/'engine/verification.json') if frames else None,
        files={p.relative_to(output).as_posix():sha256(p) for p in output.rglob('*') if p.is_file() and 'implementation' not in p.parts and 'engine' not in p.parts and p.name not in ('pipeline.json','completion.json')},
        quality_approved=False,scope=f'{len(selected)} full-clip development trials; {len(rows)}-row population preserved with {len(rows)-len(selected)} unprobed. No quarter-frame/baseline pointwise audit or human approval yet.'))
    phase('complete',engine_actor_frames=frames)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('source',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--all-targeted',action='store_true')
    a=p.parse_args();run(a.source.resolve(),a.output.resolve(),a.all_targeted)
