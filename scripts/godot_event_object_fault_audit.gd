extends "godot_event_object_audit.gd"
var injected := false

func start_case() -> void:
	injected=false
	super.start_case()

func grip() -> Transform3D:
	var value := super.grip()
	if injected and request.cases[case_index].fault=="nonrigid_grip": value.basis=value.basis.scaled(Vector3(2,1,1))
	return value

func record(observation: Dictionary) -> void:
	super.record(observation)
	if complete or injected: return
	var item: Dictionary=request.cases[case_index]
	if observation.tick==int(item.release_frame)*2+4:
		injected=true;stage="expect-fault"
		result.before_fault=serial(observation)
		match item.fault:
			"changed_step": Engine.physics_ticks_per_second=30
			"outside_clock": clock.seek_preview(clock.time_s+0.1)
			"nonrigid_grip": pass

func finish_case() -> void:
	Engine.physics_ticks_per_second=int(request.physics_fps)
	super.finish_case()
