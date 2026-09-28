const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const context=vm.createContext({});
vm.runInContext(fs.readFileSync(path.join(__dirname,'../scripts/rig-result-selection.js'),'utf8'),context);
const select=(...args)=>JSON.parse(JSON.stringify(context.rigResultSelection(...args)));
const contacts=()=>({correction_status:'rejected',variants:{transfer:{label:'Input clip'},corrected:{label:'Contact candidate'},repeated:{label:'Three cycles',source_variant:'corrected'}}});

test('failed finite and repeated corrections remain inspectable; input opens first',()=>{
 const result=contacts(),before=JSON.stringify(result),out=select(result);
 assert.equal(out.selected,'transfer');assert.match(out.message,/retained input/);
 assert.deepEqual(out.options.filter(x=>x.label.includes('Failed checks')).map(x=>x.key),['corrected','repeated']);
 assert.equal(JSON.stringify(result),before);
 for(const key of ['corrected','repeated']){const selected=select(result,key);assert.equal(selected.selected,key);assert.match(selected.message,/failed numerical checks/);}
});
test('passing numerical correction is not labeled quality approved',()=>{
 const result=contacts();result.correction_status='provisional_pass';const out=select(result);
 assert.equal(out.selected,'corrected');assert.match(out.message,/still require review/);assert.match(out.options[1].label,/Numerical screens met/);
 assert.equal(select(result,'transfer').selected,'transfer');
});
test('rejected joint targets fall back to original input; passing targets keep edited result',()=>{
 const result={joint_edit_status:'rejected',variants:{transfer:{label:'Joint target candidate'},input:{label:'Input clip'}}};
 assert.equal(select(result).selected,'input');assert.match(select(result).options[0].label,/Failed checks/);
 result.joint_edit_status='numerical_screens_met';assert.equal(select(result).selected,'transfer');
});
test('event-only descendants preserve failed motion status without inventing a clean fallback',()=>{
 const result={correction_status:'rejected',inherited_correction:{status:'rejected'},variants:{transfer:{label:'Authored markers'},repeated:{label:'Three cycles'}}};
 const out=select(result);assert.equal(out.selected,'transfer');assert.ok(out.options.every(x=>x.status==='rejected'));assert.match(out.message,/failed numerical checks/);
});
test('missing or unknown correction decisions do not silently promote correction',()=>{
 const result=contacts();delete result.correction_status;
 assert.equal(select(result).selected,'transfer');assert.match(select(result,'corrected').message,/unverified/);
 result.correction_status='new_unrecognized_status';assert.equal(select(result).selected,'transfer');
});
test('ordinary finite edits and cycles keep prior selection behavior',()=>{
 const result={variants:{transfer:{label:'Edited clip'},input:{label:'Input clip'}}};
 assert.equal(select(result).selected,'transfer');assert.equal(select(result,'input').selected,'input');assert.equal(select(result,'missing').selected,'transfer');
 assert.equal(select({variants:{transfer:{label:'One cycle'},repeated:{label:'Three cycles'}}},'repeated').selected,'repeated');
});
test('marker-only descendants of rejected joint edits retain visible failure',()=>{
 const result={joint_edit_status:'rejected',inherited_joint_edit:{status:'rejected'},variants:{transfer:{label:'Authored markers'},repeated:{label:'Three cycles'}}};
 const out=select(result);assert.equal(out.selected,'transfer');assert.ok(out.options.every(x=>x.status==='rejected'));assert.match(out.message,/failed numerical checks/);
});
test('root cleanup retains original failures on both versions and opens its input',()=>{
 for(const name of ['20260928-103008-a6626ded','20260928-103756-eebe5435','20260928-104001-895f20da','20260928-105143-aed550d4','20260928-105220-0d84b0dc']){
  const result=JSON.parse(fs.readFileSync(path.join(__dirname,'../reports/rig-jobs',name,'result.json'),'utf8'));
  const out=select(result);assert.equal(out.selected,'input');
  assert.ok(out.options.every(x=>x.status===result.correction_status));
  assert.equal(select(result,'transfer').selected,'transfer');
  assert.ok(out.options.every(x=>!x.label.includes('Numerical screens met')));
 }
});
