"""Actual native/GLB eligibility and no geometry-promotion semantics."""
import copy,sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_unapproved_anchor import assemble
from native_stored_pair_job import Job
from test_native_stored_pair_job import prepare as prepare_v1
from test_native_static_reference_job import prepare as prepare_v2
from strep import read,save,sha256

def candidate(tmp_path,version=1):
 job_path=prepare_v1(tmp_path) if version==1 else prepare_v2(tmp_path)[0];job=Job(job_path)
 value=job.value.copy();value[0]+=1e-9
 controls=tmp_path/'next-controls.npz';np.savez(controls,controls=value);files={}
 for n in job.edits.actors:
  path=tmp_path/('next-'+n+'.glb');job.edits.export(n,value,path);files[n]=path
 return job_path,job,controls,files

@pytest.mark.parametrize('version',[1,2])
def test_actual_genuine_next_job_preserves_every_original_constraint_and_remains_unapproved(tmp_path,version):
 path,job,controls,files=candidate(tmp_path,version);before={**job.inputs,**{str(p):sha256(p) for p in files.values()},str(controls):sha256(controls)}
 out=tmp_path/'internal';r=assemble(path,controls,files,out)
 next_job=Job(out/'job.json')
 assert {k:v for k,v in next_job.request.items() if k!='anchor'}=={k:v for k,v in job.request.items() if k!='anchor'}
 assert next_job.request['anchor']['corrections']==job.request['anchor']['corrections']
 assert r['native_conditions_pass'] and r['reference_bounds']['passed'] and r['original_native_maximum_excess']<=0
 assert r['original_selected'] and not any(r[k] for k in ('geometry_assessed','geometry_approved','quality_approved','release_approved'))
 for p,h in before.items():assert sha256(p)==h
 original,value_world=job.problem.decoded(files,next_job.value);again,next_world=next_job.problem.decoded(next_job.files,next_job.value)
 np.testing.assert_array_equal(original,again)
 for n in value_world:np.testing.assert_array_equal(value_world[n],next_world[n])
 with pytest.raises(ValueError,match='Fresh'):assemble(path,controls,files,out)

@pytest.mark.parametrize('fault',['zero','outside-trust','shape','nonfinite','bool-controls','missing-array','actors','payload','relative-role'])
def test_invalid_or_false_candidate_rejects_before_output_creation(tmp_path,fault):
 path,job,controls,files=candidate(tmp_path);value=job.value.copy();value[0]+=1e-9
 if fault=='zero':value=job.value.copy()
 elif fault=='outside-trust':value[0]=job.value[0]+.03
 elif fault=='shape':value=value[:-1]
 elif fault=='nonfinite':value[0]=np.nan
 elif fault=='bool-controls':value=np.ones(len(value),bool)
 elif fault=='actors':files['frozen-extra']=next(iter(files.values()))
 elif fault=='payload':
  value[0]=.01
 elif fault=='relative-role':
  r=read(path);r['source_scene']['path']=Path(r['source_scene']['path']).name;save(path,r)
 if fault=='missing-array':np.savez(controls,other=value)
 else:np.savez(controls,controls=value)
 out=tmp_path/'internal'
 with pytest.raises(ValueError):assemble(path,controls,files,out)
 assert not out.exists()

def test_exact_export_that_violates_original_source_rate_is_rejected(tmp_path):
 path,job,controls,files=candidate(tmp_path,2);value=job.value.copy();value[3]=.01
 np.savez(controls,controls=value)
 for n in files:
  files[n]=tmp_path/('violating-'+n+'.glb');job.edits.export(n,value,files[n])
 assert job.edits.audit('A',files['A'],job.scene.actors['A']['animation_index'],value=value)['passed']
 residual,_=job.problem.decoded(files,value);assert np.any(residual>0)
 out=tmp_path/'internal'
 with pytest.raises(ValueError,match='Every original decoded'):assemble(path,controls,files,out)
 assert not out.exists()
