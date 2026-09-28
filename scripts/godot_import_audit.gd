extends SceneTree

func vec(v: Vector3) -> Array:
	return [v.x, v.y, v.z]

func matrix(t: Transform3D) -> Array:
	return [vec(t.basis.x), vec(t.basis.y), vec(t.basis.z), vec(t.origin)]

func descendants(node: Node) -> Array:
	var found: Array = [node]
	for child in node.get_children():
		found.append_array(descendants(child))
	return found

func _initialize() -> void:
	call_deferred("run_audit")

func run_audit() -> void:
	var args := OS.get_cmdline_user_args()
	if args.size() != 2:
		push_error("Expected input and output JSON paths")
		quit(2)
		return
	var request = JSON.parse_string(FileAccess.get_file_as_string(args[0]))
	var report: Dictionary = {"engine": Engine.get_version_info(), "cases": [], "scope": "Godot runtime glTF import and AnimationPlayer seek on every source frame; headless, not a GPU-render or real-time physics test."}
	for item in request.cases:
		var document := GLTFDocument.new()
		var state := GLTFState.new()
		var code := document.append_from_file(item.path, state)
		if code != OK:
			push_error("glTF import failed: " + str(code))
			quit(3)
			return
		var model := document.generate_scene(state, 30.0, false, false)
		root.add_child(model)
		await process_frame
		var player: AnimationPlayer
		var skeleton: Skeleton3D
		var box: Node3D
		var meshes: Array = []
		var nodes: Array = []
		for node in descendants(model):
			nodes.append({"name": str(node.name), "class": node.get_class()})
			if node is AnimationPlayer:
				player = node
			if node is Skeleton3D:
				skeleton = node
			if str(node.name) == "Interaction_box":
				box = node
			if node is MeshInstance3D:
				for surface in range(node.mesh.get_surface_count()):
					var arrays: Array = node.mesh.surface_get_arrays(surface)
					var positions: Array = []
					for point in arrays[Mesh.ARRAY_VERTEX]:
						positions.append(vec(point))
					meshes.append({"name": str(node.name), "surface": surface, "format": node.mesh.surface_get_format(surface), "positions": positions,
						"weights": Array(arrays[Mesh.ARRAY_WEIGHTS]) if arrays[Mesh.ARRAY_WEIGHTS] != null else [],
						"bones": Array(arrays[Mesh.ARRAY_BONES]) if arrays[Mesh.ARRAY_BONES] != null else []})
		if player == null or skeleton == null:
			push_error("Missing AnimationPlayer or Skeleton3D: " + JSON.stringify(nodes))
			quit(4)
			return
		var animations: PackedStringArray = player.get_animation_list()
		var selected := ""
		for animation in animations:
			if animation != "RESET":
				selected = animation
				break
		if selected == "":
			push_error("No motion animation")
			quit(5)
			return
		player.callback_mode_process = AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_MANUAL
		player.play(selected)
		var names: Array = []
		for bone in range(skeleton.get_bone_count()):
			names.append(skeleton.get_bone_name(bone))
		var frames: Array = []
		for frame in range(item.frames):
			var sample_time: float = float(item.sample_times_s[frame]) if item.has("sample_times_s") else float(frame) / 30.0
			player.seek(sample_time, true)
			var transforms: Array = []
			for bone in range(skeleton.get_bone_count()):
				transforms.append(matrix(skeleton.global_transform * skeleton.get_bone_global_pose(bone)))
			frames.append({"bones": transforms, "object": matrix(box.global_transform) if box != null else null})
		report.cases.append({"id": item.id, "path": item.path, "import_error": code, "nodes": nodes, "animations": Array(animations), "animation": selected,
			"duration_s": player.get_animation(selected).length, "imported_loop_mode": player.get_animation(selected).loop_mode, "bone_names": names, "meshes": meshes, "frames": frames})
		model.queue_free()
		await process_frame
	var output := FileAccess.open(args[1], FileAccess.WRITE)
	output.store_string(JSON.stringify(report))
	output.close()
	print("Audited ", report.cases.size(), " imported scenes")
	quit(0)
