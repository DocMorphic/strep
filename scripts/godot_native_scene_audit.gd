extends SceneTree
const NativeTracks = preload("res://native_godot_tracks.gd")
const NativePreview = preload("res://native_godot_preview.gd")
const NativeClock = preload("res://native_engine_clock.gd")

func vector(value: Vector3) -> Array:
	return [value.x, value.y, value.z]

func matrix(value: Transform3D) -> Array:
	return [vector(value.basis.x), vector(value.basis.y), vector(value.basis.z), vector(value.origin)]

func descendants(node: Node) -> Array:
	var result: Array = [node]
	for child in node.get_children(): result.append_array(descendants(child))
	return result

func rigid_pose(key: Dictionary) -> Transform3D:
	var p: Array = key.translation_m
	var q: Array = key.rotation_xyzw
	return Transform3D(Basis(Quaternion(q[0], q[1], q[2], q[3]).normalized()), Vector3(p[0], p[1], p[2]))

func sample_object(keys: Array, time: float) -> Transform3D:
	if keys.size() == 1: return rigid_pose(keys[0])
	var right := 1
	while right < keys.size() - 1 and float(keys[right].time_s) < time: right += 1
	var left_pose := rigid_pose(keys[right - 1])
	var right_pose := rigid_pose(keys[right])
	var weight := (time - float(keys[right - 1].time_s)) / (float(keys[right].time_s) - float(keys[right - 1].time_s))
	var q := left_pose.basis.get_rotation_quaternion().slerp(right_pose.basis.get_rotation_quaternion(), weight)
	return Transform3D(Basis(q), left_pose.origin.lerp(right_pose.origin, weight))

func _initialize() -> void:
	call_deferred("audit")

func audit() -> void:
	var args := OS.get_cmdline_user_args()
	if args.size() != 2:
		quit(2)
		return
	var request = JSON.parse_string(FileAccess.get_file_as_string(args[0]))
	var times := NativeClock.decode(request.sample_clock, request.sample_times_s.size())
	if times.size() != request.sample_times_s.size():
		quit(15)
		return
	var report: Dictionary = {"engine": Engine.get_version_info(), "cases": [], "objects": []}
	for item in request.cases:
		var document := GLTFDocument.new()
		var state := GLTFState.new()
		var code := document.append_from_file(item.path, state)
		if code != OK:
			push_error("Scene actor import failed: " + str(code))
			quit(3)
			return
		var animations := state.get_animations()
		var index := int(item.animation_index)
		if index < 0 or index >= animations.size():
			quit(4)
			return
		var original_name := animations[index].original_name
		var selected_animations: Array[GLTFAnimation] = [animations[index]]
		state.set_animations(selected_animations)
		var model := document.generate_scene(state, 30.0, false, false)
		root.add_child(model)
		await process_frame
		var players: Array = []
		var skeletons: Array = []
		var mesh_nodes: Array = []
		for node in descendants(model):
			if node is AnimationPlayer: players.append(node)
			if node is Skeleton3D: skeletons.append(node)
			if node is MeshInstance3D and node.skin != null: mesh_nodes.append(node)
		if players.size() != 1 or skeletons.size() != 1 or mesh_nodes.is_empty():
			push_error("One skeleton/player and complete skinned geometry required")
			quit(5)
			return
		var player: AnimationPlayer = players[0]
		var skeleton: Skeleton3D = skeletons[0]
		var names: Array = []
		for bone in range(skeleton.get_bone_count()): names.append(str(skeleton.get_bone_name(bone)))
		var meshes: Array = []
		for node in mesh_nodes:
			if node.get_node(node.skeleton) != skeleton or node.get_blend_shape_count() != 0:
				quit(6)
				return
			var binds: Array = []
			for bind in range(node.skin.get_bind_count()):
				var name := str(node.skin.get_bind_name(bind))
				var bone: int = skeleton.find_bone(name) if name != "" else node.skin.get_bind_bone(bind)
				if bone < 0 or bone >= names.size():
					quit(7)
					return
				binds.append({"bone": bone, "pose": matrix(node.skin.get_bind_pose(bind))})
			for surface in range(node.mesh.get_surface_count()):
				var arrays: Array = node.mesh.surface_get_arrays(surface)
				var positions: Array = []
				for point in arrays[Mesh.ARRAY_VERTEX]: positions.append(vector(point))
				meshes.append({"node": str(node.get_path()), "surface": surface, "binds": binds,
					"positions": positions, "weights": Array(arrays[Mesh.ARRAY_WEIGHTS]), "bones": Array(arrays[Mesh.ARRAY_BONES]),
					"primitive_type": node.mesh.surface_get_primitive_type(surface),
					"indices": Array(arrays[Mesh.ARRAY_INDEX]) if arrays[Mesh.ARRAY_INDEX] != null else []})
		if request.playback_mode == "native-authoring":
			if NativeTracks.install(player, skeleton, item.native_payload, item.animation_output) != OK:
				quit(8)
				return
		var selected := ""
		for animation in player.get_animation_list():
			if animation != "RESET":
				if selected != "":
					quit(9)
					return
				selected = animation
		if selected == "":
			quit(10)
			return
		player.callback_mode_process = AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_MANUAL
		player.play(selected)
		var frames: Array = []
		for time in times:
			if request.playback_mode == "native-authoring":
				if NativePreview.seek(player, skeleton, player.get_animation(selected), float(time)) != OK:
					quit(11)
					return
			else: player.seek(float(time), true)
			var bones: Array = []
			for bone in range(skeleton.get_bone_count()): bones.append(matrix(skeleton.global_transform * skeleton.get_bone_global_pose(bone)))
			var mesh_world: Array = []
			for node in mesh_nodes: mesh_world.append({"node": str(node.get_path()), "matrix": matrix(node.global_transform)})
			frames.append({"requested_time_s": time, "actual_time_s": player.current_animation_position,
				"bones": bones, "skeleton_world": matrix(skeleton.global_transform), "mesh_world": mesh_world})
		report.cases.append({"id": item.id, "path": item.path, "animation_index": index,
			"original_animation_count": animations.size(), "source_animation_original_name": original_name,
			"selected_animation": selected, "bone_names": names, "meshes": meshes,
			"duration_s": player.get_animation(selected).length, "loop_mode": player.get_animation(selected).loop_mode, "frames": frames})
		model.queue_free()
		await process_frame
	for name in request.objects:
		var target := Node3D.new()
		root.add_child(target)
		var frames: Array = []
		for time in times:
			target.transform = sample_object(request.objects[name].keyframes, float(time))
			var q := target.quaternion
			frames.append({"requested_time_s": time, "matrix": matrix(target.global_transform), "rotation_xyzw": [q.x, q.y, q.z, q.w]})
		report.objects.append({"id": name, "frames": frames})
		target.queue_free()
	var output := FileAccess.open(args[1], FileAccess.WRITE)
	output.store_string(JSON.stringify(report, "", true, true))
	output.close()
	quit(0)
