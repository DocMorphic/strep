extends SceneTree

func vector(value: Vector3) -> Array:
	return [value.x, value.y, value.z]

func matrix(value: Transform3D) -> Array:
	return [vector(value.basis.x), vector(value.basis.y), vector(value.basis.z), vector(value.origin)]

func descendants(node: Node) -> Array:
	var result: Array = [node]
	for child in node.get_children():
		result.append_array(descendants(child))
	return result

func _initialize() -> void:
	call_deferred("audit")

func audit() -> void:
	var args := OS.get_cmdline_user_args()
	if args.size() != 2:
		quit(2)
		return
	var request = JSON.parse_string(FileAccess.get_file_as_string(args[0]))
	var report: Dictionary = {"engine": Engine.get_version_info(), "cases": []}
	for item in request.cases:
		var document := GLTFDocument.new()
		var state := GLTFState.new()
		var code := document.append_from_file(item.path, state)
		if code != OK:
			push_error("Contact import failed: " + str(code))
			quit(3)
			return
		var model := document.generate_scene(state, 30.0, false, false)
		root.add_child(model)
		await process_frame
		var player: AnimationPlayer
		var skeletons: Array = []
		var mesh_nodes: Array = []
		for node in descendants(model):
			if node is AnimationPlayer:
				player = node
			if node is Skeleton3D:
				skeletons.append(node)
			if node is MeshInstance3D and node.skin != null:
				mesh_nodes.append(node)
		if player == null or skeletons.size() != 1 or mesh_nodes.is_empty():
			push_error("One imported skeleton, player and skinned geometry required")
			quit(4)
			return
		var skeleton: Skeleton3D = skeletons[0]
		var names: Array = []
		for bone in range(skeleton.get_bone_count()):
			names.append(str(skeleton.get_bone_name(bone)))
		var meshes: Array = []
		for node in mesh_nodes:
			if node.get_node(node.skeleton) != skeleton or node.get_blend_shape_count() != 0:
				push_error("Other skeleton or blend shapes require a separate contact audit")
				quit(5)
				return
			var binds: Array = []
			for bind in range(node.skin.get_bind_count()):
				var name := str(node.skin.get_bind_name(bind))
				var bone: int = skeleton.find_bone(name) if name != "" else node.skin.get_bind_bone(bind)
				if bone < 0 or bone >= names.size():
					quit(6)
					return
				binds.append({"bone": bone, "pose": matrix(node.skin.get_bind_pose(bind))})
			for surface in range(node.mesh.get_surface_count()):
				var arrays: Array = node.mesh.surface_get_arrays(surface)
				var positions: Array = []
				for point in arrays[Mesh.ARRAY_VERTEX]:
					positions.append(vector(point))
				meshes.append({"node": str(node.get_path()), "surface": surface, "binds": binds,
					"positions": positions, "weights": Array(arrays[Mesh.ARRAY_WEIGHTS]),
					"bones": Array(arrays[Mesh.ARRAY_BONES])})
		var selected := ""
		for animation in player.get_animation_list():
			if animation != "RESET":
				if selected != "":
					quit(7)
					return
				selected = animation
		if selected == "":
			quit(8)
			return
		player.callback_mode_process = AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_MANUAL
		player.play(selected)
		var frames: Array = []
		for time in item.sample_times_s:
			player.seek(float(time), true)
			var bones: Array = []
			for bone in range(skeleton.get_bone_count()):
				bones.append(matrix(skeleton.global_transform * skeleton.get_bone_global_pose(bone)))
			var mesh_world: Array = []
			for node in mesh_nodes:
				mesh_world.append({"node": str(node.get_path()), "matrix": matrix(node.global_transform)})
			frames.append({"requested_time_s": time, "actual_time_s": player.current_animation_position,
				"bones": bones, "skeleton_world": matrix(skeleton.global_transform), "mesh_world": mesh_world})
		report.cases.append({"id": item.id, "path": item.path, "bone_names": names, "meshes": meshes,
			"duration_s": player.get_animation(selected).length, "loop_mode": player.get_animation(selected).loop_mode, "frames": frames})
		model.queue_free()
		await process_frame
	var output := FileAccess.open(args[1], FileAccess.WRITE)
	output.store_string(JSON.stringify(report, "", true, true))
	output.close()
	quit(0)
