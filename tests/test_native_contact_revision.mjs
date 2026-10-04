import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {createNativeSceneEditor,emptyDraft,revisionDraft} from '../scripts/native-scene-editor.mjs';
const clone=structuredClone;
const key=v=>JSON.stringify(v,(_,x)=>x&&typeof x==='object'&&!Array.isArray(x)?Object.fromEntries(Object.keys(x).sort().map(k=>[k,x[k]])):x);
class Element{constructor(){this.value='';this.checked=false;this.disabled=false;this.children=[];this.textContent='';}replaceChildren(...items){this.children=items;this.value=items[0]?.value??'';}append(...items){this.children.push(...items);}}
const html=await readFile(new URL('../scripts/native-scene-editor.html',import.meta.url),'utf8');
function setup(){
 const nodes=new Map();for(const m of html.matchAll(/<[^>]*id="(nativeScene[^"]+)"[^>]*>/g)){const n=new Element();n.value=m[0].match(/value="([^"]*)"/)?.[1]??'';nodes.set(m[1],n);}
 const el=name=>{assert(nodes.has('nativeScene'+name));return nodes.get('nativeScene'+name);};
 const base=emptyDraft();base.scene.duration_s=2;
 const actor={glb:'/files/rig-jobs/fixture/transfer/character.glb',sha256:'a'.repeat(64),animation_index:0,placement:{translation_m:[0,0,0],rotation_xyzw:[0,0,0,1]}};
 base.scene.actors={A:clone(actor),B:{...clone(actor),placement:{translation_m:[2,0,0],rotation_xyzw:[0,0,0,1]}}};
 base.scene.objects={item:{geometry:{schema:'strep-object-geometry-v1',shape:'sphere',radius_m:.8},keyframes:[{time_s:0,translation_m:[1,1,0],rotation_xyzw:[0,0,0,1]}]}};
 base.scene.contacts=[{id:'meeting',actor:'A',vertices:[[7,0,0]],reduction:'individual',target:{space:'actor',actor:'B',vertices:[[7,0,0]],reduction:'individual'},mode:'touch',interval_s:[1,1],limits:{position_m:.005}},
  {id:'world-hold',actor:'A',vertices:[[7,0,0]],reduction:'individual',target:{space:'world',points_m:[[1,2,3]]},mode:'hold',interval_s:[.8,1],limits:{position_m:.005,relative_speed_m_s:.005}}];
 base.geometry.clock.times_s=[0,.123456789,2];base.geometry.limits.penetration_m=.0021177467174925877;
 let patch={glb_sha256:actor.sha256,vertices:[[7,0,1],[7,0,2]]},reply=null,saved=null;
 const posts=[];
 function preview(p){const digest=v=>createHash('sha256').update(key(v)).digest('hex');
  const actor_sha256=Object.fromEntries(Object.entries(p.scene.actors).map(([n,a])=>[n,a.sha256]));
  const record={schema:'strep-native-contact-revision-v1',original_contacts:p.contact_revision.baseline.scene.contacts,authored_contacts:p.scene.contacts,explicit_edits:p.contact_revision.edits,actor_sha256,
   contact_timing_and_limits_unchanged:true,other_authoring_fields_unchanged:true,original_intent_retained:true,contact_intent_revised:true,animation_edited:false,anatomical_review_pending:true,quality_approved:false,training_admitted:false,release_approved:false};
  const endpoints=c=>{const times=[...new Set(c.interval_s)],count=c.reduction==='centroid'?1:c.vertices.length;
   return {times_s:times,source_world_m:times.map(()=>Array.from({length:count},()=>[0,0,0])),target_world_m:times.map(()=>Array.from({length:count},()=>[1,0,0])),separation_m:times.map(()=>Array(count).fill(1))};};
  return {schema:'strep-native-contact-revision-preview-v1',draft_sha256:digest(p),baseline_sha256:digest(p.contact_revision.baseline),implementation_sha256:{'studio_native_scene.py':'b'.repeat(64),'native_contact_revision.py':'c'.repeat(64)},actor_sha256,record,
   changes:p.contact_revision.edits.map(e=>{const a=p.contact_revision.baseline.scene.contacts.find(c=>c.id===e.id),b=p.scene.contacts.find(c=>c.id===e.id);return {id:e.id,original_contact:a,authored_contact:b,original_endpoint_inspection:endpoints(a),authored_endpoint_inspection:endpoints(b)};}),
   original_selected:true,animation_edited:false,anatomical_review_pending:true,quality_approved:false,training_admitted:false,release_approved:false};
 }
 const editor=createNativeSceneEditor({document:{getElementById:id=>nodes.get(id),createElement:()=>new Element()},getContext:()=>({}),getPatch:()=>clone(patch),
  api:async()=>({jobs:[]}),post:async(url,p)=>{posts.push([url,clone(p)]);assert.equal(url,'/api/native-scene-contact-revision');return reply?reply(p):preview(p);},download:p=>saved=p});
 editor.bind(base);return {editor,base,el,posts,preview,setPatch:p=>patch=p,setReply:r=>reply=r,saved:()=>saved};
}
async function stage(s,{partner=false,individual=false}={}){
 s.el('RevisionContact').value='meeting';s.el('RevisionContact').onchange();s.el('RevisionSourceReduction').value=individual?'individual':'centroid';
 await s.el('RevisionSource').onclick();
 if(partner){s.el('RevisionPartnerReduction').value=individual?'individual':'centroid';s.setPatch({glb_sha256:'a'.repeat(64),vertices:[[7,0,3],[7,0,4]]});await s.el('RevisionPartner').onclick();}
}

