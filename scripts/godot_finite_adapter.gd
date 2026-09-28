extends "godot_cycle_adapter.gd"
## Unbounded simulation clock, finite clamped pose and non-repeating markers.
signal clip_finished
var last_sample_s := 0.0
var duration_s := 0.0

func bind_finite(p: AnimationPlayer, s: Skeleton3D, actor: Node3D, animation_name: StringName, data: Dictionary, glb_path: String, extract: bool = false) -> Error:
	if bound or p==null or s==null or actor==null or not actor.is_ancestor_of(s) or not p.has_animation(animation_name): return ERR_INVALID_PARAMETER
	if data.get("schema")!="strep-runtime-finite-v1" or data.get("fps")!=30: return ERR_INVALID_DATA
	if not data.get("glb_sha256") is String or FileAccess.get_sha256(glb_path)!=data.glb_sha256: return ERR_INVALID_DATA
	var frames := float(data.get("frames",0))
	if not is_finite(frames) or frames!=floor(frames) or frames<2 or frames>900 or not data.get("root_bone") is String: return ERR_INVALID_DATA
	var bone := s.find_bone(data.root_bone)
	var animation := p.get_animation(animation_name)
	if bone<0 or animation.loop_mode!=Animation.LOOP_NONE or not p.root_motion_track.is_empty() or abs(animation.length-(frames-1)/30.0)>0.00001: return ERR_INVALID_DATA
	if not data.get("markers") is Array: return ERR_INVALID_DATA
	var previous := -1
	for event in data.markers:
		if not event is Dictionary or not event.get("name") is String: return ERR_INVALID_DATA
		var frame := float(event.get("phase_frame",-1))
		if not is_finite(frame) or frame!=floor(frame) or frame<0 or frame>=frames or frame<previous or event.get("first_cycle")!=0: return ERR_INVALID_DATA
		previous=int(frame)
	player=p; skeleton=s; space=actor; clip=animation_name; root_bone=bone; extracted=extract
	last_sample_s=(frames-1)/30.0; duration_s=frames/30.0; period=duration_s
	markers=data.markers.duplicate(true)
	player.callback_mode_process=AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_MANUAL
	player.play(clip);player.seek(0.0,true,true)
	anchor=space.global_transform.affine_inverse()*skeleton.global_transform*skeleton.get_bone_global_pose(root_bone)
	bound=true
	return seek_preview(0.0)

func sample(seconds: float) -> void:
	player.seek(minf(seconds,last_sample_s),true,true)
	var relative := space.global_transform.affine_inverse()*skeleton.global_transform
	var original := relative*skeleton.get_bone_global_pose(root_bone)
	root_motion_transform=original*anchor.affine_inverse()
	if extracted: skeleton.set_bone_global_pose(root_bone,relative.affine_inverse()*anchor)
	skeleton.force_update_all_bone_transforms()

func advance(seconds: float) -> Error:
	if not bound or not is_finite(seconds) or seconds<0 or seconds/period>1024 or (time_s+seconds)/period>1000000: return ERR_INVALID_PARAMETER
	if seconds==0:
		root_motion_delta=Transform3D.IDENTITY;return OK
	var before := time_s
	var increment := seconds-time_correction
	var after := before+increment
	time_correction=(after-before)-increment
	var previous := root_motion_transform
	sample(after);time_s=after;root_motion_delta=previous.affine_inverse()*root_motion_transform
	for event in markers:
		var at := float(event.phase_frame)/fps
		if at>before and at<=after: dispatch(event,0)
	if before<duration_s and after>=duration_s: clip_finished.emit()
	return OK

func rewind(seconds: float, notify_crossings: bool = false) -> Error:
	if not bound or not is_finite(seconds) or seconds<0 or seconds/period>1024: return ERR_INVALID_PARAMETER
	if seconds==0:
		root_motion_delta=Transform3D.IDENTITY;return OK
	var before := time_s
	var increment := -seconds-time_correction
	var after := 0.0 if seconds==before else before+increment
	if not is_finite(after) or after<0 or after/period>1000000: return ERR_INVALID_PARAMETER
	var correction := 0.0 if seconds==before else (after-before)-increment
	var previous := root_motion_transform
	sample(after);time_s=after;time_correction=correction
	root_motion_delta=previous.affine_inverse()*root_motion_transform
	if notify_crossings:
		for index in range(markers.size()-1,-1,-1):
			var event: Dictionary=markers[index]
			var at := float(event.phase_frame)/fps
			if at>=after and at<before:
				var value: Dictionary=event.duplicate(true)
				value.cycle=0;value.time_s=at;value.direction=-1
				marker_reversed.emit(value)
	return OK
