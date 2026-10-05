extends RefCounted
const Loader = preload("godot_native_scene_loader.gd")
const Roots = preload("godot_native_root_adapter.gd")
const Player = preload("godot_baked_scene_player.gd")
const Clock = preload("native_engine_clock.gd")
static var last_error := ""

static func load_scene(parent: Node3D, folder: String, config: Dictionary) -> Dictionary:
	last_error="runtime header"
	if config.get("schema")!="strep-baked-scene-runtime-v1" or not config.get("actors") is Array or config.actors.is_empty() or config.actors.size()>8 or not config.get("objects") is Dictionary: return {}
	if config.get("root_mode")!="original-embedded" or config.get("actor_end_policy")!="hold-original-end": return {}
	for key in ["live_prop_physics","quality_approved","release_approved"]:
		if typeof(config.get(key))!=TYPE_BOOL or config[key]: return {}
	var source = config.get("source_duration_s"); var duration = config.get("duration_s")
	if typeof(source) not in [TYPE_INT,TYPE_FLOAT] or typeof(duration) not in [TYPE_INT,TYPE_FLOAT] or not is_finite(source) or not is_finite(duration) or source<=0.0 or duration<source: return {}
	var fps = config.get("physics_fps")
	if typeof(fps) not in [TYPE_INT,TYPE_FLOAT] or not is_finite(fps) or fps!=int(fps) or int(fps) not in [60,120,240]: return {}
	var clock := Clock.decode(config.get("clock",{}),int(config.get("clock",{}).get("count",0)))
	if clock.is_empty() or clock.size()>14401 or clock[-1]!=duration or duration-source>=1.0/fps: return {}
	for i in range(clock.size()):
		if clock[i]!=float(i)/fps: return {}
	last_error="parent transform"
	var rows = config.get("parent_world_transform")
	if not rows is Array or rows.size()!=4: return {}
	for row in rows:
		if not row is Array or row.size()!=4: return {}
		for value in row:
			if typeof(value) not in [TYPE_INT,TYPE_FLOAT] or not is_finite(value): return {}
	if rows[3][0]!=0.0 or rows[3][1]!=0.0 or rows[3][2]!=0.0 or rows[3][3]!=1.0 or not Roots.rigid(Loader.matrix(rows)): return {}
	last_error="source/event references"
	var source_path := Loader.checked_path(folder,config.get("source_scene",{})); var event_path := Loader.checked_path(folder,config.get("events",{}))
	if source_path=="" or event_path=="": return {}
	var intent = JSON.parse_string(FileAccess.get_file_as_string(source_path)); var events = JSON.parse_string(FileAccess.get_file_as_string(event_path))
	if not intent is Dictionary or intent.get("schema")!="strep-native-scene-contacts-v1" or not events is Dictionary or not intent.get("actors") is Dictionary or not intent.get("objects") is Dictionary or intent.actors.size()!=config.actors.size(): return {}
	last_error="participant configuration"
	var ids := {}; var object_ids := {}
	if not config.objects.get("names") is Array or config.objects.names.is_empty() or config.objects.names.size()!=intent.objects.size(): return {}
	for name in config.objects.names:
		if not name is String or object_ids.has(name) or not intent.objects.has(name): return {}
		object_ids[name]=true
	for item in config.actors:
		if not item is Dictionary or not item.get("id") is String or ids.has(item.id) or not intent.actors.has(item.id) or not item.get("root_bone") is String or typeof(item.get("extract"))!=TYPE_BOOL or item.extract: return {}
		ids[item.id]=true
		var index = item.get("animation_index"); var placement = item.get("placement")
		if typeof(index) not in [TYPE_INT,TYPE_FLOAT] or not is_finite(index) or index<0 or index!=floor(index) or not placement is Array or placement.size()!=4: return {}
		for row in placement:
			if not row is Array or row.size()!=4: return {}
			for value in row:
				if typeof(value) not in [TYPE_INT,TYPE_FLOAT] or not is_finite(value): return {}
		if placement[3][0]!=0.0 or placement[3][1]!=0.0 or placement[3][2]!=0.0 or placement[3][3]!=1.0 or not Roots.rigid(Loader.matrix(placement)): return {}
	last_error="actor import/resource"
	var container := Node3D.new(); container.name="StrepBakedScene"; parent.add_child(container); container.global_transform=Loader.matrix(rows)
	var entries: Array = []
	for item in config.actors:
		var path := Loader.checked_path(folder,item.get("asset",{})); var resource := Loader.checked_path(folder,item.get("resource",{}))
		if path=="" or resource=="": container.free(); return {}
		var model := Loader.import_model(path,int(item.animation_index))
		if model==null: container.free(); return {}
		var actor := Node3D.new(); actor.name="Actor_"+item.id; container.add_child(actor); actor.add_child(model); actor.transform=Loader.matrix(item.placement)
		var p := Loader.install(model,resource); var skeletons: Array = []
		for node in Roots.nodes(model):
			if node is Skeleton3D: skeletons.append(node)
		if p==null or skeletons.size()!=1 or p.get_animation("Native").length!=source: container.free(); return {}
		entries.append({"id":item.id,"player":p,"skeleton":skeletons[0],"actor":actor,"root_bone":item.root_bone,"extract":false})
	last_error="prop import/resource"
	var path := Loader.checked_path(folder,config.objects.get("asset",{})); var resource := Loader.checked_path(folder,config.objects.get("resource",{}))
	if path=="" or resource=="": container.free(); return {}
	var model := Loader.import_model(path,0)
	if model==null: container.free(); return {}
	container.add_child(model); var p := Loader.install(model,resource); var objects := {}
	if p==null or p.get_animation("Native").length!=duration: container.free(); return {}
	var animation := p.get_animation("Native").duplicate(true) as Animation
	var envelope: float = max(float(duration),float(PackedFloat32Array([duration])[0]))
	for track in range(animation.get_track_count()):
		for key in range(animation.track_get_key_count(track)):
			if animation.track_get_key_time(track,key)>envelope: container.free(); return {}
	animation.length=envelope # Resource bytes/keys remain untouched; public time stays finite.
	p.get_animation_library("").remove_animation("Native"); p.get_animation_library("").add_animation("Native",animation)
	for node in Roots.nodes(model):
		if node is MeshInstance3D:
			var id := str(node.name).trim_prefix("Object_")
			if not object_ids.has(id) or objects.has(id): container.free(); return {}
			objects[id]=node
	if objects.size()!=object_ids.size(): container.free(); return {}
	for node in Roots.nodes(container):
		if node is CollisionObject3D: container.free(); return {}
	var motion := Player.new()
	if motion.bind(container,entries,p,objects,events,float(duration))!=OK: last_error="player: "+motion.last_error; container.free(); return {}
	last_error=""
	return {"container":container,"player":motion,"entries":entries,"objects":objects}
