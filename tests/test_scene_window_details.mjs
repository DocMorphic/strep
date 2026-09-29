import assert from 'node:assert/strict';
import {sceneWindowDetails} from '../scripts/scene-region-editor.js';
const row={frames:180,requested_window:[48,133],suggested_geometry_envelope:[23,133],sampled_failures:379,
 failure_counts:{locked_segments:50,boundary_segments:3,edited_window:326},locked_geometry_conflict:true};
const details=change=>sceneWindowDetails({window_geometry:{...row,...change}}).join('\n');
assert.deepEqual(sceneWindowDetails(null),[]);
assert.match(details({}),/326 inside, 3 across the boundary, 50 in locked/);
assert.match(details({}),/cannot repair/);
assert.match(details({}),/23–133/);
assert.match(details({}),/has not been changed/);
assert.match(details({}),/does not guarantee/);
for(const change of [{requested_window:[0,180]},{suggested_geometry_envelope:[-1,133]},
 {suggested_geometry_envelope:[49,133]},{sampled_failures:0},{locked_geometry_conflict:false},{failure_counts:{}},{frames:NaN}]){
 assert.match(details(change),/incomplete or invalid/);
 assert.doesNotMatch(details(change),/Suggested range/);
}
const clean={failure_counts:{locked_segments:0,boundary_segments:0,edited_window:0},sampled_failures:0,
 locked_geometry_conflict:false,suggested_geometry_envelope:[48,133]};
assert.doesNotMatch(details(clean),/cannot repair|Suggested range|checks pass|approved/);
console.log('Edit-range diagnostics retain failures, scope, invalid evidence and limitations.');
