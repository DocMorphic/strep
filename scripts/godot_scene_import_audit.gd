extends SceneTree

func matrix(t: Transform3D) -> Array:
	return [[t.basis.x.x,t.basis.x.y,t.basis.x.z],[t.basis.y.x,t.basis.y.y,t.basis.y.z],[t.basis.z.x,t.basis.z.y,t.basis.z.z],[t.origin.x,t.origin.y,t.origin.z]]

func descendants(node: Node) -> Array:
	var found: Array = [node]
	for child in node.get_children():
		found.append_array(descendants(child))
	return found

func exact_time(time: float) -> String:
	var bytes := PackedByteArray()
	bytes.resize(8)
	bytes.encode_double(0, time)
	return bytes.hex_encode()

func sample_clock(item: Dictionary) -> PackedFloat64Array:
	var times := PackedFloat64Array()
	if item.has("sample_clock"):
		var value: Dictionary = item.sample_clock
		if value.get("schema") != "strep-native-engine-clock-f64le-v1" or value.get("count") != item.frames:
			return times
		var encoded = value.get("bytes_hex")
		if not encoded is String or encoded.length() != int(item.frames) * 16:
			return times
		var bytes: PackedByteArray = encoded.hex_decode()
		if bytes.size() != int(item.frames) * 8 or bytes.hex_encode() != encoded:
			return times
		for i in range(int(item.frames)):
			var time := bytes.decode_double(i * 8)
			if not is_finite(time) or (i == 0 and time != 0.0) or (i > 0 and time <= times[i-1]):
				return PackedFloat64Array()
			times.append(time)
	else:
		for i in range(int(item.frames)): times.append(float(i) / 30.0)
	return times

func _initialize() -> void:
	call_deferred("run_audit")

func run_audit() -> void:
	var args := OS.get_cmdline_user_args()
	if args.size() != 2:
		quit(2)
		return
	var request = JSON.parse_string(FileAccess.get_file_as_string(args[0]))
	var report: Dictionary = {"engine":Engine.get_version_info(),"scenes":[]}
	for item in request.scenes:
		var times := sample_clock(item)
		if times.size() != int(item.frames) or times.size() < 2:
			quit(10)
			return
		var holder := Node3D.new()
		root.add_child(holder)
		var actors: Dictionary = {}
		for name in item.actors:
			var entry = item.actors[name]
			var document := GLTFDocument.new()
			var state := GLTFState.new()
			var code := document.append_from_file(entry.path,state)
			if code != OK:
				push_error("Actor import failed: " + str(code))
				quit(3)
				return
			var model := document.generate_scene(state,30.0,false,false)
			var placement := Node3D.new()
			holder.add_child(placement)
			var p = entry.transform.translation_m
			var q = entry.transform.rotation_xyzw
			placement.transform = Transform3D(Basis(Quaternion(q[0],q[1],q[2],q[3])),Vector3(p[0],p[1],p[2]))
			placement.add_child(model)
			await process_frame
			var player: AnimationPlayer
			var skeleton: Skeleton3D
			for node in descendants(model):
				if node is AnimationPlayer:
					player = node
				if node is Skeleton3D:
					skeleton = node
			if player == null or skeleton == null:
				push_error("Missing actor skeleton/player")
				quit(4)
				return
			var selected := ""
			for animation in player.get_animation_list():
				if animation != "RESET":
					selected = animation
					break
			if selected == "":
				quit(5)
				return
			player.callback_mode_process = AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_MANUAL
			player.play(selected)
			var names: Array = []
			for bone in range(skeleton.get_bone_count()):
				names.append(skeleton.get_bone_name(bone))
			actors[name] = {"player":player,"skeleton":skeleton,"bone_names":names,"animation":selected}
		var frames: Array = []
		var object_player: AnimationPlayer
		var objects: Dictionary = {}
		if item.has("objects_glb"):
			var document := GLTFDocument.new()
			var state := GLTFState.new()
			if document.append_from_file(item.objects_glb,state,GLTFDocument.IMPORT_FLAG_FORCE_DISABLE_MESH_COMPRESSION) != OK:
				quit(6)
				return
			var model := document.generate_scene(state,30.0,false,false)
			holder.add_child(model)
			await process_frame
			for node in descendants(model):
				if node is AnimationPlayer:
					object_player = node
				for name in item.object_names:
					if str(node.name) == "Object_" + name:
						objects[name] = node
			if object_player == null or objects.size() != item.object_names.size():
				push_error("Missing standalone object nodes/player")
				quit(7)
				return
			var selected := ""
			for animation in object_player.get_animation_list():
				if animation != "RESET":
					selected = animation
					break
			if selected == "":
				quit(8)
				return
			object_player.callback_mode_process = AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_MANUAL
			object_player.play(selected)
		var object_frames: Array = []
		var object_meshes: Dictionary = {}
		if item.get("audit_object_meshes", false):
			for name in objects:
				var node = objects[name]
				if not node is MeshInstance3D or node.mesh == null:
					quit(9)
					return
				var surfaces: Array = []
				for surface in range(node.mesh.get_surface_count()):
					var arrays = node.mesh.surface_get_arrays(surface)
					var positions: Array = []
					var normals: Array = []
					for point in arrays[Mesh.ARRAY_VERTEX]:
						positions.append([point.x, point.y, point.z])
					for normal in arrays[Mesh.ARRAY_NORMAL]:
						normals.append([normal.x, normal.y, normal.z])
					surfaces.append({"positions":positions,"normals":normals})
				object_meshes[name] = surfaces
		var clock_samples: Array = []
		for time in times:
			var sample: Dictionary = {}
			var clock: Dictionary = {"requested_time_s":time,"actors":{},"objects_time_s":null,"requested_time_f64le":exact_time(time),"actor_times_f64le":{},"objects_time_f64le":null}
			# Both actors exist in one scene and seek to the same source clock.
			for name in actors:
				actors[name].player.seek(time,true,true)
				clock.actors[name] = actors[name].player.current_animation_position
				clock.actor_times_f64le[name] = exact_time(actors[name].player.current_animation_position)
			if object_player != null:
				object_player.seek(time,true,true)
				clock.objects_time_s = object_player.current_animation_position
				clock.objects_time_f64le = exact_time(object_player.current_animation_position)
			var object_sample: Dictionary = {}
			for name in objects:
				object_sample[name] = matrix(objects[name].global_transform)
			object_frames.append(object_sample)
			for name in actors:
				var skeleton: Skeleton3D = actors[name].skeleton
				var bones: Array = []
				for bone in range(skeleton.get_bone_count()):
					bones.append(matrix(skeleton.global_transform*skeleton.get_bone_global_pose(bone)))
				sample[name] = bones
			frames.append(sample)
			clock_samples.append(clock)
		var metadata: Dictionary = {}
		for name in actors:
			metadata[name] = {"bone_names":actors[name].bone_names,"animation":actors[name].animation,"animation_index":0,"duration_s":actors[name].player.get_animation(actors[name].animation).length,"loop_mode":actors[name].player.get_animation(actors[name].animation).loop_mode}
		report.scenes.append({"id":item.id,"actors":metadata,"frames":frames,"object_frames":object_frames,"object_meshes":object_meshes,"clock_samples":clock_samples})
		holder.queue_free()
		await process_frame
	var output := FileAccess.open(args[1],FileAccess.WRITE)
	output.store_string(JSON.stringify(report))
	output.close()
	print("Verified import and clock sampling for ",report.scenes.size()," paired scenes")
	quit(0)
