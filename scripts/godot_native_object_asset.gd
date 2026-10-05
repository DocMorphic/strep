extends SceneTree
const NativeClock = preload("res://native_engine_clock.gd")

func clock_bits(time: float) -> String:
	var bytes := PackedByteArray(); bytes.resize(8); bytes.encode_double(0,time); return bytes.hex_encode()

func descendants(node: Node) -> Array:
	var result: Array = [node]
	for child in node.get_children(): result.append_array(descendants(child))
	return result

func _initialize() -> void:
	call_deferred("audit")

func audit() -> void:
	var args := OS.get_cmdline_user_args()
	if args.size() != 2:
		quit(2)
		return
	var request = JSON.parse_string(FileAccess.get_file_as_string(args[0]))
	var bake_fps = request.get("import_bake_fps",30.0)
	if typeof(bake_fps) not in [TYPE_INT,TYPE_FLOAT] or bake_fps not in [30.0,60.0,120.0,240.0]:
		quit(15)
		return
	var times := NativeClock.decode(request.payload.sample_clock, request.payload.sample_times_s.size())
	if times.size() != request.payload.sample_times_s.size():
		quit(14)
		return
	var document := GLTFDocument.new()
	var state := GLTFState.new()
	if document.append_from_file(request.asset_path, state) != OK:
		quit(3)
		return
	if state.get_animations().size() != 1:
		quit(12)
		return
	var model := document.generate_scene(state, float(bake_fps), false, false)
	root.add_child(model)
	await process_frame
	var players: Array = []
	var nodes: Dictionary = {}
	for node in descendants(model):
		if node is AnimationPlayer: players.append(node)
		if node is MeshInstance3D: nodes[str(node.name)] = node
	if players.size() != 1:
		quit(4)
		return
	var player: AnimationPlayer = players[0]
	var selected := ""
	for name in player.get_animation_list():
		if name != "RESET":
			if selected != "":
				quit(5)
				return
			selected = name
	if selected == "":
		quit(6)
		return
	var report: Dictionary = {"engine": Engine.get_version_info(), "import_bake_fps":bake_fps, "default-import": {}, "native-authoring": {}}
	for channel in request.payload.channels:
		if not nodes.has(channel.node_name):
			quit(7)
			return
		for mode in ["default-import", "native-authoring"]: report[mode][channel.object] = []
	if nodes.size() != report["default-import"].size():
		quit(13)
		return
	player.callback_mode_process = AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_MANUAL
	player.play(selected)
	for time in times:
		player.seek(float(time), true)
		for object in report["default-import"]:
			var node: Node3D = nodes["Object_" + object]
			var q := node.quaternion.normalized()
			report["default-import"][object].append({"time_s": time,"time_f64le":clock_bits(time), "translation_m": [node.position.x,node.position.y,node.position.z], "rotation_xyzw": [q.x,q.y,q.z,q.w]})
	var animation := Animation.new()
	animation.length = float(request.payload.duration_s)
	animation.loop_mode = Animation.LOOP_NONE
	var base := player.get_node(player.root_node)
	var types := {"translation": Animation.TYPE_POSITION_3D, "rotation": Animation.TYPE_ROTATION_3D, "scale": Animation.TYPE_SCALE_3D}
	for channel in request.payload.channels:
		var track := animation.add_track(types[channel.path])
		animation.track_set_path(track, base.get_path_to(nodes[channel.node_name]))
		animation.track_set_interpolation_type(track, Animation.INTERPOLATION_LINEAR)
		animation.track_set_interpolation_loop_wrap(track, false)
		for i in range(channel.times_s.size()):
			var t: float = channel.times_s[i]
			var v: Array = channel.values[i]
			match channel.path:
				"translation": animation.position_track_insert_key(track,t,Vector3(v[0],v[1],v[2]))
				"rotation": animation.rotation_track_insert_key(track,t,Quaternion(v[0],v[1],v[2],v[3]).normalized())
				"scale": animation.scale_track_insert_key(track,t,Vector3(v[0],v[1],v[2]))
	if ResourceSaver.save(animation,request.resource_path) != OK:
		quit(8)
		return
	var decoded := ResourceLoader.load(request.resource_path,"Animation",ResourceLoader.CACHE_MODE_IGNORE) as Animation
	if decoded == null or decoded.get_track_count() != request.payload.channels.size() or decoded.length != float(request.payload.duration_s):
		quit(9)
		return
	for track in range(decoded.get_track_count()):
		var channel: Dictionary = request.payload.channels[track]
		if decoded.track_get_key_count(track) != channel.times_s.size():
			quit(10)
			return
		for key in range(channel.times_s.size()):
			if decoded.track_get_key_time(track,key) != float(PackedFloat32Array([channel.times_s[key]])[0]):
				quit(11)
				return
	for time in times:
		for track in range(decoded.get_track_count()):
			var channel: Dictionary = request.payload.channels[track]
			var node: Node3D = nodes[channel.node_name]
			match decoded.track_get_type(track):
				Animation.TYPE_POSITION_3D: node.position = decoded.position_track_interpolate(track,float(time))
				Animation.TYPE_ROTATION_3D: node.quaternion = decoded.rotation_track_interpolate(track,float(time))
				Animation.TYPE_SCALE_3D: node.scale = decoded.scale_track_interpolate(track,float(time))
		for object in report["native-authoring"]:
			var node: Node3D = nodes["Object_" + object]
			var q := node.quaternion.normalized()
			report["native-authoring"][object].append({"time_s": time,"time_f64le":clock_bits(time), "translation_m": [node.position.x,node.position.y,node.position.z], "rotation_xyzw": [q.x,q.y,q.z,q.w]})
	var file := FileAccess.open(args[1],FileAccess.WRITE)
	file.store_string(JSON.stringify(report, "", true, true))
	file.close()
	quit(0)
