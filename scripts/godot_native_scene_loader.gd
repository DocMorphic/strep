extends RefCounted
const ScenePlayer = preload("godot_native_scene_player.gd")
const Roots = preload("godot_native_root_adapter.gd")

static func matrix(rows: Array) -> Transform3D:
	return Transform3D(Basis(Vector3(rows[0][0], rows[1][0], rows[2][0]), Vector3(rows[0][1], rows[1][1], rows[2][1]), Vector3(rows[0][2], rows[1][2], rows[2][2])), Vector3(rows[0][3], rows[1][3], rows[2][3]))

static func checked_path(folder: String, entry: Dictionary) -> String:
	var relative = entry.get("path")
	if not relative is String or relative.is_empty() or relative.begins_with("/") or relative.contains("\\") or relative.contains(":") or ".." in relative.split("/"): return ""
	var path := folder.path_join(relative)
	return path if entry.get("sha256") is String and FileAccess.get_sha256(path) == entry.sha256 else ""

static func import_model(path: String, index: int) -> Node3D:
	var document := GLTFDocument.new(); var state := GLTFState.new()
	if document.append_from_file(path, state) != OK: return null
	var animations := state.get_animations()
	if index < 0 or index >= animations.size(): return null
	var selected: Array[GLTFAnimation] = [animations[index]]; state.set_animations(selected)
	return document.generate_scene(state, 30.0, false, false)

static func install(model: Node3D, path: String) -> AnimationPlayer:
	var players: Array = []
	for node in Roots.nodes(model):
		if node is AnimationPlayer: players.append(node)
	if players.size() != 1: return null
	var saved := ResourceLoader.load(path, "Animation", ResourceLoader.CACHE_MODE_IGNORE) as Animation
	if saved == null: return null
	var player: AnimationPlayer = players[0]
	for name in player.get_animation_library_list(): player.remove_animation_library(name)
	var library := AnimationLibrary.new()
	if library.add_animation("Native", saved) != OK or player.add_animation_library("", library) != OK: return null
	return player

static func load_scene(parent: Node3D, folder: String, config: Dictionary) -> Dictionary:
	if config.get("schema") != "strep-native-scene-runtime-v1" or not config.get("actors") is Array or not config.has("objects"): return {}
	if config.actors.is_empty() or config.actors.size() > 8: return {}
	if config.objects != null and (not config.objects is Dictionary or not config.objects.get("names") is Array or config.objects.names.is_empty()): return {}
	var scene_path := checked_path(folder, config.get("scene", {}))
	if scene_path == "": return {}
	var intent = JSON.parse_string(FileAccess.get_file_as_string(scene_path))
	if not intent is Dictionary or intent.get("schema") != "strep-native-scene-contacts-v1" or not intent.get("actors") is Dictionary or not intent.get("objects") is Dictionary: return {}
	if intent.actors.size() != config.actors.size() or (config.objects == null and not intent.objects.is_empty()): return {}
	var ids := {}
	for item in config.actors:
		if not item is Dictionary or not item.get("id") is String or ids.has(item.id) or not intent.actors.has(item.id) or not item.get("root_bone") is String or typeof(item.get("extract")) != TYPE_BOOL: return {}
		var index_value = item.get("animation_index")
		if typeof(index_value) not in [TYPE_FLOAT, TYPE_INT] or not is_finite(index_value) or index_value < 0 or index_value != floor(index_value): return {}
		var rows = item.get("placement")
		if not rows is Array or rows.size() != 4: return {}
		for row in rows:
			if not row is Array or row.size() != 4: return {}
			for value in row:
				if typeof(value) not in [TYPE_FLOAT, TYPE_INT] or not is_finite(value): return {}
		if rows[3][0] != 0.0 or rows[3][1] != 0.0 or rows[3][2] != 0.0 or rows[3][3] != 1.0 or not Roots.rigid(matrix(rows)): return {}
		ids[item.id] = true
	var object_ids := {}
	if config.objects != null:
		if intent.objects.size() != config.objects.names.size(): return {}
		for name in config.objects.names:
			if not name is String or name.is_empty() or object_ids.has(name) or not intent.objects.has(name): return {}
			object_ids[name] = true
	var event_path := checked_path(folder, config.get("events", {}))
	if event_path == "": return {}
	var event_doc = JSON.parse_string(FileAccess.get_file_as_string(event_path))
	if not event_doc is Dictionary: return {}
	var container := Node3D.new(); container.name = "StrepScene"; parent.add_child(container)
	var entries: Array = []
	for item in config.actors:
		var path := checked_path(folder, item.get("asset", {})); var resource := checked_path(folder, item.get("resource", {}))
		if path == "" or resource == "": container.free(); return {}
		var model := import_model(path, int(item.animation_index))
		if model == null: container.free(); return {}
		var actor := Node3D.new(); actor.name = "Actor_" + str(item.id); container.add_child(actor); actor.add_child(model)
		actor.transform = matrix(item.placement)
		var player := install(model, resource); var skeletons: Array = []
		for node in Roots.nodes(model):
			if node is Skeleton3D: skeletons.append(node)
		if player == null or skeletons.size() != 1: container.free(); return {}
		entries.append({"id": item.id, "player": player, "skeleton": skeletons[0], "actor": actor, "clip": "Native", "root_bone": item.root_bone, "extract": item.extract})
	var object_player: AnimationPlayer = null; var objects := {}; var object_clip: StringName = &""
	if config.objects != null:
		var object_path := checked_path(folder, config.objects.get("asset", {})); var object_resource := checked_path(folder, config.objects.get("resource", {}))
		if object_path == "" or object_resource == "": container.free(); return {}
		var model := import_model(object_path, 0)
		if model == null: container.free(); return {}
		container.add_child(model)
		object_player = install(model, object_resource); object_clip = &"Native"
		for node in Roots.nodes(model):
			if node is MeshInstance3D:
				if str(node.name).trim_prefix("Object_") not in config.objects.names: container.free(); return {}
				for name in config.objects.names:
					if node.name == "Object_" + str(name):
						if objects.has(name): container.free(); return {}
					objects[name] = node
		if object_player == null or objects.size() != config.objects.names.size(): container.free(); return {}
	var helper := ScenePlayer.new()
	var code := helper.bind(entries, object_player, object_clip, objects, event_doc)
	if code != OK:
		push_error("Strep scene preflight/binding failed: " + str(code)); container.free(); return {}
	return {"container": container, "player": helper, "entries": entries, "objects": objects}
