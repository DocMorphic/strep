extends SceneTree
const Adapter = preload("godot_native_root_adapter.gd")
const Clock = preload("native_engine_clock.gd")

func vector(v: Vector3) -> Array: return [v.x, v.y, v.z]
func matrix(v: Transform3D) -> Array: return [vector(v.basis.x), vector(v.basis.y), vector(v.basis.z), vector(v.origin)]
func decode(rows: Array) -> Transform3D:
	return Transform3D(Basis(Vector3(rows[0][0], rows[1][0], rows[2][0]), Vector3(rows[0][1], rows[1][1], rows[2][1]), Vector3(rows[0][2], rows[1][2], rows[2][2])), Vector3(rows[0][3], rows[1][3], rows[2][3]))

func frame(helper, s: Skeleton3D, a: Node3D) -> Dictionary:
	var bones: Array = []
	for bone in range(s.get_bone_count()): bones.append(matrix(s.global_transform * s.get_bone_global_pose(bone)))
	return {"time_s": helper.time_s, "bones": bones, "actor_world": matrix(a.global_transform), "root_motion": matrix(helper.root_motion_transform), "root_delta": matrix(helper.root_motion_delta), "root_in_actor": matrix(a.global_transform.affine_inverse() * s.global_transform * s.get_bone_global_pose(helper.root_bone))}

func mesh_data(model: Node3D, s: Skeleton3D) -> Array:
	var meshes: Array = []
	for node in Adapter.nodes(model):
		if not node is MeshInstance3D: continue
		var binds: Array = []
		for bind in range(node.skin.get_bind_count()):
			var name := str(node.skin.get_bind_name(bind))
			var bone: int = s.find_bone(name) if name != "" else node.skin.get_bind_bone(bind)
			if bone < 0 or bone >= s.get_bone_count(): return []
			binds.append({"bone": bone, "pose": matrix(node.skin.get_bind_pose(bind))})
		for surface in range(node.mesh.get_surface_count()):
			var arrays: Array = node.mesh.surface_get_arrays(surface)
			var positions: Array = []
			for point in arrays[Mesh.ARRAY_VERTEX]: positions.append(vector(point))
			meshes.append({"node": str(node.get_path()), "surface": surface, "binds": binds, "positions": positions, "weights": Array(arrays[Mesh.ARRAY_WEIGHTS]), "bones": Array(arrays[Mesh.ARRAY_BONES]), "primitive_type": node.mesh.surface_get_primitive_type(surface), "indices": Array(arrays[Mesh.ARRAY_INDEX]) if arrays[Mesh.ARRAY_INDEX] != null else []})
	return meshes

func fail(message: String) -> void:
	push_error(message); quit(2)

func _initialize() -> void: call_deferred("audit")

