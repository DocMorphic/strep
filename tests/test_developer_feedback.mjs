// Synthetic test fixtures only; never written to human-review evidence.
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
const context=vm.createContext({});
vm.runInContext(readFileSync(new URL('../scripts/developer-feedback.js',import.meta.url),'utf8'),context);
const source={case_id:'synthetic-case',variant:'selected',frames:120,fps:30,glb_sha256:'a'.repeat(64),catalog_sha256:'b'.repeat(64)};
const note={reviewer:'Synthetic fixture',notes:'Synthetic fixture; not a human review.',start:0,end:119};
const result=context.developerObservation(source,note,'2026-09-28T00:00:00Z');
assert.equal(result.independent_human,false);assert.equal(result.quality_approved,false);assert.equal(result.cleanup_test_performed,false);
assert.equal(result.source.glb_sha256,source.glb_sha256);assert.equal(result.source.catalog_sha256,source.catalog_sha256);
assert.equal(result.frame_range.end_inclusive,119);
for(const change of [{reviewer:''},{reviewer:' '},{notes:''},{notes:' '},{notes:'x'.repeat(4001)},
 {start:-1},{start:1.5},{end:120},{start:10,end:9},{start:NaN},{end:Infinity}]){
 assert.throws(()=>context.developerObservation(source,{...note,...change}));
}
for(const change of [{glb_sha256:'tampered'},{catalog_sha256:''},{frames:0},{frames:2.5}]){
 assert.throws(()=>context.developerObservation({...source,...change},note));
}
assert.throws(()=>context.developerObservation(null,note));
console.log('Developer feedback: provenance, terminal frame, empty input and invalid-range guards pass. Synthetic fixtures only.');
