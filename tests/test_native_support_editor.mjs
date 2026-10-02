import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createNativeSupportEditor} from '../scripts/native-support-editor.mjs';
const html=await readFile(new URL('../scripts/native-support-editor.html',import.meta.url),'utf8');
class Element{
 constructor(){this.value='';this.disabled=false;this.hidden=false;this.open=false;this.events={};this.children=[];this.textContent='';}
 replaceChildren(...items){this.children=items;this.value=items[0]?.value??'';}
 append(...items){this.children.push(...items);}
 setAttribute(k,v){this[k]=v;}
 removeAttribute(k){delete this[k];}
 addEventListener(k,fn){this.events[k]=fn;}
}
const nodes=new Map();for(const id of html.matchAll(/id="(nativeSupport[^"]+)"/g)){assert(!nodes.has(id[1]));nodes.set(id[1],new Element());}
const el=id=>{assert(nodes.has('nativeSupport'+id));return nodes.get('nativeSupport'+id);};
const doc={getElementById:id=>nodes.get(id),createElement:()=>new Element()};
const storage=new Map();const context={job:{id:'parent'},variant:'transfer'};
const metadata={source_job:'parent',variant:'transfer',label:'Synthetic',glb_sha256:'a'.repeat(64),duration_s:2.,animation_index:0,root_node:0,
 mapping:{LeftLeg:1,LeftShin:2,LeftFoot:3},joints:[{node:0,name:'pelvis'},...[1,2,3].map(n=>({node:n,parent:n-1,name:'custom-'+n,rotation_clock:'0',interpolation:'LINEAR'}))],clocks:[{id:'0',times_s:[0,.20000000298023224,.4000000059604645,.6000000238418579,.800000011920929,1,1.2000000476837158,1.399999976158142,1.600000023841858,1.7999999523162842,2]}]};