{
 const s=setup(),before=clone(s.editor.snapshot());await stage(s,{partner:true,individual:true});
 assert.deepEqual(s.editor.snapshot(),before);await s.el('RevisionPreview').onclick();assert.equal(s.el('RevisionApply').disabled,false);assert.deepEqual(s.editor.snapshot(),before);
 assert.match(s.el('RevisionResults').children[1].textContent,/original separation/);
 const detail=JSON.parse(s.el('RevisionResults').children[2].children[1].textContent);assert.deepEqual(detail.original_contact,before.scene.contacts[0]);assert.deepEqual(detail.authored_contact.vertices,[[7,0,1],[7,0,2]]);
 await s.el('RevisionApply').onclick();const changed=s.editor.snapshot();
 assert.deepEqual(changed.contact_revision.baseline,before);assert.deepEqual(changed.geometry,before.geometry);assert.deepEqual(changed.object_edit,before.object_edit);
 assert.deepEqual(changed.scene.actors,before.scene.actors);assert.deepEqual(changed.scene.objects,before.scene.objects);assert.deepEqual(changed.scene.contacts[1],before.scene.contacts[1]);
 assert.deepEqual(changed.scene.contacts[0].vertices,[[7,0,1],[7,0,2]]);assert.deepEqual(changed.scene.contacts[0].target.vertices,[[7,0,3],[7,0,4]]);
 assert.deepEqual(changed.scene.contacts[0].limits,before.scene.contacts[0].limits);assert.deepEqual(changed.scene.contacts[0].interval_s,before.scene.contacts[0].interval_s);
 assert.equal(s.posts.length,2);assert(s.el('DepthLimit').disabled&&s.el('AddContact').disabled);assert.match(s.el('Status').textContent,/explicit|Explicit/);
 await s.el('Save').onclick();assert.deepEqual(s.saved(),changed);
 await s.el('AddContact').onclick();assert.deepEqual(s.editor.snapshot(),changed);assert.match(s.el('Status').textContent,/Restore the original/);
 await s.el('RevisionRestore').onclick();assert.deepEqual(s.editor.snapshot(),before);assert.equal(s.el('DepthLimit').disabled,false);
}
{
 const s=setup();await stage(s,{individual:true});await s.el('RevisionPreview').onclick();assert.match(s.el('Status').textContent,/one-to-one/);assert.equal(s.posts.length,0);assert.deepEqual(s.editor.snapshot(),s.base);
}
for(const fault of ['wrong-rig','oversized','duplicate','boolean']){
 const s=setup();let p={glb_sha256:'a'.repeat(64),vertices:[[7,0,1],[7,0,2]]};
 if(fault==='wrong-rig')p.glb_sha256='x'.repeat(64);if(fault==='oversized')p.vertices=Array.from({length:257},(_,i)=>[7,0,i]);if(fault==='duplicate')p.vertices[1]=p.vertices[0];if(fault==='boolean')p.vertices[0][2]=true;
 s.setPatch(p);await stage(s);await s.el('RevisionPreview').onclick();assert.equal(s.posts.length,0);assert.deepEqual(s.editor.snapshot(),s.base);
}
for(const fault of ['approval','lost-original','changed-limits','wrong-actor','missing-review','wrong-edits','wrong-schema','missing-methods','misleading-change','missing-poses','wrong-clock','nonfinite-pose','wrong-count']){
 const s=setup();await stage(s);s.setReply(p=>{const r=s.preview(p);if(fault==='approval')r.quality_approved=true;if(fault==='lost-original')r.record.original_contacts=[];
  if(fault==='changed-limits')r.record.contact_timing_and_limits_unchanged=false;if(fault==='wrong-actor')r.actor_sha256={};if(fault==='missing-review')r.anatomical_review_pending=false;
  if(fault==='wrong-edits')r.record.explicit_edits=[];if(fault==='wrong-schema')r.schema='other';if(fault==='missing-methods')r.implementation_sha256={};if(fault==='misleading-change')r.changes[0].authored_contact={id:'meeting'};
  if(fault==='missing-poses')delete r.changes[0].original_endpoint_inspection;if(fault==='wrong-clock')r.changes[0].original_endpoint_inspection.times_s=[.999];if(fault==='nonfinite-pose')r.changes[0].authored_endpoint_inspection.source_world_m[0][0][0]=NaN;if(fault==='wrong-count')r.changes[0].original_endpoint_inspection.source_world_m[0]=[];return r;});
 await s.el('RevisionPreview').onclick();assert.equal(s.el('RevisionApply').disabled,true);assert.deepEqual(s.editor.snapshot(),s.base);assert.match(s.el('Status').textContent,/does not match/);
}
{
 const s=setup();await stage(s);let resolve;s.setReply(p=>new Promise(r=>resolve=()=>r(s.preview(p))));const pending=s.el('RevisionPreview').onclick();
 assert.equal(s.el('RevisionPreview').disabled,true);s.el('DepthLimit').value='7';resolve();await pending;
 assert.equal(s.el('RevisionApply').disabled,true);assert.match(s.el('Status').textContent,/changed/);assert(!s.editor.snapshot().contact_revision);
}
{
 const s=setup();await stage(s);await s.el('RevisionPreview').onclick();s.el('RevisionSourceReduction').value='individual';s.el('RevisionSourceReduction').onchange();
 await s.el('RevisionApply').onclick();assert.equal(s.posts.length,1);assert.deepEqual(s.editor.snapshot(),s.base);assert.match(s.el('Status').textContent,/Preview/);
}
for(const fault of ['method','source']){
 const s=setup();await stage(s);await s.el('RevisionPreview').onclick();s.setReply(p=>{if(fault==='source')throw Error('Selected character clip changed');const r=s.preview(p);r.implementation_sha256['native_contact_revision.py']='d'.repeat(64);return r;});
 await s.el('RevisionApply').onclick();assert.deepEqual(s.editor.snapshot(),s.base);assert.equal(s.el('RevisionApply').disabled,true);assert.match(s.el('Status').textContent,/changed/);
}
{
 const s=setup();await stage(s);await s.el('RevisionPreview').onclick();let resolve;s.setReply(p=>new Promise(r=>resolve=()=>r(s.preview(p))));
 const pending=s.el('RevisionApply').onclick();await s.el('RevisionApply').onclick();assert.equal(s.posts.length,2);assert.match(s.el('Status').textContent,/Wait/);resolve();await pending;assert(s.editor.snapshot().contact_revision);
 const first=clone(s.editor.snapshot());s.el('RevisionContact').value='world-hold';s.el('RevisionContact').onchange();s.el('RevisionSourceReduction').value='centroid';await s.el('RevisionSource').onclick();
 s.setReply(null);await s.el('RevisionPreview').onclick();await s.el('RevisionApply').onclick();const second=s.editor.snapshot();
 assert.equal(second.contact_revision.edits.length,2);assert.deepEqual(second.contact_revision.baseline,s.base);assert.deepEqual(second.scene.contacts[0],first.scene.contacts[0]);
 await s.el('RevisionRestore').onclick();assert.deepEqual(s.editor.snapshot(),s.base);
}
console.log('Explicit contact revision staging, preview/apply, preserved bounds, provenance, stale/malformed responses, atomic partner changes and restoration passed offline.');
