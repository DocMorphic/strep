extends SceneTree
## Offline finite capture. No renderer, process clock or skin/vertex query.
const Runtime = preload("godot_scene_prop_runtime.gd")
const Loader = preload("godot_native_scene_loader.gd")
var runtime
var parent: Node3D
var destination := ""
var last_tick := 0
var closing := false
var request: Dictionary
var report := {"schema":"strep-scene-prop-capture-v1","records":[],"actions":[],"events":[],"faults":[]}

static func bits(seconds: float) -> String:
	var bytes := PackedByteArray(); bytes.resize(8); bytes.encode_double(0,seconds); return bytes.hex_encode()

static func pose_bits(value: Transform3D) -> String:
	var bytes := PackedByteArray(); bytes.resize(128)
	for row in range(4):
		for column in range(4):
			var number: float = (1.0 if column==3 else 0.0) if row==3 else (value.origin[row] if column==3 else value.basis[column][row])
			bytes.encode_double((row*4+column)*8,number)
	return bytes.hex_encode()

func finish(code: int) -> void:
	if closing: return
	closing=true
	var file := FileAccess.open(destination,FileAccess.WRITE)
	file.store_string(JSON.stringify(report,"",true,true)); file.close(); call_deferred("dispose",code)

func dispose(code: int) -> void:
	if runtime!=null: runtime.discard(); runtime=null
	if is_instance_valid(parent): parent.free()
	quit(code)

func _initialize() -> void: call_deferred("start")
func start() -> void:
	var args := OS.get_cmdline_user_args(); destination=args[1]
	request=JSON.parse_string(FileAccess.get_file_as_string(args[0]))
	report.request_sha256=FileAccess.get_sha256(args[0]); report.engine=Engine.get_version_info()
	parent=Node3D.new(); parent.transform=Loader.matrix(request.parent_world_transform); root.add_child(parent)
	if request.floor.enabled:
		var floor_body := StaticBody3D.new(); floor_body.set_meta("strep_collider_id","floor")
		var shape := WorldBoundaryShape3D.new(); shape.plane=Plane(Vector3.UP,float(request.floor.height_m))
		var collision := CollisionShape3D.new(); collision.shape=shape; floor_body.add_child(collision)
		var material := PhysicsMaterial.new(); material.friction=request.floor.friction; material.bounce=request.floor.restitution
		floor_body.physics_material_override=material; root.add_child(floor_body)
	runtime=Runtime.new()
	if runtime.bind(parent,request.asset_folder,request.config)!=OK:
		report.faults.append(runtime.last_error); finish(2); return
	last_tick=int(request.last_tick); report.physics_fps=int(request.config.physics_fps)
	runtime.loaded.player.gameplay.connect(func(event):
		report.events.append({"id":event.id,"source_time_f64le":bits(event.time_s),"pose_time_f64le":bits(runtime.loaded.player.pose_time_s)})
	)
	runtime.owner.actions_applied.connect(func(actions):
		for action in actions:
			report.actions.append({"object":action.object,"before":action.before,"after":action.after,"event_ids":action.event_ids,
				"tick":action.tick,"source_time_f64le":bits(action.source_time_s),"application_time_f64le":bits(action.physics_application_time_s),
				"pose_f64le":pose_bits(parent.global_transform.affine_inverse()*action.pose),"last_grip_released":action.last_grip_released})
	)
	runtime.owner.faulted.connect(func(reason): report.faults.append(reason); finish(2))
	runtime.owner.sampled.connect(capture)

func capture(record: Dictionary) -> void:
	if closing: return
	var clock: float = float(record.tick)/report.physics_fps
	var inverse := parent.global_transform.affine_inverse()
	var row := {"tick":record.tick,"physics_time_f64le":bits(clock),"source_time_f64le":bits(record.source_time_s),
		"pose_time_f64le":bits(runtime.loaded.player.pose_time_s),"actor_ids":runtime.loaded.player.actors.keys(),
		"members":record.members,"modes":record.modes,"props":{}}
	for id in runtime.config.object_modes:
		if runtime.config.object_modes[id]=="authored":
			row.props[id]={"pose_f64le":pose_bits(inverse*runtime.loaded.objects[id].global_transform),"contacts":[],"mode":"authored"}
		else:
			var p: Dictionary = record.props[id]
			row.props[id]={"pose_f64le":pose_bits(inverse*p.pose),"contacts":p.contacts,"mode":record.modes[id],
				"direct_state_class":p.direct_state_class,"step_s":p.step_s,"collision_layer":p.collision_layer,"collision_mask":p.collision_mask}
	report.records.append(row)
	if record.tick==last_tick: finish(0)
