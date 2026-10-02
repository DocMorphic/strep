import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {intervals,annotate,createCorrectionReviewPanel} from '../scripts/correction-review-panel.mjs';

assert.deepEqual(intervals([null,null,true,false,false]),[
 {start_frame:0,end_frame_exclusive:2,contact:null},
 {start_frame:2,end_frame_exclusive:3,contact:true},
 {start_frame:3,end_frame_exclusive:5,contact:false}]);
assert.deepEqual(annotate([null,null,null],1,3,false),[null,false,false]);
assert.throws(()=>annotate([null],0,1,0));
assert.throws(()=>annotate([null],0,2,true));

const html=readFileSync(new URL('../scripts/correction-review-panel.html',import.meta.url),'utf8');
const ids=new Set([...html.matchAll(/id="([^"]+)"/g)].map(m=>m[1]));
const nodes=new Map();
const el=id=>{
 assert(ids.has(id),'Controller ID is present in markup: '+id);
 if(!nodes.has(id))nodes.set(id,{
  _value:'',get value(){return this._value;},set value(v){this._value=String(v);},
  checked:false,disabled:false,textContent:'',open:false,children:[],
  addEventListener(type,fn){this[type]=fn;},closest(){return null;},
  replaceChildren(...items){this.children=items;if(items[0]?.value!==undefined)this.value=items[0].value;},
  append(item){this.children.push(item);}
 });return nodes.get(id);
};
const joints=['LeftFoot','LeftToeBase','RightFoot','RightToeBase'];
const packet={draft_id:'kimodo-target-review-fixture',draft_sha256:'a'.repeat(64),
 items:[{id:'one',prompt:'Wave'},{id:'two',prompt:'Sit'}]};
function metadata(id,candidate='reports/original.npz',start=0){return {...packet,item_id:id,prompt:id,frames:3,fps:30,source_start_frame:id==='one'?0:90,
 recipe:{schema:'strep-native-correction-pack-recipe-v1',item_id:id,candidate_motion:{path:candidate,sha256:'b'.repeat(64)},candidate_start_frame:start,
 joint_names:Array.from({length:77},(_,j)=>'Joint'+j),contacts:joints.map(joint=>({joint,intervals:[{start_frame:0,end_frame_exclusive:3,contact:null}]}))},
 candidate_relative:candidate,quality_approved:false,training_admitted:false,preview_scope:'Original only',preview_start_s:id==='one'?0:3,preview_end_s:(id==='one'?0:3)+2/30};}
let posts=[],calls=[],pending=null,playerLoads=0,pauses=0,timeCallback,loaded=[],supportOptions,supportResets=0;
const fetch=async(url,options)=>{
 calls.push(url);if(pending)return pending;
 let data;
 if(url==='/api/correction-review-drafts')data={drafts:[{id:packet.draft_id,sha256:packet.draft_sha256,segments:2,quality_approved:false}]};
 else if(url.startsWith('/api/correction-review-packet?'))data=metadata('one');
 else if(url.startsWith('/api/correction-review-source?')){const q=new URLSearchParams(url.split('?')[1]);data=metadata(q.get('item'),q.get('candidate')||undefined,Number(q.get('start')||0));}
 else if(url==='/api/correction-review-edit'){
  const body=JSON.parse(options.body);posts.push({url,body});const m=metadata(body.item_id,'reports/native-correction-edits/edited'+posts.length+'/candidate.npz',0);
  const previewSelection={draft_id:body.draft_id,draft_sha256:body.draft_sha256,item_id:body.item_id,candidate_motion:m.recipe.candidate_motion,candidate_start_frame:0};
  data={selection:body,metadata:m,candidate_motion:m.recipe.candidate_motion,candidate_start_frame:0,quality_approved:false,training_admitted:false,release_approved:false,
   report:{measured:{joint_from_original_degrees:3,root_from_original_m:.01,correction_step_degrees:3,root_correction_step_m:.01}},
   preview:{id:'editfixture',selection:previewSelection,preview_url:'/files/native-correction-previews/editfixture/candidate.glb',preview_sha256:'d'.repeat(64),preview_start_s:0,preview_end_s:2/30,quality_approved:false,training_admitted:false,preview_scope:'Edited numerical candidate'}};
 }
 else {const body=JSON.parse(options.body);posts.push({url,body});data=url.endsWith('-preview')?{id:'synthetic',selection:body,item_id:body.item_id,preview_url:'/files/native-correction-previews/synthetic/candidate.glb',preview_sha256:'c'.repeat(64),preview_start_s:0,preview_end_s:2/30,preview_scope:'Selected candidate',training_admitted:false,quality_approved:false}:url.endsWith('-pack')?{id:'packed',item_id:body.recipe.item_id,folder:'reports/packed',training_admitted:false,quality_approved:false}:
 {submission:{path:'fixture-submission.json'},reviewed_corrections:1,training_admitted:false};}
 return {ok:true,json:async()=>data};
};
const panel=el('correctionReviewPanel');panel.open=true;
el('correctionContactJoint').value='0';el('correctionContactState').value='free';el('correctionReviewerRole').value='developer';
const ui=createCorrectionReviewPanel({document:{getElementById:el,createElement(){return {textContent:''};}},fetch,
 Option:function(text,value){return {text,value};},MutationObserver:null,now:()=> '2026-10-02T12:00:00+00:00',
 createSupportEditor:options=>{supportOptions=options;return {reset(){supportResets++;}};},
 createPlayer:async({onTime})=>{timeCallback=onTime;return {pause(){pauses++;},async load(data){playerLoads++;loaded.push(data);},seek(){},toggle(){},fit(){}};}});
assert.equal(calls.length,0,'No automatic requests before opening');
await ui.refresh();await ui.load();
assert.equal(playerLoads,1);
assert.equal(el('correctionReviewDecision').value,'unreviewed');
assert.equal(el('correctionReviewCleanupSeconds').value,'');
assert.equal(el('correctionRightsPermitted').checked,false);
assert.equal(el('correctionReviewPack').disabled,true);
assert.match(el('correctionContactCoverage').textContent,/0 \/ 12/);
el('correctionContactStart').value='';el('correctionContactEnd').value='3';el('correctionContactSet').onclick();
assert.match(el('correctionReviewStatus').textContent,/both interval/);
for(let joint=0;joint<4;joint++){el('correctionContactJoint').value=joint;el('correctionContactWhole').onclick();}
assert.equal(el('correctionReviewPack').disabled,false);await ui.pack();
assert.equal(posts.length,1);assert.equal(posts[0].body.recipe.contacts[0].intervals[0].contact,false);
el('correctionContactState').value='unknown';el('correctionContactWhole').onclick();
assert.equal(el('correctionReviewPack').disabled,true);
el('correctionReviewDecision').value='accept_corrected';el('correctionReviewNotes').value='Synthetic test only';
el('correctionReviewerName').value='Numerical fixture';await ui.save();assert.equal(posts.length,1);
el('correctionContactState').value='free';el('correctionContactWhole').onclick();await ui.pack();
el('correctionReviewSplit').value='train';
for(const id of ['correctionSemanticPass','correctionQualityPass','correctionContactPass'])el(id).checked=true;
await ui.bind('two');timeCallback(3);assert.match(el('correctionReviewClock').textContent,/Frame 0/,'Clock uses current segment start');
assert.equal(el('correctionReviewDecision').value,'unreviewed');
el('correctionReviewDecision').value='exclude';el('correctionReviewNotes').value='Synthetic exclusion';
await ui.bind('one');assert.equal(el('correctionReviewDecision').value,'accept_corrected');
assert.equal(el('correctionSemanticPass').checked,true);
await ui.save();assert.equal(posts.length,2,'Empty cleanup cannot become automatic zero');
assert.match(el('correctionReviewStatus').textContent,/measured cleanup/);
el('correctionReviewCleanupSeconds').value='0';await ui.save();assert.equal(posts.length,2,'No automatic permission');
el('correctionRightsName').value='Numerical fixture';el('correctionRightsEvidence').value='reports/fixture.txt';
el('correctionRightsObligations').value='Fixture only';el('correctionRightsNotes').value='No actual rights';el('correctionRightsPermitted').checked=true;
await ui.save();assert.equal(posts.length,3);assert.equal(posts[2].body.items[0].cleanup_seconds,0);
assert.equal(posts[2].body.items[1].rights,null);
assert.equal(posts[2].body.reviewer.name,'Numerical fixture');
await ui.bind('one','reports/edited.npz',0);
assert.equal(el('correctionReviewDecision').value,'unreviewed','Changed candidate resets bound claims');
assert.equal(el('correctionRightsPermitted').checked,false);
el('correctionReviewDecision').value='exclude';el('correctionReviewNotes').value='Synthetic excluded';
await ui.save();assert.equal(posts.length,4);assert(posts[3].body.items.every(i=>i.pack_id===null));
await ui.buildPreview();assert.equal(posts.length,5);assert.equal(posts[4].url,'/api/correction-review-preview');
assert.equal(el('correctionPreviewVersion').value,'candidate');
assert.equal(loaded.at(-1).preview_url,'/files/native-correction-previews/synthetic/candidate.glb');
assert.equal(el('correctionRightsPermitted').checked,false,'Preview does not authorize data');
assert.equal(el('correctionReviewDecision').value,'exclude','Preview preserves an explicit decision');
assert.match(el('correctionContactCoverage').textContent,/0 \/ 12/,'Preview does not guess contacts');
await ui.bind('two');await ui.buildPreview();timeCallback(0);
assert.match(el('correctionReviewClock').textContent,/Frame 0/);assert.equal(el('correctionReviewTime').min,0);
await ui.showPreview('original');timeCallback(3);
assert.match(el('correctionReviewClock').textContent,/Frame 0/);assert.equal(el('correctionReviewTime').min,3);
await ui.bind('one','reports/another-edited.npz',0);await ui.showPreview('candidate');
assert.match(el('correctionReviewStatus').textContent,/Build the selected/,'Changed candidate does not reuse a stale preview');
for(const prefix of ['Rotation','Root'])for(const axis of ['X','Y','Z'])el('correctionEdit'+prefix+axis).value=0;
const editPostCount=posts.length;await ui.applyEdit();assert.equal(posts.length,editPostCount,'Zero offset is not submitted');
el('correctionEditRotationX').value='3';el('correctionEditRootY').value='.01';
el('correctionEditStart').value='';await ui.applyEdit();assert.equal(posts.length,editPostCount,'Empty frame key cannot become zero');
el('correctionEditStart').value=0;el('correctionEditPeak').value=1;el('correctionEditEnd').value=2;
el('correctionSemanticPass').checked=true;el('correctionRightsPermitted').checked=true;el('correctionReviewCleanupSeconds').value=12;
await ui.applyEdit();assert.equal(posts.length,editPostCount+1);const editPost=posts.at(-1);
assert.equal(editPost.url,'/api/correction-review-edit');assert.deepEqual(editPost.body.edit,{joint:'Joint0',rotation_vector_degrees:[3,0,0],root_offset_m:[0,.01,0],start_frame:0,peak_frame:1,end_frame:2});
assert.equal(el('correctionPreviewVersion').value,'candidate');assert.equal(el('correctionReviewDecision').value,'unreviewed');
assert.equal(el('correctionSemanticPass').checked,false);assert.equal(el('correctionRightsPermitted').checked,false);assert.equal(el('correctionReviewCleanupSeconds').value,'');
assert.match(el('correctionContactCoverage').textContent,/0 \/ 12/);assert.equal(el('correctionEditUndo').disabled,false);
assert.match(el('correctionEditReport').textContent,/3.000°/);const savedCandidate=el('correctionCandidatePath').value;
await ui.bind('two');await ui.bind('one');assert.equal(el('correctionCandidatePath').value,savedCandidate,'Switching segments keeps the edited candidate');
await ui.undoEdit();assert.equal(el('correctionCandidatePath').value,'reports/another-edited.npz');assert.equal(el('correctionEditUndo').disabled,true);
assert.equal(el('correctionPreviewVersion').value,'candidate','Undo previews the restored geometry');
await ui.applyEdit();assert.match(el('correctionCandidatePath').value,/native-correction-edits/);
await el('correctionEditOriginal').onclick();assert.equal(el('correctionCandidatePath').value,'reports/original.npz');assert.equal(el('correctionEditUndo').disabled,true);
let resolve;pending=new Promise(r=>resolve=r);const before=playerLoads,waiting=ui.buildPreview();panel.open=false;panel.toggle();
resolve({ok:true,json:async()=>({selection:{},preview_url:'/files/native-correction-previews/stale/candidate.glb'})});await waiting;
assert.equal(playerLoads,before,'Closed panel ignores a late candidate export');pending=null;panel.open=true;
const previous=el('correctionReviewItem').value;
pending=new Promise(r=>resolve=r);const binding=ui.bind('two');panel.open=false;panel.toggle();
resolve({ok:true,json:async()=>metadata('two')});await binding;assert.equal(el('correctionReviewItem').value,previous);
assert(pauses>0);
console.log('Correction review: explicit human fields, original/candidate switching, exact preview binding, separate clocks, candidate reset and stale responses pass.');

panel.open=true;pending=new Promise(r=>resolve=r);const editBefore=el('correctionCandidatePath').value,editWaiting=ui.applyEdit();panel.open=false;panel.toggle();resolve({ok:true,json:async()=>({selection:{}})});await editWaiting;assert.equal(el('correctionCandidatePath').value,editBefore,'Closed panel ignores late native authoring');pending=null;
console.log('Native authoring: explicit vectors and clock, new candidate, unset contacts/reviews/cleanup, segment persistence, undo, original reset and stale edits pass.');

panel.open=true;await ui.buildPreview();assert.equal(supportOptions.prefix,'correctionSupport');assert.deepEqual(supportOptions.getContext(),{job:{id:'synthetic'},variant:'native_review'});const supportParent=structuredClone(posts.at(-1).body);const supportRef={path:'reports/native-support-jobs/numerical/native-candidate.npz',sha256:'b'.repeat(64)};const supportResult={selection:supportParent,candidate_motion:supportRef,candidate_start_frame:0,quality_approved:false,training_admitted:false,release_approved:false,retained_input:true,retention_reason:'no_proposal_satisfies_all_bounds',preview:{id:'converted',selection:{...supportParent,candidate_motion:supportRef,candidate_start_frame:0},preview_url:'/files/native-correction-previews/converted/candidate.glb',preview_sha256:'e'.repeat(64),preview_start_s:0,preview_end_s:2/30,quality_approved:false,training_admitted:false}};await assert.rejects(()=>supportOptions.onNativeCandidate({...supportResult,selection:{...supportParent,item_id:'another'}}),/another selected/);el('correctionSemanticPass').checked=true;el('correctionReviewCleanupSeconds').value=4;await supportOptions.onNativeCandidate(supportResult);assert.equal(el('correctionCandidatePath').value,supportRef.path);assert.equal(el('correctionSemanticPass').checked,false);assert.equal(el('correctionReviewCleanupSeconds').value,'');assert.match(el('correctionContactCoverage').textContent,/0 \/ 12/);assert.match(el('correctionReviewStatus').textContent,/retained its input/);assert.equal(el('correctionEditUndo').disabled,false);assert(supportResets>0);console.log('Native support bridge: exact selected candidate, explicit use, retained failure, review reset and undo pass.');
