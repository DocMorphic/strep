extends RefCounted
## One finite baked clock. Source actors/events clamp at the original end.
signal gameplay(event: Dictionary)
const Roots = preload("godot_native_root_adapter.gd")
const Props = preload("godot_native_object_player.gd")
const Events = preload("godot_scene_game_events.gd")
var actors := {}
var props
var events
var source_duration_s := 0.0
var duration_s := 0.0
var pose_time_s := 0.0
var playback_time_s: Variant = null
var root_deltas := {}
var playback_roots := {}
var bound := false
var advancing := false
var container: Node3D
var parent_world := Transform3D.IDENTITY
var last_error := ""

func bind(parent: Node3D, entries: Array, object_player: AnimationPlayer, objects: Dictionary, document: Dictionary, duration: float) -> Error:
	last_error="parent/participants"
	if bound or parent==null or not parent.is_inside_tree() or not Roots.rigid(parent.global_transform) or entries.is_empty() or entries.size()>8: return ERR_INVALID_PARAMETER
	last_error="source events"; var planned := Events.new()
	if not planned.configure(document) or not is_finite(duration) or duration<planned.times[-1]: return ERR_INVALID_DATA
	last_error="native prop eligibility"
	if not Props.eligible(object_player,&"Native",objects): return ERR_INVALID_DATA
	# Loader may extend only the in-memory Float32 key envelope, never the API clock.
	var stored_end: float = float(PackedFloat32Array([duration])[0])
	if object_player.get_animation("Native").length!=max(duration,stored_end): return ERR_INVALID_DATA
	last_error="actor eligibility"; var seen := {}
	for item in entries:
		if not item is Dictionary or not item.get("id") is String or item.id.is_empty() or seen.has(item.id) or typeof(item.get("extract"))!=TYPE_BOOL or item.extract: return ERR_INVALID_DATA
		if not Roots.eligible(item.get("player"),item.get("skeleton"),item.get("actor"),&"Native",item.get("root_bone", "")): return ERR_INVALID_DATA
		if item.player.get_animation("Native").length!=planned.times[-1] or item.player==object_player or not parent.is_ancestor_of(item.actor): return ERR_INVALID_DATA
		for earlier in seen.values():
			if item.actor==earlier.actor or item.player==earlier.player or item.skeleton==earlier.skeleton or item.actor.is_ancestor_of(earlier.actor) or earlier.actor.is_ancestor_of(item.actor): return ERR_INVALID_DATA
		seen[item.id]=item
	last_error="event actor binding"
	for event in planned.events:
		if not seen.has(event.actor): return ERR_INVALID_DATA
	last_error="actor bind"
	for item in entries:
		var helper := Roots.new()
		if helper.bind(item.player,item.skeleton,item.actor,&"Native",item.root_bone,false)!=OK: return ERR_INVALID_DATA
		actors[item.id]=helper
	last_error="prop bind"; props=Props.new()
	if props.bind(object_player,&"Native",objects)!=OK: return ERR_INVALID_DATA
	events=planned; source_duration_s=planned.times[-1]; duration_s=duration
	container=parent; parent_world=parent.global_transform; bound=true
	for name in actors: playback_roots[name]=actors[name].root_motion_transform; root_deltas[name]=Transform3D.IDENTITY
	last_error=""; return OK

func can_sample(seconds: float) -> bool:
	if not bound or advancing or not is_instance_valid(container) or container.global_transform!=parent_world or not is_finite(seconds) or seconds<0.0 or seconds>duration_s or not props.can_sample(seconds): return false
	for helper in actors.values():
		if not is_instance_valid(helper.player) or not is_instance_valid(helper.actor) or not is_instance_valid(helper.skeleton) or not helper._valid(min(seconds,source_duration_s)): return false
	return true

func _sample(seconds: float) -> void:
	for helper in actors.values(): helper.seek_preview(min(seconds,source_duration_s))
	props.seek_preview(seconds); pose_time_s=seconds

func advance_to(seconds: float) -> Dictionary:
	if not can_sample(seconds) or (playback_time_s!=null and seconds<playback_time_s): return {"valid":false,"events":[]}
	advancing=true; var before := playback_roots.duplicate(); var steps: Array = []
	for event in events.events:
		if event.runtime_dispatch_allowed and (playback_time_s==null or event.time_s>playback_time_s) and event.time_s<=seconds:
			if steps.is_empty() or steps[-1]!=event.time_s: steps.append(event.time_s)
	if steps.is_empty() or steps[-1]!=seconds: steps.append(seconds)
	var dispatched: Array = []
	for time in steps:
		_sample(time); playback_time_s=time
		for name in actors: root_deltas[name]=before[name].affine_inverse()*actors[name].root_motion_transform
		for event in events.advance(min(time,source_duration_s)).events:
			dispatched.append(event.duplicate(true)); gameplay.emit(event.duplicate(true))
	for name in actors:
		if before[name]==actors[name].root_motion_transform: root_deltas[name]=Transform3D.IDENTITY
		playback_roots[name]=actors[name].root_motion_transform
	advancing=false; return {"valid":true,"events":dispatched}

func seek_preview(seconds: float) -> Error:
	if not can_sample(seconds): return ERR_INVALID_PARAMETER
	_sample(seconds); return OK

func restart() -> Error:
	if not can_sample(0.0): return ERR_INVALID_PARAMETER
	_sample(0.0); events.reset(); playback_time_s=null
	for name in actors: playback_roots[name]=actors[name].root_motion_transform; root_deltas[name]=Transform3D.IDENTITY
	return OK
