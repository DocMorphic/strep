extends SceneTree
const NativeClock = preload("res://native_engine_clock.gd")
const NativeTracks = preload("res://native_godot_tracks.gd")
const NativePreview = preload("res://native_godot_preview.gd")

func matrix(value: Transform3D) -> Array:
	return [[value.basis.x.x, value.basis.x.y, value.basis.x.z],
		[value.basis.y.x, value.basis.y.y, value.basis.y.z],
		[value.basis.z.x, value.basis.z.y, value.basis.z.z],
		[value.origin.x, value.origin.y, value.origin.z]]

func descendants(node: Node) -> Array:
	var result: Array = [node]
	for child in node.get_children(): result.append_array(descendants(child))
	return result

func _initialize() -> void:
	call_deferred("audit")

func fail(message: String) -> void:
	push_error(message)
	quit(2)

func audit() -> void:
	var args := OS.get_cmdline_user_args()
	if args.size() != 2:
		fail("Speed request and output required")
		return
	var request = JSON.parse_string(FileAccess.get_file_as_string(args[0]))
	var times := NativeClock.decode(request.sample_clock, request.sample_times_s.size())
	if times.size() != request.sample_times_s.size():
		fail("Complete exact speed clock required")
		return
	var report := {"engine": Engine.get_version_info(), "cases": [],
		"playback_mode": request.playback_mode, "import_bake_fps": request.import_bake_fps}
	for item in request.cases:
		var document := GLTFDocument.new()
		var state := GLTFState.new()
		if document.append_from_file(item.path, state) != OK:
			fail("Speed actor import failed")
			return
		var animations := state.get_animations()
		var index := int(item.animation_index)
		if index < 0 or index >= animations.size():
			fail("Explicit source animation required")
			return
		var selected_animations: Array[GLTFAnimation] = [animations[index]]
		state.set_animations(selected_animations)
		var model := document.generate_scene(state, float(request.import_bake_fps), false, false)
		if model == null:
			fail("Imported speed scene unavailable")
			return
		root.add_child(model)
		await process_frame
		var players: Array = []
		var skeletons: Array = []
		for node in descendants(model):
			if node is AnimationPlayer: players.append(node)
			if node is Skeleton3D: skeletons.append(node)
		if players.size() != 1 or skeletons.size() != 1:
			fail("One imported player and skeleton required")
			return
		var player: AnimationPlayer = players[0]
		var skeleton: Skeleton3D = skeletons[0]
		if request.playback_mode == "native-authoring":
			if NativeTracks.install(player, skeleton, item.native_payload, item.animation_output) != OK:
				fail("Native speed resource failed")
				return
		var selected := ""
		for animation in player.get_animation_list():
			if animation != "RESET":
				if selected != "":
					fail("Exactly one selected animation required")
					return
				selected = animation
		if selected == "":
			fail("Selected speed animation missing")
			return
		var nodes := state.get_nodes()
		var targets: Array = []
		var mapping: Array = []
		for capture in item.capture_nodes:
			var id := int(capture.node)
			if id < 0 or id >= int(item.source_node_count) or id >= nodes.size():
				fail("Original capture node missing")
				return
			var imported: GLTFNode = nodes[id]
			var target: Node3D
			var path: NodePath
			var bone := -1
			if imported.skeleton >= 0:
				var gltf_skeletons := state.get_skeletons()
				if imported.skeleton >= gltf_skeletons.size():
					fail("Imported source skeleton missing")
					return
				# The importer's skeleton resource and generated bone name retain
				# source identity, including a glTF bone at the scene root.
				target = gltf_skeletons[imported.skeleton].get_godot_skeleton()
				if target == null or target != skeleton:
					fail("Imported source skeleton does not resolve")
					return
				bone = skeleton.find_bone(imported.get_name())
				if bone < 0 or id not in gltf_skeletons[imported.skeleton].joints:
					fail("Imported capture bone missing")
					return
				path = NodePath(str(model.get_path_to(target)) + ":" + str(skeleton.get_bone_name(bone)))
			else:
				path = imported.get_scene_node_path(state, true)
				target = model.get_node_or_null(NodePath(path.get_concatenated_names())) as Node3D
				if target == null or path.get_subname_count() != 0:
					fail("Imported helper path does not resolve to a transform")
					return
			targets.append({"node": target, "bone": bone})
			mapping.append({"node": id, "parent": capture.parent,
				"original_name": imported.original_name, "engine_parent": imported.parent, "scene_path": str(path)})
		player.callback_mode_process = AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_MANUAL
		player.play(selected)
		var frames: Array = []
		for time in times:
			if request.playback_mode == "native-authoring":
				if NativePreview.seek(player, skeleton, player.get_animation(selected), float(time)) != OK:
					fail("Native speed seek failed")
					return
			else: player.seek(float(time), true)
			var worlds: Array = []
			for target in targets:
				var node: Node3D = target.node
				var world: Transform3D = node.global_transform
				if target.bone >= 0: world = world * (node as Skeleton3D).get_bone_global_pose(target.bone)
				worlds.append(matrix(world))
			frames.append({"requested_time_s": time, "actual_time_s": player.current_animation_position, "node_worlds": worlds})
		report.cases.append({"id": item.id, "path": item.path, "animation_index": index,
			"original_animation_count": animations.size(), "capture_nodes": mapping,
			"selected_animation": selected, "duration_s": player.get_animation(selected).length,
			"loop_mode": player.get_animation(selected).loop_mode, "frames": frames})
		model.queue_free()
		await process_frame
	var output := FileAccess.open(args[1], FileAccess.WRITE)
	output.store_string(JSON.stringify(report, "", true, true))
	output.close()
	quit(0)
