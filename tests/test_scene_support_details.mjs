import assert from 'node:assert/strict';
import {sceneSupportDetails} from '../scripts/scene-region-editor.js';

assert.deepEqual(sceneSupportDetails(null),[]);
assert.deepEqual(sceneSupportDetails({}),[]);
const row={samples:34,failures:0,maximum_error_m:.00497331,vertex_identity_gaps:0,sampled_point_preservation_passed:true};
const detail=changes=>sceneSupportDetails({preserved_support:{...row,...changes}}).join('\n');
assert.match(detail({}),/sampled checks pass/);
assert.match(detail({}),/4\.973 mm/);
assert.match(detail({failures:34,maximum_error_m:.075634,sampled_point_preservation_passed:false}),/34\/34.*75\.634 mm/);
assert.doesNotMatch(detail({vertex_identity_gaps:1}),/checks pass/);
assert.match(detail({vertex_identity_gaps:1}),/1 sample could/);
assert.doesNotMatch(detail({samples:0,maximum_error_m:null}),/checks pass/);
for(const changes of [{maximum_error_m:NaN},{failures:35},{samples:-1},{vertex_identity_gaps:.5},{sampled_point_preservation_passed:'true'}]){
 assert.match(detail(changes),/incomplete or invalid/);
 assert.doesNotMatch(detail(changes),/checks pass/);
}
assert.match(detail({}),/do not establish a planted sole/);
console.log('Support details preserve pass, failure, missing data and coverage limits.');
