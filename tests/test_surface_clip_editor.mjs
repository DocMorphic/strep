import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {pointContact,checkedStatus,createSurfaceClipEditor} from '../scripts/surface-clip-editor.mjs';
import {validateNativePreview,selectNativePreviewClip} from '../scripts/native-preview-policy.mjs';
const job='a'.repeat(32),attempt='b'.repeat(32),digest='c'.repeat(64);
const binding={source_job:'source',variant:'input',glb_sha256:digest,root_node:0,duration_s:2,label:'Fixture',joints:[{node:1,name:'Leg',interpolation:'LINEAR'},{node:2,name:'Other',interpolation:'STEP'}]};
const patch={glb_sha256:digest,vertices:[[6,0,2]]};
assert.deepEqual(pointContact(binding,patch,[1,2,3],.123,.124).vertex,[6,0,2]);
for(const p of [{...patch,glb_sha256:'d'.repeat(64)},{...patch,vertices:[]},{...patch,vertices:[[6,0,2],[6,0,3]]},{...patch,vertices:[[6,0,-1]]}])assert.throws(()=>pointContact(binding,p,[0,0,0],0,1));
for(const times of [[-1,1],[1,0],[0,3],[NaN,1]])assert.throws(()=>pointContact(binding,patch,[0,0,0],...times));
let saved={schema:'strep-studio-surface-clip-status-v1',id:job,status:'checkpointed',can_continue:true,original_selected:true,quality_approved:false,release_approved:false,
 ticket:{request_sha256:digest,state_sha256:digest,attempt:digest},downloads:[{label:'Original',url:`/files/surface-clip-jobs/${job}/${attempt}/original.glb`}],preview_url:`/surface-clip-viewer.html?job=${job}&attempt=${attempt}`,
 result:{status:'checkpointed',quality_approved:false,release_approved:false,transition_review_required:true,total_keys:11,validated_through:2}};
checkedStatus(saved,job);
for(const alter of [s=>s.quality_approved=true,s=>s.downloads[0].url='https://example.com',s=>s.preview_url+='&other=1',s=>s.ticket.state_sha256='wrong',s=>s.result.validated_through=11,s=>s.result.transition_review_required=false]){const s=structuredClone(saved);alter(s);assert.throws(()=>checkedStatus(s,job));}
class Element{constructor(){this.value='';this.checked=false;this.disabled=false;this.children=[];}replaceChildren(...v){this.children=v;}append(...v){this.children.push(...v);}setAttribute(n,v){this[n]=v;}}
const html=await readFile(new URL('../scripts/surface-clip-editor.html',import.meta.url),'utf8'),nodes=new Map();
for(const [,id] of html.matchAll(/id="([^"]+)"/g)){assert(!nodes.has(id));nodes.set(id,new Element());}
const document={getElementById:id=>nodes.get(id),createElement:()=>new Element()},el=n=>nodes.get('surfaceClip'+n);
for(const [n,v] of Object.entries({Horizontal:.15,Vertical:.75,Floor:5,Contact:20,RootStep:25,RotationStep:5,Windows:10,Seconds:240,X:0,Y:0,Z:0}))el(n).value=String(v);
let context={job:{id:'source'},variant:'input'},wait=null,posted=[];
const editor=createSurfaceClipEditor({document,getContext:()=>structuredClone(context),getPatch:()=>patch,
 api:async url=>url.startsWith('/api/native-support-source')?(wait||structuredClone(binding)):url==='/api/surface-clip-jobs'?{jobs:[saved]}:structuredClone(saved),
 post:async(url,payload)=>{posted.push({url,payload});return {id:job};}});
await el('Bind').onclick();assert.equal(el('Fields').disabled,false);
el('Joints').children[0].children[0].checked=true;
assert.equal(el('Joints').children[1].children[0].disabled,true);
await el('Add').onclick();assert.equal(editor.request().contacts.length,1);
await el('Build').onclick();assert.equal(posted.length,1);assert.equal(posted[0].payload.limits.floor_depth_m,.005);
assert.equal(posted[0].payload.end_policy,'preserve');assert.equal(el('Jobs').value,job);
el('EditEnd').checked=true;await el('Build').onclick();assert.equal(posted.length,1);assert.match(el('Status').textContent,/Acknowledge/);
el('Ack').checked=true;await el('Build').onclick();assert.equal(posted[1].payload.end_policy,'edit');
context.variant='transfer';await el('Build').onclick();assert.equal(posted.length,2);assert.match(el('Status').textContent,/selection changed/);context.variant='input';
await el('Review').onclick();assert.equal(el('Continue').disabled,false);assert.equal(el('Results').children.length,2);
await el('Continue').onclick();assert.equal(posted.at(-1).url,`/api/surface-clip-jobs/${job}/continue`);assert.deepEqual(posted.at(-1).payload,saved.ticket);
await el('Review').onclick();saved.ticket.state_sha256='d'.repeat(64);await el('Continue').onclick();assert.equal(posted.length,3);assert.match(el('Status').textContent,/progress changed/);
let resolve;wait=new Promise(r=>resolve=r);const pending=el('Bind').onclick();context.variant='transfer';resolve(binding);await pending;assert.match(el('Status').textContent,/selection changed/);assert.equal(el('Fields').disabled,true);
wait=null;context.variant='input';await el('Bind').onclick();el('Joints').children[0].children[0].checked=true;
el('EditStart').checked=true;const priorPosts=posted.length;await el('Build').onclick();assert.equal(posted.length,priorPosts);assert.match(el('Status').textContent,/Acknowledge/);
el('StartAck').checked=true;await el('Build').onclick();assert.equal(posted.at(-1).payload.start_policy,'edit');assert.equal(posted.at(-1).payload.acknowledge_changed_start,true);
el('EditStart').onchange();assert.equal(el('StartAck').checked,false);
const preview={kind:'native_surface_correction',preview_url:`/files/surface-clip-jobs/${job}/${attempt}/original.glb`,preview_sha256:digest,preview_start_s:0,preview_end_s:2,animation_index:0,animation_count:1};
validateNativePreview(preview);assert.equal(selectNativePreviewClip(preview,[{duration:2}]).duration,2);
for(const url of [preview.preview_url+'?x=1',preview.preview_url.replace(attempt,'..'),'/files/action-jobs/x/a.glb'])assert.throws(()=>validateNativePreview({...preview,preview_url:url}));
assert.throws(()=>selectNativePreviewClip(preview,[{duration:2},{duration:2}]));
const bundle=await readFile(new URL('../scripts/action-studio.html',import.meta.url),'utf8');
for(const id of nodes.keys())assert.equal([...bundle.matchAll(new RegExp(`id="${id}"`,'g'))].length,1,id);
console.log('Ground-contact editor: source identity, point targets, endpoint acknowledgment, stale continuation, artifact policy and mounted controls pass.');
