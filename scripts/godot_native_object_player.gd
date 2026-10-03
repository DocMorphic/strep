extends RefCounted
## Saved native rigid object tracks, without import baking or playback-end snap.
var player: AnimationPlayer
var animation: Animation
var objects: Dictionary = {}
var targets: Array[Node3D] = []
var bound := false
var time_s := 0.0

static func eligible(p: AnimationPlayer, clip: StringName, nodes: Dictionary) -> bool:
	if p == null or not p.has_animation(clip) or nodes.is_empty() or not p.root_motion_track.is_empty(): return false
	var base := p.get_node_or_null(p.root_node)
	var source := p.get_animation(clip)
	if base == null or not is_finite(source.length) or source.length <= 0.0 or source.loop_mode != Animation.LOOP_NONE: return false
	var seen := {}; var covered := {}
	for name in nodes:
		if not name is String or not nodes[name] is Node3D or not is_instance_valid(nodes[name]) or (nodes[name] != base and not base.is_ancestor_of(nodes[name])): return false
	for track in range(source.get_track_count()):
		var path := source.track_get_path(track); var kind := source.track_get_type(track)
		var target := base.get_node_or_null(path)
		if path.get_subname_count() != 0 or target not in nodes.values() or kind not in [Animation.TYPE_POSITION_3D, Animation.TYPE_ROTATION_3D, Animation.TYPE_SCALE_3D]: return false
		if not source.track_is_enabled(track) or source.track_get_interpolation_type(track) != Animation.INTERPOLATION_LINEAR or source.track_get_key_count(track) == 0: return false
		var key := str(path) + ":" + str(kind)
		if seen.has(key): return false
		seen[key] = true; covered[target] = true
		var previous := -1.0
		for index in range(source.track_get_key_count(track)):
			var time := source.track_get_key_time(track, index); var value = source.track_get_key_value(track, index)
			if not is_finite(time) or time < 0.0 or time > source.length or time <= previous: return false
			previous = time
			if kind == Animation.TYPE_ROTATION_3D:
				if not value is Quaternion or not value.is_finite() or abs(value.length_squared() - 1.0) > 0.00001: return false
			else:
				if not value is Vector3 or not value.is_finite() or (kind == Animation.TYPE_SCALE_3D and value != Vector3.ONE): return false
	return covered.size() == nodes.size()

func bind(p: AnimationPlayer, clip: StringName, nodes: Dictionary) -> Error:
	if bound or not eligible(p, clip, nodes): return ERR_INVALID_PARAMETER
	player = p; animation = p.get_animation(clip).duplicate(true) as Animation; objects = nodes.duplicate()
	var base := player.get_node(player.root_node)
	for track in range(animation.get_track_count()): targets.append(base.get_node(animation.track_get_path(track)))
	player.callback_mode_process = AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_MANUAL
	player.play(clip); bound = true
	return seek_preview(0.0)

func can_sample(seconds: float) -> bool:
	if not bound or not is_instance_valid(player) or not is_finite(seconds) or seconds < 0.0 or seconds > animation.length: return false
	for target in targets:
		if not is_instance_valid(target) or not target.is_inside_tree(): return false
	return true

func seek_preview(seconds: float) -> Error:
	if not can_sample(seconds): return ERR_INVALID_PARAMETER
	player.seek(seconds, false)
	for track in range(animation.get_track_count()):
		match animation.track_get_type(track):
			Animation.TYPE_POSITION_3D: targets[track].position = animation.position_track_interpolate(track, seconds)
			Animation.TYPE_ROTATION_3D: targets[track].quaternion = animation.rotation_track_interpolate(track, seconds)
			Animation.TYPE_SCALE_3D: targets[track].scale = animation.scale_track_interpolate(track, seconds)
	time_s = seconds
	return OK
