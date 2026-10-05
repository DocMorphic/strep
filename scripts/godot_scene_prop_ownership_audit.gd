extends SceneTree
const Native = preload("godot_native_scene_player.gd")
const Owner = preload("godot_scene_prop_owner.gd")
const Body = preload("godot_scene_prop_body.gd")
const Observe = preload("godot_native_scene_observations.gd")
var request: Dictionary
var output := {"cases":[]}
var destination := ""
var case_index := 0
var world: Node3D
var motion
var ownership
var props: Dictionary = {}
var result: Dictionary = {}
var stage := "forward"
var waits := 0
var finishing := false

func serial(value: Variant) -> Variant:
	if value is Transform3D:
		return [[value.basis.x.x,value.basis.y.x,value.basis.z.x,value.origin.x],[value.basis.x.y,value.basis.y.y,value.basis.z.y,value.origin.y],[value.basis.x.z,value.basis.y.z,value.basis.z.z,value.origin.z],[0,0,0,1]]
	if value is Vector3: return [value.x,value.y,value.z]
	if value is Dictionary:
		var d := {}
		for k in value: d[k]=serial(value[k])
		return d
	if value is Array:
		var a: Array = []
		for item in value: a.append(serial(item))
		return a
	return value

func fail(reason: String) -> void:
	push_error(reason); quit(2)

func _initialize() -> void: call_deferred("begin")
func begin() -> void:
	var args := OS.get_cmdline_user_args()
	if args.size()!=2: fail("Request/output paths required"); return
	request=JSON.parse_string(FileAccess.get_file_as_string(args[0])); destination=args[1]
	output.engine=Engine.get_version_info(); output.backend=ProjectSettings.get_setting("physics/3d/physics_engine")
	Engine.physics_ticks_per_second=int(request.physics_fps)
	start_case()

func center(id: String,time: float) -> Vector3:
	var phase: float = max(0.0,time-0.2)
	return Vector3(-0.7,1.5,0)+Vector3(0.4,0.1,0)*phase if id=="P" else Vector3(0.7,1.5,0)+Vector3(-0.4,0.1,0)*phase

func actor(id: String,extract: bool) -> Dictionary:
	var node := Node3D.new(); node.name=id; world.add_child(node)
	var skeleton := Skeleton3D.new(); skeleton.name="Skeleton"; node.add_child(skeleton)
	for n in ["Root","Left","Right"]: skeleton.add_bone(n)
	skeleton.set_bone_parent(1,0); skeleton.set_bone_parent(2,0)
	for i in range(3): skeleton.set_bone_rest(i,Transform3D.IDENTITY)
	skeleton.set_bone_pose_position(1,Vector3(0.2,0,0)); skeleton.set_bone_pose_position(2,Vector3(-0.2,0,0))
	# Tiny procedural skinned triangle: native playback fixture, no character download.
	var arrays: Array = []; arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX]=PackedVector3Array([Vector3.ZERO,Vector3(0.01,0,0),Vector3(0,0.01,0)])
	arrays[Mesh.ARRAY_BONES]=PackedInt32Array([0,0,0,0,0,0,0,0,0,0,0,0])
	arrays[Mesh.ARRAY_WEIGHTS]=PackedFloat32Array([1,0,0,0,1,0,0,0,1,0,0,0])
	var mesh := ArrayMesh.new(); mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays)
	var instance := MeshInstance3D.new(); instance.mesh=mesh; instance.skin=Skin.new(); instance.skin.add_named_bind(&"Root",Transform3D.IDENTITY)
	node.add_child(instance); instance.skeleton=instance.get_path_to(skeleton)
	var player := AnimationPlayer.new(); player.name="AnimationPlayer"; node.add_child(player)
	var animation := Animation.new(); animation.length=2.0; animation.loop_mode=Animation.LOOP_NONE
	var position := animation.add_track(Animation.TYPE_POSITION_3D); animation.track_set_path(position,NodePath("Skeleton:Root"))
	var rotation := animation.add_track(Animation.TYPE_ROTATION_3D); animation.track_set_path(rotation,NodePath("Skeleton:Root"))
	var right := -1
	if id=="B": right=animation.add_track(Animation.TYPE_POSITION_3D); animation.track_set_path(right,NodePath("Skeleton:Right"))
	for f in range(61):
		var t := float(f)/30.0; var q := Quaternion(Vector3.UP,max(0.0,t-0.2)*0.3)
		animation.position_track_insert_key(position,t,center("P",t)); animation.rotation_track_insert_key(rotation,t,q)
		if right>=0: animation.position_track_insert_key(right,t,Basis(q).inverse()*(center("Q",t)-center("P",t))+Vector3(-0.2,0,0))
	var library := AnimationLibrary.new(); library.add_animation(&"clip",animation); player.add_animation_library(&"",library)
	return {"id":id,"player":player,"skeleton":skeleton,"actor":node,"clip":&"clip","root_bone":&"Root","extract":extract}

