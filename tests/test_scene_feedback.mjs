// Synthetic notes remain in memory; these are not human-review submissions.
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
const elements=new Map(),storage=new Map();
const el=id=>{if(!elements.has(id))elements.set(id,{value:'',disabled:false,textContent:'',addEventListener(name,fn){this[name]=fn;}});return elements.get(id);};
const ctx=vm.createContext({structuredClone,TextDecoder,DataView,document:{getElementById:el},localStorage:{getItem:k=>storage.get(k)||null,setItem:(k,v)=>storage.set(k,v)}});
vm.runInContext(readFileSync(new URL('../scripts/scene-feedback.js',import.meta.url),'utf8'),ctx);
const source={bundle_url:'/files/scene-region-jobs/synthetic/candidate.json',bundle_sha256:'a'.repeat(64),scene_id:'synthetic',frames:120,fps:30,actors:[{actor:'A',glb_url:'/files/scene-region-jobs/synthetic/A.glb',glb_sha256:'b'.repeat(64)},{actor:'B',glb_url:'/files/scene-region-jobs/synthetic/B.glb',glb_sha256:'c'.repeat(64)}]};
const draft={reviewer:'Synthetic',notes:'Synthetic observation; not human evidence.',start:0,end:119};
const note=ctx.sceneObservation(source,draft);assert.equal(note.quality_approved,false);assert.equal(note.independent_human,false);assert.equal(note.cleanup_test_performed,false);assert.deepEqual(note.source,source);
for(const delta of [{start:-1},{end:120},{start:false},{start:2,end:1},{notes:' '},{reviewer:''},{end:Infinity}])assert.throws(()=>ctx.sceneObservation(source,{...draft,...delta}));
assert.throws(()=>ctx.sceneObservation(null,draft));
let frame=119;const ui=ctx.setupSceneFeedback(()=>frame);ui.bind(source);
assert.equal(el('sceneFeedbackFields').disabled,false);
el('sceneReviewer').value=draft.reviewer;el('sceneReviewNote').value=draft.notes;el('sceneReviewNote').input();
assert.equal(el('sceneExportFeedback').disabled,false);ui.bind(null);assert.equal(el('sceneFeedbackFields').disabled,true);assert.equal(el('sceneExportFeedback').disabled,true);
ui.bind(source);assert.equal(el('sceneReviewNote').value,draft.notes);assert.equal(Number(el('sceneNoteEnd').value),119);
const changed=structuredClone(source);changed.actors[1].glb_sha256='d'.repeat(64);ui.bind(changed);assert.equal(el('sceneReviewNote').value,'');assert.equal(el('sceneExportFeedback').disabled,true);
ui.bind(source);assert.equal(el('sceneReviewNote').value,draft.notes);
el('sceneNoteEnd').value='';el('sceneNoteEnd').input();assert.equal(el('sceneExportFeedback').disabled,true);
frame=60;el('sceneNoteHere').onclick();assert.equal(Number(el('sceneNoteStart').value),60);assert.equal(Number(el('sceneNoteEnd').value),60);
function glb(doc){const json=new TextEncoder().encode(JSON.stringify(doc));const bytes=new ArrayBuffer(json.length+20),v=new DataView(bytes);[0x46546c67,2,bytes.byteLength,json.length,0x4e4f534a].forEach((x,i)=>v.setUint32(i*4,x,true));new Uint8Array(bytes,20).set(json);return bytes;}
assert.equal(ctx.sceneReviewEmbeddedGLB(glb({buffers:[{byteLength:4}]})),true);
assert.equal(ctx.sceneReviewEmbeddedGLB(glb({buffers:[{uri:'external.bin'}]})),false);
assert.equal(ctx.sceneReviewEmbeddedGLB(new ArrayBuffer(3)),false);
console.log('Scene feedback: exact scene/partner draft isolation, invalidation, frame guards and embedded-asset checks pass.');
