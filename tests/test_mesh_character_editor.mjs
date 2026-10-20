import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {correctionRequest,createMeshCharacterEditor} from '../scripts/mesh-character-editor.mjs';
const job='a'.repeat(32),digest='b'.repeat(64),fit='c'.repeat(32);
let scene={job,request:{schema:'strep-studio-mesh-scene-v1',draft:{scene:{actors:{A:{sha256:'d'.repeat(64)}}}}}};
let bounds={schema:'strep-studio-native-scene-fit-v1',draft:structuredClone(scene.request.draft),actors:{A:{tracks:[{node:0,path:'translation',maximum_change:.02}]}},options:{iterations:4},resume_from:null};
assert.deepEqual(correctionRequest(job,digest,scene.request,bounds,[],false).editable_clip_boundaries,{A:[]});
assert.throws(()=>correctionRequest(job,digest,scene.request,bounds,['start'],false),/Acknowledge/);
for(const modified of [{...bounds,resume_from:'old'},{...bounds,rotation_speed_limits:[]},{...bounds,schema:'strep-studio-native-scene-fit-v3'}])assert.throws(()=>correctionRequest(job,digest,scene.request,modified,[],false),/fresh/);
assert.throws(()=>correctionRequest(job,digest,scene.request,{...bounds,draft:{}},[],false),/exact scene/);
class Element{constructor(){this.value='';this.checked=false;this.children=[];}replaceChildren(...values){this.children=values;}append(...values){this.children.push(...values);}}
const html=await readFile(new URL('../scripts/mesh-character-editor.html',import.meta.url),'utf8'),nodes=new Map();
for(const [,id] of html.matchAll(/id="([^"]+)"/g)){assert(!nodes.has(id));nodes.set(id,new Element());}
const document={getElementById:id=>nodes.get(id),createElement:()=>new Element()},el=n=>nodes.get('meshCharacter'+n),posted=[];
let wait=null,report={id:fit,status:'complete',original_selected:true,quality_approved:false,release_approved:false,result:{accepted_steps:1,probes:2,candidate:'probe-000',sampled_candidate_pass:false,original_selected:true,quality_approved:false,release_approved:false},comparison_url:`/mesh-character-viewer.html?job=${fit}&result=${digest}`,download_url:`/files/mesh-character-jobs/${fit}/correction-package.zip`};
const saved={id:job,status:'complete',original_selected:true,quality_approved:false,preview_url:`/mesh-scene-viewer.html?job=${job}&result=${digest}`};
createMeshCharacterEditor({document,api:async url=>url.includes('/mesh-scene-jobs/')?(wait||structuredClone(saved)):structuredClone(report),post:async(url,payload)=>{posted.push({url,payload});return {id:fit};},getScene:()=>structuredClone(scene),getBounds:()=>structuredClone(bounds)});
await el('Build').onclick();assert.equal(posted[0].url,'/api/mesh-character-jobs');assert.deepEqual(posted[0].payload.editable_clip_boundaries,{A:[]});assert.equal(el('Job').value,fit);
el('Start').checked=true;await el('Build').onclick();assert.match(el('Status').textContent,/Acknowledge/);assert.equal(posted.length,1);
el('Ack').checked=true;await el('Build').onclick();assert.deepEqual(posted[1].payload.editable_clip_boundaries,{A:['start']});
await el('Review').onclick();assert.match(el('Status').textContent,/still fails/);assert.equal(el('Results').children.length,2);
report.result.candidate=null;await el('Review').onclick();assert.match(el('Status').textContent,/No improved candidate/);
report.result.sampled_candidate_pass=true;report.result.candidate='probe-001';await el('Review').onclick();assert.match(el('Status').textContent,/passes declared sampled/);
report.comparison_url='https://elsewhere.test';await el('Review').onclick();assert.match(el('Status').textContent,/Unexpected/);
let resolve;wait=new Promise(r=>resolve=r);const pending=el('Build').onclick();bounds.options.iterations=5;resolve(saved);await pending;assert.match(el('Status').textContent,/changed/);assert.equal(posted.length,2);
console.log('Mesh character editor: exact scene/bounds, unsupported settings, explicit clip-edge acknowledgment, stale async selection and honest failure/candidate review pass.');
