extends SceneTree
const Adapter = preload("godot_cycle_adapter.gd")
const Prop = preload("godot_event_object_body.gd")
var output: Dictionary = {"cases":[]}
var destination := ""
var request: Dictionary
var case_index := 0
var world: Node3D
var actor: Node3D
var skeleton: Skeleton3D
var clock: Node
var prop: RigidBody3D
var hand := -1
var placement := Transform3D(Basis(Vector3.UP,0.4),Vector3(2,1,-1))
var offset := Transform3D(Basis(Vector3.FORWARD,0.2),Vector3(0.06,-0.04,0.1))
var result: Dictionary
var stage := "forward"
var waits := 0
var complete := false

func nodes(n: Node) -> Array:
	var found: Array=[n]
	for child in n.get_children(): found.append_array(nodes(child))
	return found

func serial(value: Variant) -> Variant:
	if value is Transform3D:
		var b: Basis=value.basis; var p: Vector3=value.origin
		return [[b.x.x,b.y.x,b.z.x,p.x],[b.x.y,b.y.y,b.z.y,p.y],[b.x.z,b.y.z,b.z.z,p.z],[0,0,0,1]]
	if value is Vector3: return [value.x,value.y,value.z]
	if value is Dictionary:
		var converted: Dictionary={}
		for k in value: converted[k]=serial(value[k])
		return converted
	if value is Array:
		var converted: Array=[]
		for item in value: converted.append(serial(item))
		return converted
	return value

func grip() -> Transform3D:
	actor.transform=placement*clock.root_motion_transform if clock.extracted else placement
	return skeleton.global_transform*skeleton.get_bone_global_pose(hand)*offset

func _initialize() -> void:
	call_deferred("run")

func run() -> void:
	var args := OS.get_cmdline_user_args()
	request=JSON.parse_string(FileAccess.get_file_as_string(args[0])); destination=args[1]
	output.engine=Engine.get_version_info(); output.backend=ProjectSettings.get_setting("physics/3d/physics_engine")
	Engine.physics_ticks_per_second=int(request.physics_fps)
	start_case()

func start_case() -> void:
	var item: Dictionary=request.cases[case_index]
	world=Node3D.new();root.add_child(world)
	var floor_body := StaticBody3D.new();floor_body.set_meta("strep_collider_id","floor")
	var floor_shape := CollisionShape3D.new();floor_shape.shape=WorldBoundaryShape3D.new()
	floor_body.add_child(floor_shape);world.add_child(floor_body)
	actor=Node3D.new();actor.transform=placement;world.add_child(actor)
	var document := GLTFDocument.new();var gltf := GLTFState.new()
	assert(document.append_from_file(item.path,gltf)==OK)
	var model := document.generate_scene(gltf,30.0,false,false);actor.add_child(model)
	var player: AnimationPlayer
	for n in nodes(model):
		if n is AnimationPlayer: player=n
		if n is Skeleton3D: skeleton=n
	assert(player!=null and skeleton!=null)
	hand=skeleton.find_bone(item.hand);assert(hand>=0)
	var animation := ""
	for name in player.get_animation_list():
		if name!="RESET": animation=name
	var metadata=JSON.parse_string(FileAccess.get_file_as_string(item.metadata))
	if metadata.schema=="strep-runtime-finite-v1":
		clock=load("res://godot_finite_adapter.gd").new();actor.add_child(clock)
		assert(clock.bind_finite(player,skeleton,actor,animation,metadata,item.path,item.get("extract",true))==OK)
	else:
		clock=Adapter.new();actor.add_child(clock)
		assert(clock.bind_cycle(player,skeleton,actor,animation,metadata,item.path,item.get("extract",true))==OK)
	prop=Prop.new();prop.position=Vector3(0,1,0);prop.mass=2.0;prop.max_contacts_reported=8
	prop.continuous_cd=true;prop.contact_monitor=true
	prop.linear_damp_mode=RigidBody3D.DAMP_MODE_REPLACE;prop.angular_damp_mode=RigidBody3D.DAMP_MODE_REPLACE
	prop.linear_damp=0;prop.angular_damp=0
	var shape := CollisionShape3D.new();shape.shape=BoxShape3D.new();shape.shape.size=Vector3(0.12,0.12,0.12)
	prop.add_child(shape);world.add_child(prop)
	result={"id":item.id,"records":[],"actions":[],"rejections":{},"faults":[]}
	result.rejections.invalid_rate=prop.bind_prop(clock,grip,"test-grasp","test-release",50)
	result.rejections.missing_marker=prop.bind_prop(clock,grip,"missing","test-release")
	var saved_markers: Array=clock.markers.duplicate(true)
	clock.markers[1].source_event.requires_review=true
	result.rejections.unconfirmed=prop.bind_prop(clock,grip,"test-grasp","test-release")
	clock.markers=saved_markers
	assert(prop.bind_prop(clock,grip,"test-grasp","test-release",int(request.physics_fps),128)==OK)
	prop.action_applied.connect(func(e): result.actions.append(serial(e)))
	prop.faulted.connect(func(reason): result.faults.append(reason))
	prop.sampled.connect(record)
	stage="forward";waits=0;complete=false

func record(observation: Dictionary) -> void:
	if complete: return
	observation.stage=stage
	result.records.append(serial(observation))
	var item: Dictionary=request.cases[case_index]
	var release_tick: int=item.release_frame*2
	var attach_tick: int=item.attach_frame*2
	if not observation.failure.is_empty():
		complete=true;call_deferred("finish_case");return
	if stage=="forward" and observation.tick==release_tick+6:
		result.rejections.unknown_history=prop.preview_tick(-1)
		assert(prop.pause_playback()==OK)
		result.rejections.busy_command=prop.restart_playback()
		stage="pause"
	elif stage=="pause" and observation.transport=="paused":
		waits+=1
		if waits==5:
			# Neither arbitrary signal injection nor reverse notification owns physics.
			var fake: Dictionary=clock.markers[1].duplicate(true)
			fake.cycle=0;fake.time_s=clock.time_s
			clock.marker.emit(fake);fake.direction=-1;clock.marker_reversed.emit(fake)
			assert(prop.preview_tick(attach_tick+1)==OK);stage="preview-held"
	elif stage=="preview-held" and observation.transport=="preview":
		assert(prop.preview_tick(release_tick+3)==OK);stage="preview-free"
	elif stage=="preview-free" and observation.transport=="preview":
		assert(prop.preview_tick(attach_tick-1)==OK);stage="reverse-preview"
	elif stage=="reverse-preview" and observation.transport=="preview":
		assert(prop.resume_playback()==OK);stage="resume"
	elif stage=="resume" and observation.tick==int(item.end_tick):
		result.rejections.evicted_history=prop.preview_tick(0)
		result.retained_history_samples=prop.history.size()
		assert(prop.restart_playback()==OK);stage="replay"
	elif stage=="replay" and observation.session==1 and observation.tick==int(item.end_tick):
		complete=true;call_deferred("finish_case")

func finish_case() -> void:
	output.cases.append(result)
	world.queue_free();await process_frame
	case_index+=1
	if case_index<request.cases.size(): start_case()
	else:
		var file:=FileAccess.open(destination,FileAccess.WRITE)
		file.store_string(JSON.stringify(output));file.close();quit(0)
