import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {correctionRequest,createMeshCharacterEditor,diagnosticLines} from '../scripts/mesh-character-editor.mjs';
const job='a'.repeat(32),digest='b'.repeat(64),fit='c'.repeat(32);
let scene={job,request:{schema:'strep-studio-mesh-scene-v1',draft:{scene:{actors:{A:{sha256:'d'.repeat(64)}}}}}};
let bounds={schema:'strep-studio-native-scene-fit-v1',draft:structuredClone(scene.request.draft),actors:{A:{tracks:[{node:0,path:'translation',maximum_change:.02}]}},options:{iterations:4},resume_from:null};
assert.deepEqual(correctionRequest(job,digest,scene.request,bounds,[],false).editable_clip_boundaries,{A:[]});
assert.equal(correctionRequest(job,digest,scene.request,bounds,[],false).recoverable,true);
for(const seconds of [900,1800,3600])assert.equal(correctionRequest(job,digest,scene.request,bounds,[],false,seconds).max_runtime_seconds,seconds);
for(const seconds of [true,0,901,Infinity,'3600'])assert.throws(()=>correctionRequest(job,digest,scene.request,bounds,[],false,seconds),/processing time/);
assert.throws(()=>correctionRequest(job,digest,scene.request,bounds,['start'],false),/Acknowledge/);
for(const modified of [{...bounds,resume_from:'old'},{...bounds,rotation_speed_limits:[]},{...bounds,schema:'strep-studio-native-scene-fit-v3'}])assert.throws(()=>correctionRequest(job,digest,scene.request,modified,[],false),/fresh/);
assert.throws(()=>correctionRequest(job,digest,scene.request,{...bounds,draft:{}},[],false),/exact scene/);
class Element{constructor(){this.value='';this.checked=false;this.children=[];}replaceChildren(...values){this.children=values;}append(...values){this.children.push(...values);}}
const html=await readFile(new URL('../scripts/mesh-character-editor.html',import.meta.url),'utf8'),nodes=new Map();
for(const [,id] of html.matchAll(/id="([^"]+)"/g)){assert(!nodes.has(id));nodes.set(id,new Element());}
const document={getElementById:id=>nodes.get(id),createElement:()=>new Element()},el=n=>nodes.get('meshCharacter'+n),posted=[];
assert.match(html,/<option value="3600" selected>/);el('TimeLimit').value='3600';
let wait=null,jobWait=null,report={id:fit,status:'complete',original_selected:true,quality_approved:false,release_approved:false,result:{accepted_steps:1,probes:2,candidate:'probe-000',sampled_candidate_pass:false,original_selected:true,quality_approved:false,release_approved:false},comparison_url:`/mesh-character-viewer.html?job=${fit}&result=${digest}`,download_url:`/files/mesh-character-jobs/${fit}/correction-package.zip`};
const saved={id:job,status:'complete',original_selected:true,quality_approved:false,preview_url:`/mesh-scene-viewer.html?job=${job}&result=${digest}`};
createMeshCharacterEditor({document,api:async url=>url.includes('/mesh-scene-jobs/')?(wait||structuredClone(saved)):(jobWait||structuredClone(report)),post:async(url,payload)=>{posted.push({url,payload});return {id:fit};},getScene:()=>structuredClone(scene),getBounds:()=>structuredClone(bounds)});
await el('Build').onclick();assert.equal(posted[0].url,'/api/mesh-character-jobs');assert.deepEqual(posted[0].payload.editable_clip_boundaries,{A:[]});assert.equal(el('Job').value,fit);
assert.equal(posted[0].payload.max_runtime_seconds,3600);assert.match(el('Status').textContent,/60-minute/);
el('Start').checked=true;await el('Build').onclick();assert.match(el('Status').textContent,/Acknowledge/);assert.equal(posted.length,1);
el('Ack').checked=true;await el('Build').onclick();assert.deepEqual(posted[1].payload.editable_clip_boundaries,{A:['start']});
await el('Review').onclick();assert.match(el('Status').textContent,/still fails/);assert.equal(el('Results').children.length,2);
const diagnostic={schema:'strep-studio-mesh-diagnostics-v1',available:true,attempts:2,accepted:1,quality_approved:false,release_approved:false,
 checks:Array.from({length:10},(_,i)=>({key:`check-${i}`,label:i===9?'Avoiding worse body self-intersections':`Check ${i}`,passed:0,failed:1,not_checked:1,not_recorded:0}))};
