extends RefCounted

# Original LINEAR bone TRS, without GLTFDocument's fixed-rate track bake.
static func install(player: AnimationPlayer, skeleton: Skeleton3D, payload: Dictionary, output_path: String) -> Error:
	if payload.schema_version != 1 or payload.loop or payload.channels.is_empty():
		return ERR_INVALID_DATA
	var animation := Animation.new()
	animation.length = float(payload.duration_s)
	animation.loop_mode = Animation.LOOP_NONE
	animation.resource_name = str(payload.name)
	var skeleton_path := str(player.get_node(player.root_node).get_path_to(skeleton))
	for channel in payload.channels:
		if channel.interpolation != "LINEAR" or skeleton.find_bone(channel.bone) < 0:
			return ERR_INVALID_DATA
		var types := {"translation": Animation.TYPE_POSITION_3D, "rotation": Animation.TYPE_ROTATION_3D, "scale": Animation.TYPE_SCALE_3D}
		if not types.has(channel.path) or channel.times_s.size() != channel.values.size():
			return ERR_INVALID_DATA
		var track := animation.add_track(types[channel.path])
		animation.track_set_path(track, NodePath(skeleton_path + ":" + str(channel.bone)))
		animation.track_set_interpolation_type(track, Animation.INTERPOLATION_LINEAR)
		animation.track_set_interpolation_loop_wrap(track, false)
		for index in range(channel.times_s.size()):
			var time: float = float(channel.times_s[index])
			var value: Array = channel.values[index]
			if channel.path == "rotation":
				animation.rotation_track_insert_key(track, time, Quaternion(value[0], value[1], value[2], value[3]).normalized())
			elif channel.path == "translation":
				animation.position_track_insert_key(track, time, Vector3(value[0], value[1], value[2]))
			else:
				animation.scale_track_insert_key(track, time, Vector3(value[0], value[1], value[2]))
	# Audit the reloaded binary Animation resource, including its native keys.
	var code := ResourceSaver.save(animation, output_path)
	if code != OK:
		return code
	var decoded := ResourceLoader.load(output_path, "Animation", ResourceLoader.CACHE_MODE_IGNORE) as Animation
	if decoded == null:
		return ERR_FILE_CORRUPT
	if decoded.get_track_count() != payload.channels.size() or decoded.length != float(payload.duration_s):
		push_error("Native resource header mismatch: " + str(decoded.get_track_count()) + ", " + str(decoded.length) + " vs " + str(payload.duration_s))
		return ERR_FILE_CORRUPT
	for track in range(decoded.get_track_count()):
		var keys: Array = payload.channels[track].times_s
		if decoded.track_get_key_count(track) != keys.size():
			push_error("Native key count mismatch on track " + str(track))
			return ERR_FILE_CORRUPT
		for key in range(keys.size()):
			# Source glTF times are float32; JSON parsing can add double ULPs.
			var source_time := float(PackedFloat32Array([keys[key]])[0])
			if decoded.track_get_key_time(track, key) != source_time:
				push_error("Native time mismatch on track " + str(track) + " key " + str(key) + ": " + str(decoded.track_get_key_time(track, key)) + " vs " + str(source_time))
				return ERR_FILE_CORRUPT
	for library in player.get_animation_library_list():
		player.remove_animation_library(library)
	var library := AnimationLibrary.new()
	code = library.add_animation("Native", decoded)
	if code != OK:
		return code
	return player.add_animation_library("", library)
