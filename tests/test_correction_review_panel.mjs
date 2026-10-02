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
 contacts:joints.map(joint=>({joint,intervals:[{start_frame:0,end_frame_exclusive:3,contact:null}]}))},
 candidate_relative:candidate,quality_approved:false,training_admitted:false,preview_scope:'Original only',preview_start_s:id==='one'?0:3,preview_end_s:(id==='one'?0:3)+2/30};}
let posts=[],calls=[],pending=null,playerLoads=0,pauses=0,timeCallback,loaded=[];
const fetch=async(url,options)=>{
 calls.push(url);if(pending)return pending;
 let data;
 if(url==='/api/correction-review-drafts')data={drafts:[{id:packet.draft_id,sha256:packet.draft_sha256,segments:2,quality_approved:false}]};
 else if(url.startsWith('/api/correction-review-packet?'))data=metadata('one');
 else if(url.startsWith('/api/correction-review-source?')){const q=new URLSearchParams(url.split('?')[1]);data=metadata(q.get('item'),q.get('candidate')||undefined,Number(q.get('start')||0));}
 else {const body=JSON.parse(options.body);posts.push({url,body});data=url.endsWith('-preview')?{selection:body,item_id:body.item_id,preview_url:'/files/native-correction-previews/synthetic/candidate.glb',preview_sha256:'c'.repeat(64),preview_start_s:0,preview_end_s:2/30,preview_scope:'Selected candidate',training_admitted:false,quality_approved:false}:url.endsWith('-pack')?{id:'packed',item_id:body.recipe.item_id,folder:'reports/packed',training_admitted:false,quality_approved:false}:
 {submission:{path:'fixture-submission.json'},reviewed_corrections:1,training_admitted:false};}
 return {ok:true,json:async()=>data};
};
const panel=el('correctionReviewPanel');panel.open=true;
el('correctionContactJoint').value='0';el('correctionContactState').value='free';el('correctionReviewerRole').value='developer';
const ui=createCorrectionReviewPanel({document:{getElementById:el,createElement(){return {textContent:''};}},fetch,
 Option:function(text,value){return {text,value};},MutationObserver:null,now:()=> '2026-10-02T12:00:00+00:00',
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
let resolve;pending=new Promise(r=>resolve=r);const before=playerLoads,waiting=ui.buildPreview();panel.open=false;panel.toggle();
resolve({ok:true,json:async()=>({selection:{},preview_url:'/files/native-correction-previews/stale/candidate.glb'})});await waiting;
assert.equal(playerLoads,before,'Closed panel ignores a late candidate export');pending=null;panel.open=true;
const previous=el('correctionReviewItem').value;
pending=new Promise(r=>resolve=r);const binding=ui.bind('two');panel.open=false;panel.toggle();
resolve({ok:true,json:async()=>metadata('two')});await binding;assert.equal(el('correctionReviewItem').value,previous);
assert(pauses>0);
console.log('Correction review: explicit human fields, original/candidate switching, exact preview binding, separate clocks, candidate reset and stale responses pass.');
