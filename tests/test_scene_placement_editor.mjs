import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
const markup=await readFile(new URL('../scripts/scene-placement-editor.html',import.meta.url),'utf8');
const ids=[...markup.matchAll(/id="([^"]+)"/g)].map(m=>m[1]);assert.equal(new Set(ids).size,ids.length);
class Element{constructor(){this.value='';this.disabled=false;this.textContent='';this.children=[];}replaceChildren(...rows){this.children=rows;}}
let elements,scene,metadata,report,posts,selected,deferred,fail;
function setup(){
 elements=new Map(ids.map(id=>[id,new Element()]));
 globalThis.document={getElementById:id=>{assert(elements.has(id));return elements.get(id);},createElement:()=>new Element()};
 scene={actors:{A:{transform:{translation_m:[0,0,0],rotation_xyzw:[0,0,0,1]}}},objects:{box:{keyframes:[{frame:0,translation_m:[0,.2,.55],rotation_xyzw:[0,0,0,1]}]}}};
 metadata={schema:'strep-scene-placement-source-v1',source_url:'/files/source/scene.json',revision:'r1'};
 report={schema:'strep-scene-placement-reach-v1',status:'provably_incompatible',source_url:metadata.source_url,revision:'r1',quality_approved:false,release_approved:false,
  rows:[{actor:'A',contact:'grip',samples:61,incompatible_frames:[85,86],maximum_error_lower_bound_m:.103,authored_tolerance_m:.03,worst_frame:102,worst_seconds:3.4}],skipped:[]};
 posts=[];selected=null;deferred=null;fail=false;
 globalThis.fetch=async(url,options)=>{
  if(url.startsWith('/api/scene-placement-source'))return {ok:true,json:async()=>structuredClone(metadata)};
  posts.push({url,body:JSON.parse(options.body)});
  if(deferred)await deferred.promise;
  if(fail)return {ok:false,json:async()=>({error:'Source changed; reload'})};
  const result=url.endsWith('snapshots')?{collection:'scene-placement-jobs/placement-'+'a'.repeat(32),scene_id:'placement',reach:report,source_url:metadata.source_url,revision:metadata.revision,quality_approved:false,release_approved:false}:report;
  return {ok:true,json:async()=>structuredClone(result)};
 };
}
const {createScenePlacementEditor}=await import(new URL('../scripts/scene-placement-editor.mjs',import.meta.url));
const el=id=>elements.get('scenePlacement'+id);
const create=()=>createScenePlacementEditor({getContext:()=>({scene}),onComplete:async(...args)=>{selected=args;}});
const wait=()=>{let resolve;const promise=new Promise(r=>resolve=r);return {promise,resolve};};
setup();let editor=create();assert(el('Check').disabled);await editor.bind(metadata.source_url);
scene.objects.box.keyframes[0].translation_m[2]=.1;
await el('Check').onclick();assert.equal(posts.length,1);assert.equal(posts[0].body.placement.objects.box[0].translation_m[2],.1);
assert.match(el('Status').textContent,/conflict/);assert.match(el('Results').children[0].textContent,/2\/61/);
assert.equal(scene.objects.box.keyframes[0].translation_m[2],.1);assert.equal(selected,null);
await el('Save').onclick();assert.equal(selected[1],'placement');assert.match(el('Status').textContent,/Original clips are preserved/);
editor.changed();assert.equal(el('Results').children.length,0);
report.status='not_ruled_out';report.rows[0].incompatible_frames=[];report.rows[0].maximum_error_lower_bound_m=.02;
await el('Check').onclick();assert.match(el('Status').textContent,/not a feasibility or quality pass/);
fail=true;await el('Check').onclick();assert.match(el('Status').textContent,/reload/);assert.equal(el('Save').disabled,false);
setup();editor=create();await editor.bind(metadata.source_url);deferred=wait();
let pending=el('Check').onclick();await el('Check').onclick();assert.equal(posts.length,1,'Duplicate check suppressed');
scene.actors.A.transform.translation_m[0]=1;deferred.resolve();await pending;
assert.match(el('Status').textContent,/changed during the check/);assert.equal(el('Results').children.length,0);
setup();editor=create();await editor.bind(metadata.source_url);deferred=wait();pending=el('Save').onclick();
editor.reset();metadata={...metadata,source_url:'/files/other/scene.json',revision:'r2'};await editor.bind(metadata.source_url);deferred.resolve();await pending;
assert.equal(selected,null,'Old save cannot select a newly loaded scene');assert.equal(el('Save').disabled,false);
setup();editor=create();await editor.bind(metadata.source_url);report.quality_approved=true;
await el('Check').onclick();assert.match(el('Status').textContent,/Invalid reach report/);
report.quality_approved=false;report.rows[0].maximum_error_lower_bound_m=NaN;
await el('Check').onclick();assert.match(el('Status').textContent,/Incomplete/);
report.rows[0].maximum_error_lower_bound_m=.103;report.source_url='/files/wrong/scene.json';
await el('Check').onclick();assert.match(el('Status').textContent,/different source/);
console.log('Placement editor: immutable draft capture, limits, explicit non-approval, duplicate/stale request handling, errors and source binding pass.');

const {placementPose,placementKeyOptions,objectEditKeys}=await import(new URL('../scripts/scene-placement-controls.mjs',import.meta.url));
const keys=[{frame:0,translation_m:[0,.2,0],rotation_xyzw:[0,0,0,1]},{frame:120,translation_m:[0,.6,0],rotation_xyzw:[0,0,0,1]}];
scene={actors:{A:{transform:{translation_m:[1,0,0],rotation_xyzw:[0,0,0,1]}}},objects:{box:{keyframes:keys}}};
assert.equal(placementPose(scene,'actor','A','key',120),scene.actors.A.transform);
assert.equal(placementPose(scene,'object','box','key',120),keys[1]);
assert.equal(placementPose(scene,'object','box','path',120),keys[0]);
assert.deepEqual(placementKeyOptions(scene,'object','box').map(o=>o.value),['0','120']);
assert.deepEqual(placementKeyOptions(scene,'actor','A'),[]);
const selectedKeys=objectEditKeys(scene,'box','key',120);selectedKeys[0].translation_m[1]=1.;
assert.equal(keys[0].translation_m[1],.2);assert.equal(keys[1].translation_m[1],1.);
assert.deepEqual(keys.map(k=>k.frame),[0,120]);assert.equal(objectEditKeys(scene,'box','path',120).length,2);
assert.throws(()=>placementPose(scene,'object','box','key',119));assert.throws(()=>placementPose(scene,'object','box','key',120.5));
assert.throws(()=>objectEditKeys(scene,'box','unknown',120));assert.throws(()=>placementPose(scene,'object','missing','path',0));
console.log('Saved-pose controls: actor placement, path/key selection, untouched neighbor poses and clocks, and invalid key rejection pass.');