let posted=null,jobData={jobs:[]},waitMetadata=null;
const fetch=async(url,options)=>{
 if(url.startsWith('/api/native-support-source?'))return waitMetadata||{ok:true,json:async()=>structuredClone(metadata)};
 if(url==='/api/native-support-jobs')return {ok:true,json:async()=>structuredClone(jobData)};
 if(url==='/api/native-support-edits'){posted=JSON.parse(options.body);return {ok:true,json:async()=>({id:'fit1'})};}
 throw Error(url);
};
const actualInterval=globalThis.setInterval;globalThis.setInterval=()=>0;
const editor=createNativeSupportEditor({getContext:()=>context,document:doc,fetch,Option:function(text,value){return {text,value};},MutationObserver:null,storage:{getItem:k=>storage.get(k)||null,setItem:(k,v)=>storage.set(k,v)}});
globalThis.setInterval=actualInterval;
el('Panel').open=true;el('Foot').value='LeftFoot';el('Name').value='left-stance';
for(const[id,value]of Object.entries({NX:0,NY:1,NZ:0,Plane:.2,Clearance:.25,Gap:5,Displacement:30,Angle:45}))el(id).value=value;
await editor.bind();assert.equal(el('Fields').disabled,false);assert.equal(el('Last').value,'10');
assert.match(el('First').children[3].text,/0.600000024/);
el('First').value='1';el('Last').value='9';el('Start').value='.8';el('End').value='1.2';await el('Add').onclick();
const draft=JSON.parse(storage.get('strep:native-support:'+metadata.glb_sha256));assert.deepEqual(draft.supports[0].stance_s,[.8,1.2]);assert.deepEqual(draft.mapping,{LeftLeg:1,LeftShin:2,LeftFoot:3});
el('Name').value='left-stance';el('End').value='1.25';await el('Add').onclick();assert.equal(JSON.parse(storage.get('strep:native-support:'+metadata.glb_sha256)).supports.length,1);
context.variant='corrected';await el('Fit').onclick();assert.equal(posted,null);assert.match(el('Status').textContent,/Selected clip changed/);
context.variant='transfer';await el('Fit').onclick();assert.equal(posted.spec.glb_sha256,metadata.glb_sha256);assert.equal(posted.spec.supports[0].stance_s[1],1.25);assert.equal(el('Fields').disabled,true);
assert.deepEqual(Object.keys(posted).sort(),['source_job','spec','variant']);assert.equal(el('Refine').checked,false);
jobData={jobs:[{id:'fit1',status:'complete',review:{retained_input:true,retention_reason:'no_proposal_satisfies_all_bounds',result_sha256:'b'.repeat(64)}}]};
await editor.refresh();assert.match(el('Status').textContent,/Input retained/);assert.equal(el('Fields').disabled,false);el('Review').onclick();assert.equal(el('Frame').src,'/native-support-viewer.html?id=fit1&result='+'b'.repeat(64));
el('Panel').open=false;el('Panel').events.toggle();assert.equal(el('Frame').src,undefined);
// A late metadata response cannot attach to a different selected version.
el('Panel').open=true;let resolve;waitMetadata=new Promise(r=>resolve=r);const loading=editor.bind();context.variant='corrected';resolve({ok:true,json:async()=>metadata});await loading;assert.equal(el('Fields').disabled,true);assert.match(el('Binding').textContent,/Checking/);
waitMetadata=null;context.variant='transfer';await editor.bind();assert.equal(el('Intervals').children.length,1);el('Intervals').children[0].children[2].onclick();assert.equal(JSON.parse(storage.get('strep:native-support:'+metadata.glb_sha256)).supports.length,0);
await el('Fit').onclick();assert.match(el('Status').textContent,/Add a stance interval/);
// Close/reset while a metadata request is in flight: no stale draft is installed.
waitMetadata=new Promise(r=>resolve=r);const closing=editor.bind();editor.reset();resolve({ok:true,json:async()=>metadata});await closing;assert.equal(el('Fields').disabled,true);assert.equal(el('Binding').textContent,'No clip selected.');
// Preparation is an explicit submission choice; the original draft stays bound.
waitMetadata=null;metadata.rigid_preparation={eligible:true,static_node_changes:1,geometry_check_pending:true};
await editor.bind();assert.equal(el('Preparation').hidden,false);assert.equal(el('PrepareRig').checked,false);assert.equal(el('PrepareRig').disabled,false);
el('Name').value='prepared-stance';el('First').value='1';el('Last').value='9';el('Start').value='.8';el('End').value='1.2';await el('Add').onclick();
el('PrepareRig').checked=true;el('PrepareRig').onchange();el('Refine').checked=true;el('Refine').onchange();posted=null;jobData={jobs:[]};await el('Fit').onclick();
assert.equal(posted.prepare_rigid_input,true);assert.equal(posted.spec.glb_sha256,metadata.glb_sha256);
assert.equal(posted.sampled_support_repair,true);assert.equal(posted.sampled_support_iterations,undefined);
assert.equal(JSON.parse(storage.get('strep:native-support:'+metadata.glb_sha256)).prepare_rigid_input,undefined);
assert.equal(JSON.parse(storage.get('strep:native-support:'+metadata.glb_sha256)).sampled_support_repair,undefined);
jobData={jobs:[{id:'fit1',status:'complete',review:{preparation:{changes:1},retained_input:true,retention_reason:'no_proposal_satisfies_all_bounds',result_sha256:'c'.repeat(64)}}]};
await editor.refresh();assert.match(el('Status').textContent,/Prepared input retained/);
await editor.bind();assert.equal(el('PrepareRig').checked,false);assert.equal(el('Refine').checked,false);
metadata.rigid_preparation={eligible:false,static_node_changes:null,reason:'Scale exceeds limit'};
await editor.bind();assert.equal(el('PrepareRig').disabled,true);assert.match(el('PreparationHint').textContent,/separate conversion/);
el('PrepareRig').checked=true;posted=null;await el('Fit').onclick();assert.equal(posted,null);assert.match(el('Status').textContent,/preparation is unavailable/);
el('Refine').checked=true;editor.reset();assert.equal(el('Preparation').hidden,true);assert.equal(el('PrepareRig').checked,false);assert.equal(el('Refine').checked,false);
await editor.bind();el('PrepareRig').checked=false;el('JointSearch').checked=true;el('JointSearch').onchange();assert.equal(el('Refine').disabled,true);posted=null;await el('Fit').onclick();assert.equal(posted.joint_source_rate_search,true);assert.equal(posted.joint_search_evaluations,undefined);assert.equal(posted.sampled_support_repair,undefined);jobData={jobs:[{id:'fit1',status:'complete',review:{retained_input:true,retention_reason:'no_proposal_satisfies_all_bounds',result_sha256:'c'.repeat(64)}}]};await editor.refresh();el('Refine').checked=true;posted=null;await el('Fit').onclick();assert.equal(posted,null);assert.match(el('Status').textContent,/one support proposal method/);editor.reset();assert.equal(el('JointSearch').checked,false);assert.equal(el('Refine').disabled,false);assert.equal(el('JointSearch').disabled,false);
editor.dispose();
console.log('Native supports: original clocks, source/version isolation, explicit preparation/refinement, immutable submission, original draft persistence, retained failures and stale responses pass. DOM simulation only.');

const nativeNodes=new Map([...nodes].map(([id])=>[id.replace('nativeSupport','correctionSupport'),new Element()]));let selectedConversion;globalThis.setInterval=()=>0;const nativeEditor=createNativeSupportEditor({prefix:'correctionSupport',getContext:()=>({job:{id:'parent'},variant:'native_review'}),document:{getElementById:id=>nativeNodes.get(id),createElement:()=>new Element()},fetch,Option:function(text,value){return {text,value};},storage:null,MutationObserver:null,onNativeCandidate:async value=>{selectedConversion=value;}});globalThis.setInterval=actualInterval;const ne=id=>nativeNodes.get('correctionSupport'+id);assert.equal(ne('UseCorrection').hidden,false);assert.equal(ne('UseCorrection').disabled,true);jobData={jobs:[{id:'native',status:'complete',review:{native_review_candidate:{selection:{item_id:'fixture'},retained_input:true,training_admitted:false},result_sha256:'d'.repeat(64)}}]};await nativeEditor.refresh();assert.equal(ne('UseCorrection').disabled,false);await ne('UseCorrection').onclick();assert.equal(selectedConversion.retained_input,true);assert.equal(selectedConversion.training_admitted,false);nativeEditor.dispose();console.log('Native support namespace and explicit candidate callback pass without touching character-editor controls.');
