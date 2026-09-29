import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
const code=await readFile(new URL('../scripts/scene-region-editor.js',import.meta.url),'utf8');
const html=await readFile(new URL('../scripts/action-studio.html',import.meta.url),'utf8');
class Element{
 constructor(){this.value='';this.disabled=false;this.checked=true;this.textContent='';this.events={};this.option={};}
 addEventListener(event,handler){this.events[event]=handler;}
 replaceChildren(...children){this.children=children;this.value=children[0]?.value||'';}
 querySelector(){return this.option;}
}
const elements=new Map();
for(const id of html.matchAll(/id="(sceneRegion[^"]+)"/g)){
 assert(!elements.has(id[1]),'Duplicate UI ID');elements.set(id[1],new Element());
}
globalThis.document={getElementById(id){assert(elements.has(id),'Missing control '+id);return elements.get(id);}};
globalThis.Option=class{constructor(label,value){this.label=label;this.value=value;}};
const storage=new Map();globalThis.localStorage={getItem:k=>storage.get(k)||null,setItem:(k,v)=>storage.set(k,v),removeItem:k=>storage.delete(k)};
const data={source_url:'/files/example/palm.json',revision:'version1',frames:10,contacts:[{id:'grip',actor:'A',hand:'LeftHand',target_object:'box',supported:true,
 edit:{id:'grip',start_frame:2,end_frame:6,point_m:[.2,.1,0],anchor_tolerance_m:.005,patch_mode:'saved',patch_radius_m:.045,patch_normal_degrees:60,
 limits:{clearance_m:.002,contact_gap_m:.003,spacing_m:.006,area_m2:.000025,centroid_error_m:.005,local_radius_m:.02,normal_degrees:10}}}]};
let posted=null,completed=null,changed=false,preview=null,pickRequests=0,cancellations=0;
globalThis.fetch=async(url,options)=>{
 if(url.startsWith('/api/scene-region-source'))return {ok:true,json:async()=>structuredClone(data)};
 if(url==='/api/scene-region-fits'){posted=JSON.parse(options.body);return {ok:true,json:async()=>({id:'job1'})};}
 assert.equal(url,'/api/scene-region-jobs');return {ok:true,json:async()=>({jobs:[{id:'job1',status:'complete',collection:'scene-region-jobs/job1',assessment:{contact_geometry_passed:false,contact_failures:2,geometry_failures:3,motion_regressions:['peak_joint_speed_m_s']}}]})};
};
const {createSceneRegionEditor}=await import(new URL('../scripts/scene-region-editor.js',import.meta.url));
const editor=createSceneRegionEditor({getContext:()=>({frame:4,changed}),onComplete:async c=>{completed=c;},onDraft:(contact,edit,include)=>preview=contact?structuredClone({contact,edit,include}):null,onPick:()=>pickRequests++,onCancelPick:()=>cancellations++});
await editor.bind(data.source_url);
const el=id=>elements.get('sceneRegion'+id);
assert.equal(el('Gap').value,3);assert.equal(el('Area').value,25);
el('Pick').onclick();assert.equal(pickRequests,1);
editor.setGripPoint([.2,.137425,.021625]);assert.deepEqual(preview.edit.point_m,[.2,.137425,.021625]);
assert.equal(preview.include,true);assert.equal(preview.contact.target_object,'box');
assert.deepEqual(JSON.parse(storage.get('strep:regions:version1')).drafts.grip.edit.point_m,[.2,.137425,.021625]);
el('UseFrame').onclick();assert.equal(el('Start').value,4);
changed=true;await el('Apply').onclick();assert.equal(posted,null);assert.match(el('Status').textContent,/unsaved/);
changed=false;el('Label').value='Edited grip';el('Gap').value='3.5';el('Gap').events.input();
await el('Apply').onclick();for(let i=0;i<5;i++)await new Promise(resolve=>setImmediate(resolve));
assert.equal(posted.contacts[0].limits.contact_gap_m,.0035);assert.equal(posted.contacts[0].start_frame,4);
assert.deepEqual(posted.contacts[0].point_m,[.2,.137425,.021625]);assert(cancellations>0);
assert.equal(posted.label,'Edited grip');assert.equal(completed,'scene-region-jobs/job1');
assert.match(el('Status').textContent,/Needs correction/);assert.match(el('Status').textContent,/Motion regressions/);
assert.equal(storage.get('strep:region-active-job'),undefined);
editor.reset();assert.equal(el('Apply').disabled,true);
assert.equal(el('Pick').disabled,true);assert.equal(preview,null);el('Pick').onclick();assert.equal(pickRequests,1);
globalThis.localStorage={getItem(){throw Error('Storage denied');},setItem(){throw Error('Storage denied');},removeItem(){throw Error('Storage denied');}};
const privateEditor=createSceneRegionEditor({getContext:()=>({frame:0,changed:false}),onComplete:async()=>{}});
await privateEditor.bind(data.source_url);assert.equal(el('Apply').disabled,false);
console.log('Region editor: markup binding, unit conversions, draft capture, unsaved-placement guard, submission, failed-result presentation and unavailable-storage recovery pass. No network or browser used.');
