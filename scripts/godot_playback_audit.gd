extends SceneTree
const Adapter = preload("godot_clip_adapter.gd")
var received: Array = []
var playback_time := 0.0

func vec(v: Vector3) -> Array:
	return [v.x, v.y, v.z]

func rotation(q: Quaternion) -> Array:
	return [q.x, q.y, q.z, q.w]

func record(event: Dictionary) -> void:
	received.append({"event": event, "dispatched_at_s": playback_time})

func descendants(node: Node) -> Array:
	var result: Array = [node]
	for child in node.get_children():
		result.append_array(descendants(child))
	return result

func _initialize() -> void:
	call_deferred("audit")

func audit() -> void:
	var args := OS.get_cmdline_user_args()
	var request = JSON.parse_string(FileAccess.get_file_as_string(args[0]))
	var report: Dictionary = {"engine": Engine.get_version_info(), "cases": []}
	for item in request.cases:
		var document := GLTFDocument.new()
		var state := GLTFState.new()
		assert(document.append_from_file(item.path, state) == OK)
		var model := document.generate_scene(state, 30.0, false, false)
		root.add_child(model)
		await process_frame
		var player: AnimationPlayer
		for node in descendants(model):
			if node is AnimationPlayer:
				player = node
		assert(player != null)
		var selected := ""
		for name in player.get_animation_list():
			if name != "RESET":
				selected = name
		assert(selected != "")
		var adapter := Adapter.new()
		adapter.name = "StrepEvents"
		model.add_child(adapter)
		adapter.marker.connect(record)
		var events = JSON.parse_string(FileAccess.get_file_as_string(item.events)) if item.has("events") else {"fps": 30, "events": []}
		# Reject malformed documents before mutating animation tracks.
		var before_count := player.get_animation(selected).get_track_count()
		assert(adapter.bind_clip(player, selected, {"fps": 30, "events": [{"type": "bad", "actor": "A", "frame": 1, "time_s": 2}]}) != OK)
		assert(player.get_animation(selected).get_track_count() == before_count)
		assert(adapter.bind_clip(player, selected, events) == OK)
		assert(adapter.bind_clip(player, selected, events) != OK)
		var imported_duration := player.get_animation(selected).length
		assert(adapter.hold_terminal_frame(player, selected, 30.0) == OK)
		assert(adapter.extract_root(player, selected, "Hips") == OK)
		player.callback_mode_process = AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_MANUAL
		player.callback_mode_method = AnimationMixer.ANIMATION_CALLBACK_MODE_METHOD_IMMEDIATE
		var runs: Array = []
		for stride in [1, 17]:
			player.stop()
			received = []
			playback_time = 0.0
			player.play(selected)
			player.advance(0.0)
			var frames: Array = []
			var last_frame := 0
			while last_frame < int(item.frames) - 1:
				var next_frame: int = mini(last_frame + stride, int(item.frames) - 1)
				playback_time = float(next_frame) / 30.0
				player.advance(float(next_frame - last_frame) / 30.0)
				frames.append({"from_frame": last_frame, "to_frame": next_frame,
					"position_delta": vec(player.get_root_motion_position()), "rotation_delta": rotation(player.get_root_motion_rotation())})
				last_frame = next_frame
			# A final tiny advance crosses a last-frame event if floating-point time
			# lands just before its key; it must never dispatch earlier events again.
			playback_time = player.get_animation(selected).length + 0.000001
			player.advance(1.0 / 30.0 + 0.000001)
			runs.append({"stride_frames": stride, "events": received.duplicate(true), "root_motion": frames,
				"terminal_position_delta": vec(player.get_root_motion_position()), "terminal_rotation_delta": rotation(player.get_root_motion_rotation())})
		# Timeline scrubbing must not trigger gameplay side effects.
		received = []
		adapter.seek_preview(player, 0.0)
		adapter.seek_preview(player, player.get_animation(selected).length)
		for event in events.events:
			adapter.seek_preview(player, float(event.time_s))
		var seek_events := received.duplicate(true)
		report.cases.append({"id": item.id, "root_motion_track": str(player.root_motion_track), "runs": runs, "seek_events": seek_events,
			"imported_duration_s": imported_duration, "playback_duration_s": player.get_animation(selected).length})
		model.queue_free()
		await process_frame
	var output := FileAccess.open(args[1], FileAccess.WRITE)
	output.store_string(JSON.stringify(report))
	output.close()
	print("Playback audited ", report.cases.size(), " clips")
	quit(0)
