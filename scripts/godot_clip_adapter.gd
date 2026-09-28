extends Node
## Runtime adapter for Strep's authored markers. Bind once to a freshly imported
## clip. Signals report authored intent, not physical grasp/contact success.
signal marker(event: Dictionary)
var bound := false

func emit_marker(event: Dictionary) -> void:
	marker.emit(event.duplicate(true))

func seek_preview(player: AnimationPlayer, seconds: float) -> void:
	# update_only suppresses method/audio/playback tracks even at a marker key.
	player.seek(seconds, true, true)

func hold_terminal_frame(player: AnimationPlayer, animation_name: StringName, fps: float) -> Error:
	# An N-sample clip occupies N/fps seconds. Holding its terminal sample for
	# one interval also keeps the last moving interval before end processing.
	if not player.has_animation(animation_name) or not is_finite(fps) or fps <= 0:
		return ERR_INVALID_PARAMETER
	var animation := player.get_animation(animation_name)
	if animation.loop_mode != Animation.LOOP_NONE:
		return ERR_UNAVAILABLE
	var last_key := 0.0
	for track in range(animation.get_track_count()):
		var count := animation.track_get_key_count(track)
		if count > 0:
			last_key = maxf(last_key, animation.track_get_key_time(track, count - 1))
	animation.length = maxf(animation.length, last_key + 1.0 / fps)
	return OK

func bind_clip(player: AnimationPlayer, animation_name: StringName, document: Dictionary) -> Error:
	if bound or not player.has_animation(animation_name):
		return ERR_INVALID_PARAMETER
	var animation := player.get_animation(animation_name)
	var fps := float(document.get("fps", 0))
	if fps <= 0 or not is_finite(fps) or not document.get("events") is Array:
		return ERR_INVALID_DATA
	var previous_frame := -1
	for event in document.events:
		if not event is Dictionary:
			return ERR_INVALID_DATA
		if not event.get("type") is String or not event.get("actor") is String:
			return ERR_INVALID_DATA
		var frame := float(event.get("frame", -1))
		var time := float(event.get("time_s", -1))
		if not is_finite(frame) or not is_finite(time) or frame != floor(frame) or frame < 0 or frame < previous_frame:
			return ERR_INVALID_DATA
		if abs(time - frame / fps) > 0.000001 or time > animation.length + 0.000001:
			return ERR_INVALID_DATA
		previous_frame = int(frame)
	# Fixed receiver/method: JSON supplies data, never a method or node path.
	var track := animation.add_track(Animation.TYPE_METHOD)
	var base := player.get_node(player.root_node)
	animation.track_set_path(track, base.get_path_to(self))
	for event in document.events:
		animation.track_insert_key(track, float(event.time_s), {"method": &"emit_marker", "args": [event.duplicate(true)]})
	bound = true
	player.clear_caches()
	return OK

func extract_root(player: AnimationPlayer, animation_name: StringName, bone_name: StringName) -> Error:
	if not player.has_animation(animation_name):
		return ERR_INVALID_PARAMETER
	var animation := player.get_animation(animation_name)
	var paths: Array[NodePath] = []
	for track in range(animation.get_track_count()):
		var path := animation.track_get_path(track)
		if animation.track_get_type(track) == Animation.TYPE_POSITION_3D and path.get_subname_count() == 1 and path.get_subname(0) == bone_name:
			paths.append(path)
	if paths.size() != 1:
		return ERR_INVALID_DATA
	player.root_motion_track = paths[0]
	player.root_motion_local = false
	return OK
