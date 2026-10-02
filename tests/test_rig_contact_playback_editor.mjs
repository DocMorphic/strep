import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import vm from 'node:vm';
const html=await readFile(new URL('../scripts/action-studio.html',import.meta.url),'utf8');
const source=await readFile(new URL('../scripts/character-contacts.js',import.meta.url),'utf8');
class Element {
 constructor(){this.value='';this.children=[];this._text='';this.style={};}
 set textContent(v){this._text=v;this.children=[];}
 get textContent(){return this._text+this.children.map(c=>c.textContent).join('');}
 replaceChildren(...c){this._text='';this.children=c;if(c[0]?.value!==undefined)this.value=c[0].value;}
 append(...c){this.children.push(...c);}
 setAttribute(){} addEventListener(){} scrollIntoView(){}
}
const elements=new Map([...html.matchAll(/id="([^"]+)"/g)].map(m=>[m[1],new Element()]));
const C=id=>{assert(elements.has(id),'Missing generated HTML element '+id);return elements.get(id);};
const defaults={schema:'strep-mesh-playback-fit-v1',contact_clock:'authored-keys',spacing_frames:10,floor_iterations:30,contact_iterations:60};
const spec={glb_sha256:'a'.repeat(64),frames:7,patches:{wrist:{vertices:[0]}},contacts:[{patch:'wrist',start_frame:2,end_frame_exclusive:4,target_position_m:[0,0,0]}],edit_joints:{},limits:{root_horizontal_m:.04,root_vertical_m:.12,root_step_m:.015,joint_step_degrees:5}};
let metadata={job_id:'parent',variant:'transfer',glb_sha256:spec.glb_sha256,frames:7,fps:30,spec,primitives:[],verification_vertices:[],editable_joints:[],playback_fit:{available:true,defaults}};
let current={job:{id:'parent',label:'Synthetic'},result:{kind:'rough_import'},variant:'transfer',frame:0,model:{updateMatrixWorld(){},traverse(){}}};
const storage=new Map(),calls=[],messages=[],seeks=[],fits=[];let pending=null,failStorage=false,apiPending=null;
class Geometry {constructor(){this.attributes={};}setFromPoints(){return this;}getAttribute(k){return this.attributes[k];}setAttribute(k,v){this.attributes[k]=v;}computeBoundingSphere(){}}
class Object3D {constructor(geometry){this.geometry=geometry;this.position={set(){}};}}
class Vector3 {constructor(x=0,y=0,z=0){this.set(x,y,z);}set(x,y,z){Object.assign(this,{x,y,z});return this;}applyMatrix4(m){this.x+=m.shift[0];this.y+=m.shift[1];this.z+=m.shift[2];return this;}}
class Attribute {constructor(array,size){this.array=array;this.count=array.length/size;}setXYZ(i,x,y,z){this.array.set([x,y,z],i*3);}}
const THREE={Points:Object3D,LineSegments:Object3D,BufferGeometry:Geometry,PointsMaterial:class{},LineBasicMaterial:class{},Vector3,Float32BufferAttribute:Attribute};
const sceneNodes=[];
const sandbox={structuredClone,URLSearchParams,document:{createElement:()=>new Element(),createTextNode:text=>({textContent:text})},Option:class extends Element{constructor(text,value){super();this.textContent=text;this.value=value;}},localStorage:{getItem:k=>storage.get(k)||null,setItem:(k,v)=>{if(failStorage)throw Error('full');storage.set(k,v);}}};
vm.createContext(sandbox);vm.runInContext(source+'\nglobalThis.createEditor=createRigContactEditor;',sandbox);
const editor=sandbox.createEditor({C,THREE,canvas:new Element(),scene:{add(node){sceneNodes.push(node);}},camera:{},controls:{},
 api:async()=>apiPending?await apiPending:structuredClone(metadata),post:async(url,payload)=>{calls.push({url,payload});return pending?await pending:{id:'edit'};},
 status:m=>messages.push(m),getContext:()=>current,pause(){},seek:f=>seeks.push(f),onFit:j=>fits.push(j)});
const open=()=>C('rigEditContacts').onclick();
await open();assert.equal(C('rigFitMode').value,'playback');assert.equal(C('rigFitClock').value,'authored-keys');
assert.match(C('rigFitHint').textContent,/do not guarantee a hold/);
C('rigFitClock').value='frame-hold';await C('rigFitClock').onchange();
C('rigFitContactIterations').value='12';await C('rigFitContactIterations').onchange();
assert(storage.has('strep:mesh-contact-fit:'+spec.glb_sha256));assert(!('contact_clock' in JSON.parse(storage.get('strep:mesh-contacts:'+spec.glb_sha256)||'{}')));
let resolve;pending=new Promise(r=>resolve=r);const submit=C('rigContactFit').onclick();
assert(C('rigContactFit').disabled);await C('rigContactFit').onclick();assert.equal(calls.length,1,'No duplicate submission');
assert.equal(calls[0].payload.fit_options.contact_clock,'frame-hold');assert.equal(calls[0].payload.fit_options.contact_iterations,12);
assert.deepEqual(Object.keys(calls[0].payload).sort(),['fit_options','source_job','spec','variant']);
assert(!('contact_clock' in calls[0].payload.spec));C('rigFitClock').value='authored-keys';await C('rigFitClock').onchange();
assert.equal(calls[0].payload.fit_options.contact_clock,'frame-hold','Submitted choice remains a snapshot');
editor.setBusy(true);resolve({id:'edit'});await submit;pending=null;assert(C('rigContactFit').disabled);assert.equal(fits.length,1);editor.setBusy(false);
// Inspect the exact clock and seek its fractional worst sample.
const inspection={failed_intervals:0,contacts:[],screen:{contact_error_m:.02,floor_depth_m:.005},floor_frames_failed:0,frames:7,worst_floor:{depth_m:0,frame:0,skin_influences:[]},
 playback_contacts:{contact_clock:'frame-hold',failed_intervals:1,contacts:[{index:0,patch:'wrist',error_max_m:.023,worst_time_s:.083333}]},playback_floor:{floor_depth_max_m:.004,failed_samples:0}};
pending=Promise.resolve(inspection);await C('rigContactInspect').onclick();pending=null;
assert.equal(calls.at(-1).payload.fit_options.contact_clock,'authored-keys');
assert.match(C('rigContactDiagnostics').textContent,/1\/1 intervals fail/);
C('rigContactDiagnostics').children.at(-1).onclick();assert.equal(seeks.at(-1),.083333*30);
pending=new Promise(r=>resolve=r);const inspect=C('rigContactInspect').onclick();
C('rigFitMode').value='sequential';await C('rigFitMode').onchange();resolve(inspection);await inspect;pending=null;
assert.equal(C('rigContactDiagnostics').textContent,'','Changed fit options discard stale inspection');
await C('rigContactFit').onclick();assert.equal(Object.keys(calls.at(-1).payload).sort().join(','),'source_job,spec,variant','Legacy payload unchanged');
// Invalid budgets and unsupported periodic mode cannot submit.
C('rigFitMode').value='playback';C('rigFitFloorIterations').value='1.5';const count=calls.length;
await C('rigContactFit').onclick();assert.equal(calls.length,count);assert.match(messages.at(-1),/whole numbers/);
metadata={...metadata,period_frames:6,playback_fit:{available:false,defaults,reason:'Playback fitting does not preserve periodic closure; use the cycle contact fit'}};
await open();assert.equal(C('rigFitMode').value,'sequential');assert(C('rigFitPlayback').disabled);assert.match(C('rigFitHint').textContent,/periodic closure/);
C('rigFitMode').value='playback';await C('rigContactFit').onclick();assert.equal(calls.length,count);assert.match(messages.at(-1),/unavailable/);
// Storage failure keeps a usable choice; an obsolete metadata response cannot reopen a different source.
metadata={...metadata,period_frames:null,playback_fit:{available:true,defaults}};failStorage=true;await open();
C('rigFitFloorIterations').value='30';
C('rigFitMode').value='playback';C('rigFitClock').value='frame-hold';await C('rigFitClock').onchange();assert.match(messages.at(-1),/storage is unavailable/);
await C('rigContactFit').onclick();assert.equal(calls.at(-1).payload.fit_options.contact_clock,'frame-hold');
// Different interval choices survive edits, deletion/remapping and reopening.
failStorage=false;C('rigIntervals').children[0].children[1].onclick();
C('rigIntervalClock').value='frame-hold';await C('rigContactAdd').onclick();
C('rigContactStart').value=4;C('rigContactEnd').value=4;C('rigIntervalClock').value='authored-keys';await C('rigContactAdd').onclick();
await C('rigContactFit').onclick();assert.equal(JSON.stringify(calls.at(-1).payload.fit_options.contact_clock_overrides),JSON.stringify({'0':'frame-hold','1':'authored-keys'}));
assert(!('contact_clock' in calls.at(-1).payload.spec.contacts[0]),'Draft contact schema stays unchanged');
C('rigIntervals').children[0].children[2].onclick();await C('rigContactFit').onclick();
assert.equal(JSON.stringify(calls.at(-1).payload.fit_options.contact_clock_overrides),JSON.stringify({'0':'authored-keys'}));
await open();C('rigIntervals').children[0].children[1].onclick();assert.equal(C('rigIntervalClock').value,'authored-keys');
const mixedCount=calls.length;C('rigFitMode').value='sequential';await C('rigFitMode').onchange();await C('rigContactFit').onclick();
assert.equal(calls.length,mixedCount);assert.match(messages.at(-1),/Individual interval timings require/);
// Clearing the explicit choice restores the unchanged legacy request.
C('rigIntervalClock').value='default';await C('rigContactAdd').onclick();await C('rigContactFit').onclick();
assert(!('fit_options' in calls.at(-1).payload));
// A saved override never binds to a changed contact list, even on the same clip.
const stored=JSON.parse(storage.get('strep:mesh-contact-fit:'+spec.glb_sha256));stored.options.contact_clock_overrides={'0':'frame-hold'};stored.contacts=spec.contacts;
storage.set('strep:mesh-contact-fit:'+spec.glb_sha256,JSON.stringify(stored));await open();
C('rigFitMode').value='playback';await C('rigContactFit').onclick();assert(!('contact_clock_overrides' in calls.at(-1).payload.fit_options));
// A new browser/reopened candidate gets the saved job choice, including its overrides.
storage.clear();metadata.playback_fit.saved_options={...defaults,contact_clock:'frame-hold',contact_clock_overrides:{'0':'authored-keys'}};
await open();assert.equal(C('rigFitClock').value,'frame-hold');C('rigIntervals').children[0].children[1].onclick();
assert.equal(C('rigIntervalClock').value,'authored-keys');await C('rigContactFit').onclick();
assert.equal(JSON.stringify(calls.at(-1).payload.fit_options.contact_clock_overrides),JSON.stringify({'0':'authored-keys'}));
apiPending=new Promise(r=>resolve=r);const opening=open();editor.reset();current={...current,model:{updateMatrixWorld(){},traverse(){}}};resolve(metadata);await opening;
assert(C('rigContactPanel').hidden);
const studio=await readFile(new URL('../scripts/character-studio.js',import.meta.url),'utf8');
assert(studio.includes('playback_contact_fit'));assert(studio.includes('Saved fitting choice'));assert(studio.includes('Playback contact review'));
assert(html.replace(/\r\n/g,'\n').includes(source.replace(/\r\n/g,'\n')),'Generated page includes the tested editor source');
// Bone-region drafts are read-only until explicitly applied, and retain timing.
metadata.vertex_count=3;metadata.editable_joints=[{node:3,label:'Foot'}];metadata.primitives=[{node:99,primitive:0,vertex_offset:0,vertices:3}];
const regionMesh={isMesh:true,parent:null,matrixWorld:{shift:[2,3,4]},geometry:{getAttribute:()=>({count:3})},getVertexPosition:(i,target)=>target.set(i*.1,i*.2,-i*.3)};
current.model={updateMatrixWorld(){},traverse(fn){fn(regionMesh);}};current.loaded={parser:{associations:new Map([[regionMesh,{nodes:99,primitives:0}]])}};
await open();C('rigRegionBone').value='3';
const patchBefore=C('rigPatchVertices').value,clockBefore=C('rigFitClock').value;
const resultFor=request=>({schema:request.schema,selector:Object.fromEntries(Object.entries(request).reverse()),vertex_count:3,
 matched_count:2,vertices:[0,2],selection_limit:256,can_apply:true,requires_review:true,anatomy_verified:false,quality_approved:false,bounds_world_m:{min:[0,0,0],max:[1,1,1]}});
async function regionPreview(transform=x=>x){pending=new Promise(r=>resolve=r);const task=C('rigRegionPreview').onclick();const request=structuredClone(calls.at(-1).payload);resolve(transform(resultFor(request)));await task;pending=null;return request;}
const regionRequest=await regionPreview();assert.equal(calls.at(-1).url,'/api/rig-patch-selection');assert.equal(regionRequest.box_world_m,null);
assert.equal(C('rigPatchVertices').value,patchBefore,'Preview retains old patch');assert(!C('rigRegionApply').disabled);
editor.update();assert(sceneNodes[1].visible);const cyan=sceneNodes[1].geometry.getAttribute('position');assert.equal(cyan.count,2);
for(const [i,want] of [2,3,4,2.2,3.4,3.4].entries())assert(Math.abs(cyan.array[i]-want)<3e-7,'Cyan indices use displayed world transforms');
await C('rigRegionApply').onclick();assert.equal(C('rigPatchVertices').value,'0, 2');assert.equal(C('rigFitClock').value,clockBefore);assert(C('rigRegionApply').disabled);
editor.update();assert(!sceneNodes[1].visible);assert.equal(sceneNodes[0].geometry.getAttribute('position').count,2);
// No partial sampling of an oversized region, no empty/malformed application.
await regionPreview(r=>({...r,matched_count:257,vertices:[],can_apply:false}));assert(C('rigRegionApply').disabled);assert.match(C('rigRegionInfo').textContent,/not sampled down/);
await C('rigRegionApply').onclick();assert.equal(C('rigPatchVertices').value,'0, 2');
await regionPreview(r=>({...r,matched_count:0,vertices:[],can_apply:false,bounds_world_m:null}));assert(C('rigRegionApply').disabled);
await regionPreview(r=>({...r,vertices:[0,0]}));assert(C('rigRegionApply').disabled);assert.match(messages.at(-1),/Invalid bone-region/);
await regionPreview(r=>({...r,quality_approved:true}));assert(C('rigRegionApply').disabled);
// Recursive comparison includes box bounds even without firing onchange.
C('rigRegionBox').checked=true;await regionPreview();C('rigRegionMaxX').value='0.75';
await C('rigRegionApply').onclick();assert.match(messages.at(-1),/Preview.*again/);assert.equal(C('rigPatchVertices').value,'0, 2');
await regionPreview();current.frame=.5;await C('rigRegionApply').onclick();assert.match(messages.at(-1),/Preview.*again/);current.frame=0;
// Draft changes and source reset invalidate late results; duplicate clicks do not submit.
pending=new Promise(r=>resolve=r);const regionTask=C('rigRegionPreview').onclick(),regionCount=calls.length,late=structuredClone(calls.at(-1).payload);
await C('rigRegionPreview').onclick();assert.equal(calls.length,regionCount);C('rigRegionWeight').value='0.6';C('rigRegionWeight').onchange();resolve(resultFor(late));await regionTask;pending=null;assert(C('rigRegionApply').disabled);
pending=new Promise(r=>resolve=r);const resetTask=C('rigRegionPreview').onclick(),resetRequest=structuredClone(calls.at(-1).payload);editor.reset();resolve(resultFor(resetRequest));await resetTask;pending=null;assert(C('rigRegionApply').disabled);
console.log('Studio playback/region editor: interval choices, binding, source isolation, explicit region application, nested box/frame guards, oversized/empty/malformed rejection, late responses and duplicate submission pass. DOM/source only; no browser or GPU.');