func grip(key: String,id: String) -> Transform3D:
	var binding: Dictionary = request.cases[case_index].plan.grips[key]
	var helper = motion.actors[binding.actor]
	var bone: int = helper.skeleton.find_bone("Left" if key.ends_with("L") else "Right")
	var offset := Transform3D(Basis.IDENTITY,Vector3(-0.2,0,0) if key.ends_with("L") else Vector3(0.2,0,0))
	var pose: Transform3D = helper.skeleton.global_transform*helper.skeleton.get_bone_global_pose(bone)*offset
	if request.cases[case_index].get("fault","")=="conflict" and key=="AR" and motion.pose_time_s>=0.3: pose.origin.x+=0.02
	if request.cases[case_index].get("fault","")=="provider-clock" and key=="AR" and motion.pose_time_s>=0.3: motion.seek_preview(0.0)
	return pose

func start_case() -> void:
	var item: Dictionary = request.cases[case_index]; world=Node3D.new(); root.add_child(world)
	var floor_body := StaticBody3D.new(); floor_body.set_meta("strep_collider_id","floor")
	var floor_shape := CollisionShape3D.new(); floor_shape.shape=WorldBoundaryShape3D.new(); floor_body.add_child(floor_shape); world.add_child(floor_body)
	motion=Native.new(); var entries: Array = [actor("A",false),actor("B",true)]
	if motion.bind(entries,null,&"",{},item.events)!=OK: fail("Native animated participants rejected"); return
	props.clear()
	var names: Array = ["Q","P"] if item.get("reverse_bodies",false) else ["P","Q"]
	for id in names:
		var body = Body.new(); body.name=id; body.mass=2.0; body.transform=Transform3D(Basis.IDENTITY,center(id,0.0))
		body.set_meta("strep_collider_id",id); body.continuous_cd=true; body.max_contacts_reported=16; body.contact_monitor=true
		body.linear_damp_mode=RigidBody3D.DAMP_MODE_REPLACE; body.angular_damp_mode=RigidBody3D.DAMP_MODE_REPLACE; body.linear_damp=0; body.angular_damp=0
		var material := PhysicsMaterial.new(); material.friction=0.6; body.physics_material_override=material
		var shape := CollisionShape3D.new()
		if id=="P":
			var cylinder := CylinderShape3D.new(); cylinder.radius=0.15; cylinder.height=0.4; shape.shape=cylinder
			body.inertia=Vector3(2*(3*0.15*0.15+0.4*0.4)/12,2*0.15*0.15/2,2*(3*0.15*0.15+0.4*0.4)/12)
		else:
			var sphere := SphereShape3D.new(); sphere.radius=0.15; shape.shape=sphere; body.inertia=Vector3.ONE*(0.4*2*0.15*0.15)
		body.add_child(shape); world.add_child(body); props[id]=body
	var providers := {}
	for key in item.plan.grips: providers[key]=func(object_id: String) -> Transform3D: return grip(key,object_id)
	var rejected := 0
	for fault in ["contract","membership","actor","clock","duplicate-prop"]:
		var bad: Dictionary = item.plan.duplicate(true)
		match fault:
			"contract": bad.source_events[0].timing_confirmed=false
			"membership": bad.groups[0].transitions[0].after=[]
			"actor": bad.grips.AL.actor="missing"
			"clock": bad.clock.bytes_hex="00"
			"duplicate-prop": bad.objects[1]=bad.objects[0]
		var owner = Owner.new()
		if owner.bind(motion,bad,props,providers,int(request.physics_fps),80)==OK: fail("Malformed ownership accepted"); return
		for body in props.values():
			if body.strep_manager!=null or body.custom_integrator: fail("Rejected plan mutated participants"); return
		rejected+=1
	ownership=Owner.new()
	if ownership.bind(motion,item.plan,props,providers,int(request.physics_fps),80)!=OK: fail("Shared ownership bind rejected"); return
	var other = Owner.new()
	if other.bind(motion,item.plan,props,providers,int(request.physics_fps),80)==OK: fail("Second clock owner accepted"); return
	result={"id":item.id,"records":[],"actions":[],"faults":[],"source_events":[],"malformed_rejected":rejected,"second_owner_rejected":true}; stage="forward"; waits=0; finishing=false
	result.installed_geometry={"P":{"schema":"strep-object-geometry-v1","shape":"cylinder","radius_m":props.P.get_child(0).shape.radius,"height_m":props.P.get_child(0).shape.height},"Q":{"schema":"strep-object-geometry-v1","shape":"sphere","radius_m":props.Q.get_child(0).shape.radius}}
	motion.gameplay.connect(func(event): result.source_events.append({"id":event.id,"time_s":event.time_s,"pose_time_s":motion.pose_time_s}))
	ownership.actions_applied.connect(func(actions): result.actions.append_array(serial(actions)))
	ownership.faulted.connect(func(reason): result.faults.append(reason); call_deferred("finish_case"))
	ownership.sampled.connect(on_sample)

