extends SceneTree
const Runtime = preload("godot_scene_prop_runtime.gd")
const Loader = preload("godot_native_scene_loader.gd")
const Observe = preload("godot_native_scene_observations.gd")
var runtime
var destination := ""
var result := {"records":[],"faults":[],"bodies":{},"quality_approved":false,"release_approved":false}

func serial(value: Variant) -> Variant:
	if value is Transform3D: return [[value.basis.x.x,value.basis.y.x,value.basis.z.x,value.origin.x],[value.basis.x.y,value.basis.y.y,value.basis.z.y,value.origin.y],[value.basis.x.z,value.basis.y.z,value.basis.z.z,value.origin.z],[0,0,0,1]]
	if value is Vector3: return [value.x,value.y,value.z]
	if value is Dictionary:
		var d := {}
		for key in value: d[key]=serial(value[key])
		return d
	if value is Array:
		var items: Array = []
		for item in value: items.append(serial(item))
		return items
	return value

func fail(reason: String) -> void:
	push_error(reason); quit(2)

func _initialize() -> void: call_deferred("begin")
func begin() -> void:
	var args := OS.get_cmdline_user_args()
	if args.size()!=2: fail("Two audit paths required"); return
	var request = JSON.parse_string(FileAccess.get_file_as_string(args[0])); destination=args[1]
	if not request is Dictionary or not request.get("config") is Dictionary: fail("Complete request required"); return
	var parent := Node3D.new(); parent.transform=Loader.matrix(request.placement); root.add_child(parent)
	var floor_body := StaticBody3D.new(); floor_body.set_meta("strep_collider_id","floor")
	var collision := CollisionShape3D.new(); collision.shape=WorldBoundaryShape3D.new(); floor_body.add_child(collision); root.add_child(floor_body)
	runtime=Runtime.new()
	if runtime.bind(parent,request.asset_folder,request.config)!=OK: fail(runtime.last_error); return
	result.engine=Engine.get_version_info(); result.collision_settings=runtime.collision_settings.duplicate(true)
	result.physics_fps=Engine.physics_ticks_per_second; result.last_tick=int(request.last_tick)
	result.gravity_m_s2=float(ProjectSettings.get_setting("physics/3d/default_gravity"))
	result.gravity_direction=serial(ProjectSettings.get_setting("physics/3d/default_gravity_vector"))
	for id in runtime.bodies:
		result.bodies[id]={"mass_kg":runtime.bodies[id].mass,"inertia_diagonal":serial(runtime.bodies[id].inertia),"continuous_cd":runtime.bodies[id].continuous_cd}
	runtime.owner.faulted.connect(func(reason): result.faults.append(reason); fail(reason))
	runtime.owner.sampled.connect(func(record):
		var snapshot: Dictionary = serial(record); snapshot.scene=Observe.snapshot(runtime.loaded.player); result.records.append(snapshot)
		if record.tick>=int(request.last_tick):
			var file := FileAccess.open(destination,FileAccess.WRITE); file.store_string(JSON.stringify(result)); file.close(); quit(0)
	)
