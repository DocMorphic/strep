extends SceneTree
const Loader = preload("godot_native_scene_loader.gd")
const Observe = preload("godot_native_scene_observations.gd")
const Boot = preload("godot_native_scene_boot.gd")
var callbacks: Array = []
var reentrant_rejected := true

class ParentListener extends Node3D:
	var received: Array = []
	var ready_to_listen := false
	func _ready() -> void:
		ready_to_listen = true
		get_node("Player").gameplay.connect(record_event)
	func record_event(event: Dictionary) -> void:
		var player = get_node("Player")
		received.append({"id": event.id, "sample_index": event.sample_index, "pose_time_s": player.motion.pose_time_s, "parent_ready": ready_to_listen})

func fail(message: String) -> void: push_error(message); quit(2)
func _initialize() -> void: call_deferred("audit")

func audit() -> void:
	var args := OS.get_cmdline_user_args()
	if args.size() != 2: fail("Two audit paths required"); return
	var request = JSON.parse_string(FileAccess.get_file_as_string(args[0]))
	var parent := Node3D.new(); root.add_child(parent)
	var report := {"engine": Engine.get_version_info(), "modes": {}}
	for mode in ["embedded", "extracted", "mixed"]:
		var config: Dictionary = request.config.duplicate(true)
		for index in range(config.actors.size()): config.actors[index].extract = mode == "extracted" or (mode == "mixed" and index % 2 == 0)
		var loaded := Loader.load_scene(parent, request.asset_folder, config)
		if loaded.is_empty(): fail("Saved scene loading failed: " + mode); return
		var scene = loaded.player; var times: PackedFloat64Array = scene.times
		var malformed_count := 0
		var initial := Observe.snapshot(scene); var child_count := parent.get_child_count()
		for fault in ["root", "partial-root", "index", "index-bool", "duplicate", "event-hash", "mode", "scene-hash", "missing-objects", "empty-objects", "object-population"]:
			var bad: Dictionary = config.duplicate(true)
			match fault:
				"root": bad.actors[-1].root_bone = "missing-root"
				"partial-root":
					var helper = scene.actors[scene.actors.keys()[-1]]
					for bone in range(helper.skeleton.get_bone_count()):
						if helper.skeleton.get_bone_name(bone) != bad.actors[-1].root_bone:
							bad.actors[-1].root_bone = str(helper.skeleton.get_bone_name(bone)); break
				"index": bad.actors[-1].animation_index = 1000000
				"index-bool": bad.actors[-1].animation_index = false
				"duplicate": bad.actors.append(bad.actors[0].duplicate(true))
				"event-hash": bad.events.sha256 = "invalid-hash"
				"mode": bad.actors[-1].extract = "yes"
				"scene-hash": bad.scene.sha256 = "invalid-hash"
				"missing-objects": bad.erase("objects")
				"empty-objects": bad.objects = {"names": []}
				"object-population":
					if config.objects == null: bad.objects = {"names": ["ghost"]}
					else: bad.objects = null
			var rejected := Loader.load_scene(parent, request.asset_folder, bad)
			if not rejected.is_empty() or parent.get_child_count() != child_count or Observe.snapshot(scene) != initial: fail("Malformed scene config changed existing scene"); return
			malformed_count += 1
		callbacks = []; reentrant_rejected = true
		scene.gameplay.connect(func(event):
			callbacks.append({"event": event.duplicate(true), "scene": Observe.snapshot(scene)})
			var before := Observe.snapshot(scene)
			if scene.advance_to(scene.pose_time_s).valid or scene.seek_preview(0.0) == OK or scene.restart() == OK or Observe.snapshot(scene) != before: reentrant_rejected = false
		)
		var entry := {"actors": {}, "object_channels": Observe.channels(scene.props.animation) if scene.props != null else [], "frames": [], "events": [], "previews": [], "traces": {}, "invalid_rejected": false, "late_participant_rejected": false, "malformed_configs_rejected": true, "malformed_configs": malformed_count}
		for track in range(entry.object_channels.size()): entry.object_channels[track].target_name = str(scene.props.targets[track].name)
		for name in scene.actors: entry.actors[name] = Observe.skin_data(scene.actors[name])
		for time in times:
			if not scene.advance_to(time).valid: fail("Full scene clock rejected"); return
			entry.frames.append(Observe.snapshot(scene))
		entry.events = callbacks.duplicate(true)
		var terminal := Observe.snapshot(scene)
		var event_cursor = scene.events.cursor
		for invalid in [-1.0, times[-1]+1.0, NAN, INF, -INF, 0.0]:
			if scene.advance_to(invalid).valid or Observe.snapshot(scene) != terminal or scene.events.cursor != event_cursor: fail("Invalid scene advance mutated state"); return
		for invalid in [-1.0, times[-1]+1.0, NAN, INF, -INF]:
			if scene.seek_preview(invalid) == OK or Observe.snapshot(scene) != terminal or scene.events.cursor != event_cursor: fail("Invalid scene preview mutated state"); return
		entry.invalid_rejected = true
		for time in [0.0, times[-1], times[int(times.size()/2)], times[-1], 0.0, 0.0]:
			if scene.seek_preview(time) != OK or scene.events.cursor != event_cursor or scene.playback_time_s != times[-1]: fail("Preview altered playback cursor"); return
			entry.previews.append(Observe.snapshot(scene))
		var callback_count := callbacks.size()
		if not scene.advance_to(times[-1]).valid or callbacks.size() != callback_count: fail("Preview replayed events"); return
		for delta in scene.root_deltas.values():
			if delta != Transform3D.IDENTITY: fail("Repeated playback clock moved root"); return
		var scenarios := {"whole-clip": [times.size()-1], "skipped": [0, int(times.size()/3), int(times.size()*2/3), times.size()-1], "repeated": [0,0,int(times.size()/2),int(times.size()/2),times.size()-1,times.size()-1]}
		for id in scenarios:
			if scene.restart() != OK: fail("Explicit restart failed"); return
			callbacks = []
			for index in scenarios[id]:
				if not scene.advance_to(times[index]).valid: fail("Skipped scene clock rejected"); return
			entry.traces[id] = callbacks.duplicate(true)
		# A changed LAST participant must reject before updating any earlier actor,
		# objects, event cursor or gameplay state.
		var last = scene.actors[scene.actors.keys()[-1]]
		last.skeleton.add_bone("late-invalid-bone")
		var before := Observe.snapshot(scene); event_cursor = scene.events.cursor
		if scene.advance_to(times[-1]).valid or scene.seek_preview(0.0) == OK or scene.restart() == OK or Observe.snapshot(scene) != before or scene.events.cursor != event_cursor: fail("Late participant failure partially advanced scene"); return
		entry.late_participant_rejected = true; entry.reentrant_rejected = reentrant_rejected
		report.modes[mode] = entry
		for connection in scene.get_signal_connection_list("gameplay"): scene.gameplay.disconnect(connection.callable)
		loaded.container.free()
	# Exercise the actual exported bootstrap, including child-before-parent ready
	# ordering. No camera/GPU mesh readback or physical simulation is involved.
	var listener := ParentListener.new(); var boot := Boot.new(); boot.name = "Player"
	listener.add_child(boot); root.add_child(listener)
	for index in range(4): await process_frame
	if boot.motion == null or boot.motion.playback_time_s == null: fail("Exported bootstrap did not advance"); return
	var initial: Array = []
	for entry in listener.received:
		if entry.sample_index == 0:
			if entry.pose_time_s != 0.0 or not entry.parent_ready: fail("Initial bootstrap callback used wrong pose/listener order"); return
			initial.append(entry.id)
	report.bootstrap = {"parent_ready_listener": true, "initial_event_ids": initial, "frames": 4, "valid_clock": is_finite(boot.motion.playback_time_s) and boot.motion.playback_time_s >= 0.0 and boot.motion.playback_time_s <= boot.motion.times[-1]}
	listener.free()
	var output := FileAccess.open(args[1], FileAccess.WRITE)
	output.store_string(JSON.stringify(report, "", true, true)); output.close(); quit(0)