func audit() -> void:
	var args := OS.get_cmdline_user_args()
	if args.size() != 2: fail("Two audit paths required"); return
	var request = JSON.parse_string(FileAccess.get_file_as_string(args[0]))
	var times := Clock.decode(request.clock, int(request.clock.count))
	if times.is_empty(): fail("Complete binary clock required"); return
	var document := GLTFDocument.new(); var state := GLTFState.new()
	if document.append_from_file(request.glb, state) != OK: fail("Rig import failed"); return
	var source_animations := state.get_animations()
	if request.animation_index < 0 or request.animation_index >= source_animations.size(): fail("Selected animation missing"); return
	var selected: Array[GLTFAnimation] = [source_animations[int(request.animation_index)]]
	state.set_animations(selected)
	var model := document.generate_scene(state, 30.0, false, false)
	var actor := Node3D.new(); root.add_child(actor); actor.add_child(model)
	actor.global_transform = decode(request.placement)
	await process_frame
	var players: Array = []; var skeletons: Array = []
	for node in Adapter.nodes(actor):
		if node is AnimationPlayer: players.append(node)
		if node is Skeleton3D: skeletons.append(node)
	if players.size() != 1 or skeletons.size() != 1: fail("One skeleton/player required"); return
	var player: AnimationPlayer = players[0]; var skeleton: Skeleton3D = skeletons[0]
	# Load the PREVIOUSLY SAVED resource, never generate/rewrite native keys here.
	var animation := ResourceLoader.load(request.animation_resource, "Animation", ResourceLoader.CACHE_MODE_IGNORE) as Animation
	if animation == null: fail("Saved native resource missing"); return
	for name in player.get_animation_library_list(): player.remove_animation_library(name)
	var library := AnimationLibrary.new(); library.add_animation("Native", animation); player.add_animation_library("", library)
	var channels: Array = []
	for track in range(animation.get_track_count()):
		var values: Array = []; var keys: Array = []
		for key in range(animation.track_get_key_count(track)):
			keys.append(animation.track_get_key_time(track, key))
			var value = animation.track_get_key_value(track, key)
			values.append([value.x, value.y, value.z, value.w] if value is Quaternion else vector(value))
		channels.append({"path": str(animation.track_get_path(track)), "type": animation.track_get_type(track), "times_s": keys, "values": values})
	var names: Array = []
	for bone in range(skeleton.get_bone_count()): names.append(str(skeleton.get_bone_name(bone)))
	var embedded := Adapter.new()
	if embedded.bind(player, skeleton, actor, "Native", request.root_bone, false) != OK: fail("Native embedded binding rejected"); return
	var meshes := mesh_data(model, skeleton)
	if meshes.is_empty(): fail("Complete raw skin required"); return
	var report := {"engine": Engine.get_version_info(), "bone_names": names, "meshes": meshes, "channels": channels, "duration_s": animation.length, "embedded": [], "extracted": [], "preview": [], "invalid_rejected": false, "malformed_bindings_rejected": false}
	for time in times:
		if embedded.advance_to(time) != OK: fail("Embedded clock rejected"); return
		report.embedded.append(frame(embedded, skeleton, actor))
	var extracted := Adapter.new()
	if extracted.bind(player, skeleton, actor, "Native", request.root_bone, true) != OK: fail("Native extraction binding rejected"); return
	for time in times:
		if extracted.advance_to(time) != OK: fail("Extracted clock rejected"); return
		report.extracted.append(frame(extracted, skeleton, actor))
	var terminal := frame(extracted, skeleton, actor)
	for invalid in [-1.0, animation.length + 1.0, NAN, INF, -INF, 0.0]:
		if extracted.advance_to(invalid) == OK or frame(extracted, skeleton, actor) != terminal: fail("Invalid advance mutated state"); return
	for invalid in [-1.0, animation.length + 1.0, NAN, INF, -INF]:
		if extracted.seek_preview(invalid) == OK or frame(extracted, skeleton, actor) != terminal: fail("Invalid preview mutated state"); return
	report.invalid_rejected = true
	# Invalid bindings must not alter actor/poses/player or bind partially.
	var malformed := 0
	var candidates: Array = []
	for kind in ["loop", "disabled", "duplicate", "method", "scale", "nonlinear"]:
		var changed: Animation = animation.duplicate(true)
		match kind:
			"loop": changed.loop_mode = Animation.LOOP_LINEAR
			"disabled": changed.track_set_enabled(0, false)
			"duplicate": changed.copy_track(0, changed)
			"method": changed.add_track(Animation.TYPE_METHOD)
			"scale":
				var track := changed.add_track(Animation.TYPE_SCALE_3D)
				changed.track_set_path(track, animation.track_get_path(0)); changed.scale_track_insert_key(track, 0.0, Vector3(2, 1, 1))
			"nonlinear": changed.track_set_interpolation_type(0, Animation.INTERPOLATION_NEAREST)
		library.add_animation(kind, changed); candidates.append([kind, request.root_bone])
	candidates.append(["Native", "missing-root"])
	if skeleton.get_bone_count() > 1:
		for bone in range(skeleton.get_bone_count()):
			if skeleton.get_bone_name(bone) != request.root_bone:
				candidates.append(["Native", skeleton.get_bone_name(bone)]); break
	for candidate in candidates:
		var helper := Adapter.new()
		var clock_before := player.current_animation_position
		if helper.bind(player, skeleton, actor, candidate[0], candidate[1], true) == OK or helper.bound or player.current_animation_position != clock_before or frame(extracted, skeleton, actor) != terminal: fail("Malformed binding mutated state"); return
		malformed += 1
	# Reject a competing built-in extraction path and unskinned scene geometry.
	player.root_motion_track = animation.track_get_path(0)
	var conflict := Adapter.new()
	if conflict.bind(player, skeleton, actor, "Native", request.root_bone, true) == OK or conflict.bound: fail("Competing root extraction accepted"); return
	player.root_motion_track = NodePath("")
	var accessory := MeshInstance3D.new(); accessory.mesh = BoxMesh.new(); actor.add_child(accessory)
	var static_helper := Adapter.new()
	if static_helper.bind(player, skeleton, actor, "Native", request.root_bone, true) == OK or static_helper.bound: fail("Unskinned accessory accepted"); return
	actor.remove_child(accessory); accessory.free()
	if frame(extracted, skeleton, actor) != terminal: fail("Ineligible binding changed poses"); return
	malformed += 2
	report.malformed_bindings_rejected = true; report.malformed_bindings = malformed
	# Reverse/repeated previews restore the original base poses before evaluating.
	for time in [0.0, times[-1], times[int(times.size()/2)], times[-1], 0.0, 0.0]:
		if extracted.seek_preview(time) != OK: fail("Preview rejected"); return
		report.preview.append(frame(extracted, skeleton, actor))
	if extracted.advance_to(0.0) != OK or extracted.root_motion_delta != Transform3D.IDENTITY: fail("Repeated clock changed root delta"); return
	var output := FileAccess.open(args[1], FileAccess.WRITE)
	output.store_string(JSON.stringify(report, "", true, true)); output.close(); quit(0)
