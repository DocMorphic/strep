extends RefCounted
## One absolute finite clock. Callbacks observe ALL participants at marker time.
signal gameplay(event: Dictionary)
const Roots = preload("godot_native_root_adapter.gd")
const Props = preload("godot_native_object_player.gd")
const Events = preload("godot_scene_game_events.gd")
var actors: Dictionary = {}
var props
var events
var times := PackedFloat64Array()
var playback_time_s: Variant = null
var pose_time_s := 0.0
var root_deltas: Dictionary = {}
var playback_roots: Dictionary = {}
var bound := false
var advancing := false

func bind(entries: Array, object_player: AnimationPlayer, object_clip: StringName, objects: Dictionary, document: Dictionary) -> Error:
	if bound or entries.is_empty() or entries.size() > 8: return ERR_INVALID_PARAMETER
	var planned := Events.new()
	if not planned.configure(document) or not Props.eligible(object_player, object_clip, objects): return ERR_INVALID_DATA
	var duration: float = planned.times[-1]
	if object_player.get_animation(object_clip).length != duration: return ERR_INVALID_DATA
	var seen := {}
	for item in entries:
		if not item is Dictionary or not item.get("id") is String or item.id == "" or seen.has(item.id) or typeof(item.get("extract")) != TYPE_BOOL: return ERR_INVALID_DATA
		if not item.get("player") is AnimationPlayer or not item.get("skeleton") is Skeleton3D or not item.get("actor") is Node3D: return ERR_INVALID_DATA
		if not Roots.eligible(item.get("player"), item.get("skeleton"), item.get("actor"), item.get("clip", ""), item.get("root_bone", "")) or item.player.get_animation(item.clip).length != duration: return ERR_INVALID_DATA
		if item.player == object_player or item.actor.is_ancestor_of(object_player): return ERR_INVALID_DATA
		for earlier in seen.values():
			if item.actor == earlier.actor or item.player == earlier.player or item.skeleton == earlier.skeleton or item.actor.is_ancestor_of(earlier.actor) or earlier.actor.is_ancestor_of(item.actor): return ERR_INVALID_DATA
		seen[item.id] = item
	for event in planned.events:
		if not seen.has(event.actor): return ERR_INVALID_DATA
	# Whole-scene preflight finishes before any pose/player mutation.
	for item in entries:
		var helper := Roots.new()
		if helper.bind(item.player, item.skeleton, item.actor, item.clip, item.root_bone, item.extract) != OK: return ERR_INVALID_DATA
		actors[item.id] = helper
	props = Props.new()
	if props.bind(object_player, object_clip, objects) != OK: return ERR_INVALID_DATA
	events = planned; times = planned.times; bound = true
	for name in actors:
		playback_roots[name] = actors[name].root_motion_transform; root_deltas[name] = Transform3D.IDENTITY
	return OK

func can_sample(seconds: float) -> bool:
	if not bound or advancing or not is_finite(seconds) or seconds < 0.0 or seconds > times[-1] or not props.can_sample(seconds): return false
	for helper in actors.values():
		if not is_instance_valid(helper.player) or not is_instance_valid(helper.actor) or not is_instance_valid(helper.skeleton) or not helper._valid(seconds): return false
	return true

func _sample(seconds: float) -> void:
	for helper in actors.values(): helper.seek_preview(seconds)
	props.seek_preview(seconds); pose_time_s = seconds

func advance_to(seconds: float) -> Dictionary:
	if not can_sample(seconds) or (playback_time_s != null and seconds < playback_time_s): return {"valid": false, "events": []}
	advancing = true
	var before := playback_roots.duplicate(); var steps: Array = []
	for event in events.events:
		if event.runtime_dispatch_allowed and (playback_time_s == null or event.time_s > playback_time_s) and event.time_s <= seconds:
			if steps.is_empty() or steps[-1] != event.time_s: steps.append(event.time_s)
	if steps.is_empty() or steps[-1] != seconds: steps.append(seconds)
	var dispatched: Array = []
	for time in steps:
		_sample(time); playback_time_s = time
		for name in actors: root_deltas[name] = before[name].affine_inverse() * actors[name].root_motion_transform
		var crossed: Dictionary = events.advance(time)
		for event in crossed.events:
			dispatched.append(event.duplicate(true)); gameplay.emit(event.duplicate(true))
	for name in actors:
		# Repeated playback time has exactly zero root movement, even after preview.
		if before[name] == actors[name].root_motion_transform: root_deltas[name] = Transform3D.IDENTITY
		playback_roots[name] = actors[name].root_motion_transform
	advancing = false
	return {"valid": true, "events": dispatched}

func seek_preview(seconds: float) -> Error:
	# Preview changes visible poses, not the forward playback/event cursors.
	if not can_sample(seconds): return ERR_INVALID_PARAMETER
	_sample(seconds)
	return OK

func restart() -> Error:
	# Explicit new traversal, silent until the next advance; no inverse gameplay.
	if not can_sample(0.0): return ERR_INVALID_PARAMETER
	_sample(0.0); events.reset(); playback_time_s = null
	for name in actors:
		playback_roots[name] = actors[name].root_motion_transform; root_deltas[name] = Transform3D.IDENTITY
	return OK
