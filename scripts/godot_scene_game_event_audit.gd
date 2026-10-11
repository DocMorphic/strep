extends SceneTree

const Events = preload("godot_scene_game_events.gd")
const Clock = preload("native_engine_clock.gd")

func _initialize() -> void:
	var args := OS.get_cmdline_user_args()
	if args.size() != 2:
		quit(2)
		return
	var request = JSON.parse_string(FileAccess.get_file_as_string(args[0]))
	var document = JSON.parse_string(FileAccess.get_file_as_string(request.events_path))
	var clock := Clock.decode(document.clock, int(document.clock.count))
	var dispatcher := Events.new()
	if not dispatcher.configure(document):
		quit(3)
		return
	var traces := {}
	for scenario in request.scenarios:
		dispatcher.reset()
		var fired: Array = []
		for index in scenario.indices:
			var result: Dictionary = dispatcher.advance(clock[int(index)])
			if not result.valid:
				quit(4)
				return
			fired.append_array(result.events)
		traces[scenario.id] = fired
	var before: Variant = dispatcher.cursor
	var invalid_rejected := true
	for invalid_time in [-1.0, clock[-1] + 1.0, 0.0, NAN, INF]:
		var rejected: Dictionary = dispatcher.advance(invalid_time)
		invalid_rejected = invalid_rejected and not rejected.valid and dispatcher.cursor == before
	var malformed: Array = []
	# Empty event tracks are valid. Isolate rejection fixtures from dispatch
	# observations, without adding events to the exported character document.
	var basis: Dictionary = document.duplicate(true)
	if basis.events.is_empty():
		basis.events.append({"id":"audit-fixture", "name":"audit-fixture", "actor":"audit", "sample_index":0, "kind":"gameplay_intent", "timing_confirmed":true, "runtime_dispatch_allowed":true})
	var checked_basis := Events.new()
	if not checked_basis.configure(basis):
		quit(5)
		return
	var bad: Dictionary = basis.duplicate(true)
	bad.events.append(bad.events[0].duplicate(true))
	malformed.append(bad)
	bad = basis.duplicate(true)
	bad.events[0].sample_index = clock.size()
	malformed.append(bad)
	bad = basis.duplicate(true)
	bad.events[0].sample_index = true
	malformed.append(bad)
	bad = basis.duplicate(true)
	bad.clock.bytes_hex = bad.clock.bytes_hex.substr(2)
	malformed.append(bad)
	bad = basis.duplicate(true)
	bad.events[0].timing_confirmed = "yes"
	malformed.append(bad)
	bad = basis.duplicate(true)
	var contact_id := "audit-invalid-contact"
	var ids := {}
	for entry in bad.events:ids[entry.id] = true
	while ids.has(contact_id):contact_id += "_"
	bad.events.append({"id":contact_id, "name":"audit-contact", "actor":"audit", "sample_index":basis.events[-1].sample_index, "kind":"contact_intent", "timing_confirmed":true, "runtime_dispatch_allowed":true})
	malformed.append(bad)
	var malformed_rejected := true
	for forged in malformed:
		var candidate := Events.new()
		malformed_rejected = malformed_rejected and not candidate.configure(forged)
	var output := FileAccess.open(args[1], FileAccess.WRITE)
	output.store_string(JSON.stringify({"engine":Engine.get_version_info(), "traces":traces, "invalid_rejected":invalid_rejected, "malformed_configs_rejected":malformed_rejected, "malformed_config_cases":malformed.size()}, "", false, true))
	output.close()
	quit(0)