func on_sample(record: Dictionary) -> void:
	if finishing: return
	var copy: Dictionary = serial(record); copy.scene=serial(Observe.snapshot(motion)); copy.history_size=ownership.history.size(); result.records.append(copy)
	var fault: String = request.cases[case_index].get("fault","")
	if fault=="outside" and record.tick==int(request.physics_fps*0.35): motion.seek_preview(0.0); return
	if fault=="missing-body" and record.tick==int(request.physics_fps*0.35): props.Q.strep_manager=null; return
	if not fault.is_empty(): return
	if stage=="forward" and record.tick==int(request.physics_fps*1.55):
		result.live_before_preview=copy; stage="paused"; assert(ownership.pause_playback()==OK)
	elif stage=="paused" and record.transport=="paused": stage="preview-old"; assert(ownership.preview_tick(record.tick-20)==OK)
	elif stage=="preview-old" and record.transport=="preview": stage="resume"; assert(ownership.resume_playback()==OK)
	elif stage=="resume" and record.command=="resume": stage="tail"; result.restored=copy
	elif stage=="tail" and record.tick==int(request.physics_fps*3.0):
		result.expired_preview_rejected=ownership.preview_tick(0)!=OK; stage="replay"; assert(ownership.restart_playback()==OK)
	elif stage=="replay" and record.session==1 and record.tick==int(request.physics_fps*1.4): call_deferred("finish_case")

func finish_case() -> void:
	if finishing: return
	finishing=true; output.cases.append(result); world.queue_free(); case_index+=1
	if case_index<request.cases.size():
		await process_frame
		start_case()
	else:
		var file := FileAccess.open(destination,FileAccess.WRITE); file.store_string(JSON.stringify(output)); file.close(); quit(0)
