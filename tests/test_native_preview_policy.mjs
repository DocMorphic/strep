import assert from 'node:assert/strict';
import {validateNativePreview,selectNativePreviewClip} from '../scripts/native-preview-policy.mjs';
const source={kind:'native_rig_transfer',preview_url:'/files/character-assets/'+'a'.repeat(64)+'/character.glb',preview_sha256:'a'.repeat(64),preview_start_s:0,preview_end_s:2.001,animation_index:1,animation_count:2};
const clips=[{duration:.73,id:'old-target'},{duration:2.001,id:'candidate'}];
assert.equal(selectNativePreviewClip(source,clips),clips[1]);
const candidate={...source,preview_url:'/files/native-transfer-jobs/job/transfer/character.glb'};validateNativePreview(candidate);
for(const patch of [{preview_url:'https://example.test/a.glb'},{preview_url:'/files/native-transfer-jobs/../transfer/character.glb'},{preview_url:source.preview_url+'?x=1'},
 {preview_sha256:'bad'},{preview_start_s:NaN},{preview_end_s:Infinity},{animation_index:false},{animation_index:-1},{animation_index:2},{animation_count:1}])assert.throws(()=>selectNativePreviewClip({...source,...patch},clips));
assert.throws(()=>selectNativePreviewClip(source,clips.slice(1)));assert.throws(()=>selectNativePreviewClip({...source,preview_end_s:3},clips));
const legacy={preview_url:'/files/action-jobs/job/a.glb',preview_sha256:'b'.repeat(64),preview_start_s:0,preview_end_s:1};
assert.equal(selectNativePreviewClip(legacy,[{duration:1}]).duration,1);assert.throws(()=>selectNativePreviewClip(legacy,clips));
assert.throws(()=>validateNativePreview({...legacy,preview_url:candidate.preview_url}));
console.log('Native preview appended-clip selection, exact populations, legacy single-clip behavior and malformed clock/path rejection passed.');
