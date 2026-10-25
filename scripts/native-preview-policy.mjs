// Pure binding/clip selection; renderer behavior is verified separately.
export function validateNativePreview(data){
 const continuation=data?.kind==='native_key_continuation',surface=data?.kind==='native_surface_correction',native=data?.kind==='native_rig_transfer'||continuation||surface;
 const valid=surface?typeof data.preview_url==='string'&&/^\/files\/surface-clip-jobs\/[a-f0-9]{32}\/[a-f0-9]{32}\/(original|candidate|rejected)\.glb$/.test(data.preview_url):continuation?typeof data.preview_url==='string'&&/^\/files\/key-continuation-jobs\/[A-Za-z0-9_-]{1,100}\/(input\/saved-start|study\/probes\/final\/character)\.glb$/.test(data.preview_url):native?(typeof data.preview_url==='string'&&(/^\/files\/native-transfer-jobs\/[A-Za-z0-9_-]{1,100}\/transfer\/character\.glb$/.test(data.preview_url)||/^\/files\/character-assets\/[a-f0-9]{64}\/character\.glb$/.test(data.preview_url))):typeof data?.preview_url==='string'&&['/files/action-jobs/','/files/native-correction-previews/'].some(p=>data.preview_url.startsWith(p));
 if(!valid||!/^[a-f0-9]{64}$/.test(data.preview_sha256)||![data.preview_start_s,data.preview_end_s].every(Number.isFinite)||data.preview_start_s<0||data.preview_end_s<data.preview_start_s)throw Error('Bound native preview required');
 if(native&&(!Number.isInteger(data.animation_index)||data.animation_index<0||!Number.isInteger(data.animation_count)||data.animation_count<1||data.animation_index>=data.animation_count))throw Error('Bound animation selection required');
}
export function selectNativePreviewClip(data,clips){
 validateNativePreview(data);const native=['native_rig_transfer','native_key_continuation','native_surface_correction'].includes(data.kind),index=native?data.animation_index:0;
 if(!Array.isArray(clips)||clips.length!==(native?data.animation_count:1)||!clips[index]||!Number.isFinite(clips[index].duration)||data.preview_end_s>clips[index].duration+1e-5)throw Error('Native preview clock or clip population differs');
 return clips[index];
}
