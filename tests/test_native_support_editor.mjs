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
jobData={jobs:[{id:'fit1',status:'complete',review:{retained_input:true,retention_reason:'no_proposal_satisfies_all_bounds',result_sha256:'b'.repeat(64)}}]};
await editor.refresh();assert.match(el('Status').textContent,/Input retained/);assert.equal(el('Fields').disabled,false);el('Review').onclick();assert.equal(el('Frame').src,'/native-support-viewer.html?id=fit1&result='+'b'.repeat(64));
el('Panel').open=false;el('Panel').events.toggle();assert.equal(el('Frame').src,undefined);
// A late metadata response cannot attach to a different selected version.
el('Panel').open=true;let resolve;waitMetadata=new Promise(r=>resolve=r);const loading=editor.bind();context.variant='corrected';resolve({ok:true,json:async()=>metadata});await loading;assert.equal(el('Fields').disabled,true);assert.match(el('Binding').textContent,/Checking/);
waitMetadata=null;context.variant='transfer';await editor.bind();assert.equal(el('Intervals').children.length,1);el('Intervals').children[0].children[2].onclick();assert.equal(JSON.parse(storage.get('strep:native-support:'+metadata.glb_sha256)).supports.length,0);
await el('Fit').onclick();assert.match(el('Status').textContent,/Add a stance interval/);
// Close/reset while a metadata request is in flight: no stale draft is installed.
waitMetadata=new Promise(r=>resolve=r);const closing=editor.bind();editor.reset();resolve({ok:true,json:async()=>metadata});await closing;assert.equal(el('Fields').disabled,true);assert.equal(el('Binding').textContent,'No clip selected.');
editor.dispose();
console.log('Native supports: original fractional clocks, source/version isolation, immutable submission, retained failures, draft persistence and stale responses pass.');
