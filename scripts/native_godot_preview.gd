extends RefCounted

# Scrubbing only: evaluate native bone tracks without playback end snapping.
# This does not advance playback or dispatch gameplay/method/audio events.
static func seek(player: AnimationPlayer, skeleton: Skeleton3D, animation: Animation, time_s: float) -> Error:
	if not is_finite(time_s) or time_s < 0.0 or time_s > animation.length or animation.loop_mode != Animation.LOOP_NONE:
		return ERR_INVALID_PARAMETER
	var root_node := player.get_node(player.root_node)
	var skeleton_path := str(root_node.get_path_to(skeleton))
	var targets: Array = []
	for track in range(animation.get_track_count()):
		var path := animation.track_get_path(track)
		if path.get_subname_count() != 1 or str(path.get_concatenated_names()) != skeleton_path or animation.track_get_key_count(track) == 0 or animation.track_get_interpolation_type(track) != Animation.INTERPOLATION_LINEAR:
			return ERR_INVALID_DATA
		var bone := skeleton.find_bone(path.get_subname(0))
		var kind := animation.track_get_type(track)
		if bone < 0 or kind not in [Animation.TYPE_POSITION_3D, Animation.TYPE_ROTATION_3D, Animation.TYPE_SCALE_3D]:
			return ERR_INVALID_DATA
		targets.append(bone)
	player.seek(time_s, false)
	for track in range(animation.get_track_count()):
		var bone: int = targets[track]
		match animation.track_get_type(track):
			Animation.TYPE_POSITION_3D: skeleton.set_bone_pose_position(bone, animation.position_track_interpolate(track, time_s))
			Animation.TYPE_ROTATION_3D: skeleton.set_bone_pose_rotation(bone, animation.rotation_track_interpolate(track, time_s))
			Animation.TYPE_SCALE_3D: skeleton.set_bone_pose_scale(bone, animation.scale_track_interpolate(track, time_s))
	return OK