report.diagnostics=structuredClone(diagnostic);await el('Review').onclick();assert.equal(el('Results').children.length,3);
const detail=el('Results').children[2];assert.equal(detail.children[0].textContent,'View attempt checks');
assert.match(detail.children[1].textContent,/including rejected proposals/);
assert.match(detail.children[2].children[9].textContent,/1 failed, 1 not checked, 0 not recorded/);
for(const mutate of [s=>s.checks[0].passed++,s=>s.checks[0].failed=true,s=>s.checks[1].key=s.checks[0].key,s=>s.attempts++,s=>s.quality_approved=true,s=>s.checks.pop()]){
 const invalid=structuredClone(diagnostic);mutate(invalid);assert.throws(()=>diagnosticLines(invalid,report.result));}
report.diagnostics={schema:diagnostic.schema,available:false,quality_approved:false,release_approved:false};
await el('Review').onclick();assert.match(el('Results').children[2].children[2].children[0].textContent,/not included/);
delete report.diagnostics;
report.result.candidate=null;await el('Review').onclick();assert.match(el('Status').textContent,/No improved candidate/);
report.result.sampled_candidate_pass=true;report.result.candidate='probe-001';await el('Review').onclick();assert.match(el('Status').textContent,/passes declared sampled/);
report.comparison_url='https://elsewhere.test';await el('Review').onclick();assert.match(el('Status').textContent,/Unexpected/);
let resolve;wait=new Promise(r=>resolve=r);const pending=el('Build').onclick();bounds.options.iterations=5;resolve(saved);await pending;assert.match(el('Status').textContent,/changed/);assert.equal(posted.length,2);
wait=new Promise(r=>resolve=r);const changingTime=el('Build').onclick();el('TimeLimit').value='1800';resolve(saved);await changingTime;assert.match(el('Status').textContent,/changed/);assert.equal(posted.length,2);
wait=null;await el('Build').onclick();assert.equal(posted[2].payload.max_runtime_seconds,1800);assert.match(el('Status').textContent,/30-minute/);
report.max_runtime_seconds=3600;report.status='processing';await el('Review').onclick();assert.match(el('Status').textContent,/60-minute limit/);
assert.equal(el('Continue').disabled,true);
report.status='failed';report.error='Execution limit reached';report.recoverable=true;report.can_continue=true;
report.continuation={attempt:'e'.repeat(32),progress:{request_sha256:digest,checkpoint:{checkpoint:'checkpoints/saved.json',sha256:'f'.repeat(64)}}};
await el('Review').onclick();assert.equal(el('Continue').disabled,false);assert.match(el('Status').textContent,/saved scene and bounds/);
const ticket=structuredClone(report.continuation);el('TimeLimit').value='900';bounds.options.iterations=9;
await el('Continue').onclick();assert.equal(posted.at(-1).url,`/api/mesh-character-jobs/${fit}/continue`);
assert.deepEqual(posted.at(-1).payload,ticket);assert.match(el('Status').textContent,/Continuing the saved correction/);assert.equal(el('Continue').disabled,true);
await el('Review').onclick();const count=posted.length;report.continuation.progress.checkpoint.sha256='0'.repeat(64);
await el('Continue').onclick();assert.equal(posted.length,count);assert.match(el('Status').textContent,/progress changed/);
jobWait=new Promise(r=>resolve=r);const reviewing=el('Review').onclick();el('Job').value='1'.repeat(32);el('Job').oninput();resolve(structuredClone(report));await reviewing;
assert.match(el('Status').textContent,/selection or scope changed/);assert.equal(el('Continue').disabled,true);
jobWait=null;el('Job').value=fit;report.recoverable=false;delete report.can_continue;delete report.continuation;
await el('Review').onclick();assert.equal(el('Continue').disabled,true);assert.equal(posted.length,count);
console.log('Mesh character editor: exact saved bounds, immutable-budget continuation, stale progress/selection rejection and honest original/candidate review pass.');
