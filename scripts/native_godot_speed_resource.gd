extends RefCounted

# Load the exact saved resource being exported. No regeneration or resaving.
static func install(player: AnimationPlayer, skeleton: Skeleton3D, payload: Dictionary, path: String) -> Error:
	var animation := ResourceLoader.load(path, "Animation", ResourceLoader.CACHE_MODE_IGNORE) as Animation
	if animation == null or animation.length != float(payload.duration_s) or animation.loop_mode != Animation.LOOP_NONE or animation.get_track_count() != payload.channels.size():
		return ERR_INVALID_DATA
	var skeleton_path := str(player.get_node(player.root_node).get_path_to(skeleton))
	var types := {"translation": Animation.TYPE_POSITION_3D, "rotation": Animation.TYPE_ROTATION_3D, "scale": Animation.TYPE_SCALE_3D}
	for track in range(animation.get_track_count()):
		var channel: Dictionary = payload.channels[track]
		if not types.has(channel.path) or animation.track_get_type(track) != types[channel.path] or animation.track_get_path(track) != NodePath(skeleton_path + ":" + str(channel.bone)) or animation.track_get_interpolation_type(track) != Animation.INTERPOLATION_LINEAR or animation.track_get_interpolation_loop_wrap(track):
			return ERR_INVALID_DATA
		if animation.track_get_key_count(track) != channel.times_s.size() or skeleton.find_bone(channel.bone) < 0:
			return ERR_INVALID_DATA
		for key in range(channel.times_s.size()):
			if animation.track_get_key_time(track, key) != float(PackedFloat32Array([channel.times_s[key]])[0]):
				return ERR_INVALID_DATA
	for library in player.get_animation_library_list():player.remove_animation_library(library)
	var library := AnimationLibrary.new()
	var code := library.add_animation("Native", animation)
	if code != OK:return code
	return player.add_animation_library("", library)
