extends SceneTree
const Runtime = preload("godot_scene_prop_runtime.gd")
const Loader = preload("godot_native_scene_loader.gd")
const Tracks = preload("native_godot_tracks.gd")
const Observe = preload("godot_native_scene_observations.gd")
var result := {"records":[],"actions":[],"events":[],"faults":[],"malformed_rejected":0}
var destination := ""
var runtime
var stage := "forward"

class ParentListener extends Node3D:
	signal done(receipt: Dictionary)
	var receipt := {"events":[],"actions":0,"samples":0,"faults":[],"parent_ready":false,"floor_contact":false}
	static func bits(seconds: float) -> String:
		var bytes := PackedByteArray(); bytes.resize(8); bytes.encode_double(0,seconds); return bytes.hex_encode()
	func _ready() -> void:
		var boot = get_node("Strep")
		receipt.parent_ready=true
		if boot.motion==null: receipt.faults.append("Exported boot binding failed"); done.emit(receipt); return
		receipt.collision_settings=boot.runtime.collision_settings.duplicate(true)
		receipt.continuous_cd={}
		for id in boot.runtime.bodies: receipt.continuous_cd[id]=boot.runtime.bodies[id].continuous_cd
		boot.gameplay.connect(func(event): receipt.events.append({"id":event.id,"source_time_s":event.time_s,"pose_time_s":boot.motion.pose_time_s,"source_time_f64le":bits(event.time_s),"pose_time_f64le":bits(boot.motion.pose_time_s),"parent_ready":receipt.parent_ready}))
		boot.actions_applied.connect(func(actions): receipt.actions+=actions.size())
		boot.faulted.connect(func(reason): receipt.faults.append(reason); done.emit(receipt))
		boot.sampled.connect(func(record):
			receipt.samples+=1
			for prop in record.props.values():
				if "floor" in prop.contacts: receipt.floor_contact=true
			if record.tick>=3*Engine.physics_ticks_per_second:
				receipt.final_source_time_s=record.source_time_s; receipt.actors=boot.motion.actors.keys(); receipt.props=record.props.keys(); done.emit(receipt)
		)

func serial(value: Variant) -> Variant:
	if value is Transform3D: return [[value.basis.x.x,value.basis.y.x,value.basis.z.x,value.origin.x],[value.basis.x.y,value.basis.y.y,value.basis.z.y,value.origin.y],[value.basis.x.z,value.basis.y.z,value.basis.z.z,value.origin.z],[0,0,0,1]]
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

func fail(reason: String) -> void: push_error(reason); quit(2)
func _initialize() -> void: call_deferred("begin")
func begin() -> void:
	var args := OS.get_cmdline_user_args()
	if args.size()!=2: fail("Two fixture audit paths required"); return
	var request = JSON.parse_string(FileAccess.get_file_as_string(args[0])); destination=args[1]
	if request.get("mode")=="prepare": prepare(request); return
	if request.get("mode")=="boot":
		var floor_body := StaticBody3D.new(); floor_body.set_meta("strep_collider_id","floor")
		var collision := CollisionShape3D.new(); collision.shape=WorldBoundaryShape3D.new(); floor_body.add_child(collision); root.add_child(floor_body)
		var scene := load("res://ownership-v1/scene.tscn") as PackedScene
		if scene==null: fail("Packaged main scene failed to load"); return
		var parent := ParentListener.new(); parent.position=Vector3(0,2,0); parent.add_child(scene.instantiate())
		parent.done.connect(func(receipt):
			var file := FileAccess.open(destination,FileAccess.WRITE); file.store_string(JSON.stringify(receipt)); file.close(); quit(0)
		)
		root.add_child(parent); return
	var config: Dictionary = request.config
	var parent := Node3D.new(); parent.transform=Loader.matrix(request.placement); root.add_child(parent)
	var floor_body := StaticBody3D.new(); floor_body.set_meta("strep_collider_id","floor")
	var collision := CollisionShape3D.new(); collision.shape=WorldBoundaryShape3D.new(); floor_body.add_child(collision); root.add_child(floor_body)
	var child_count := parent.get_child_count()
	var faults: Array = ["offset","bone","node","geometry","inertia","object-mode","source-hash","event-clock","rate","mass"]
	if config.has("collision_profile"): faults.append_array(["collision-name","collision-value","collision-extra","collision-project"])
	if config.has("physical_timing"): faults.append_array(["timing-clock","timing-group","timing-limit","timing-approved","timing-population","timing-count","timing-decision"])
	for fault in faults:
		var bad: Dictionary = config.duplicate(true); var key: String = bad.grip_bindings.keys()[0]; var prop: String = bad.props.keys()[0]
		var setting := "physics/jolt_physics_3d/simulation/continuous_cd_movement_threshold"
		var saved_setting = ProjectSettings.get_setting(setting)
		match fault:
			"offset": bad.grip_bindings[key].prop_offsets[prop][0][0]=2
			"bone": bad.grip_bindings[key].bone="ghost"
			"node": bad.grip_bindings[key].joint_node=99999
			"geometry": bad.props[prop].geometry.radius_m=2
			"inertia": bad.props[prop].inertia_diagonal[0]+=1
			"object-mode": bad.object_modes[prop]="authored"
			"source-hash": bad.grip_bindings[key].character_glb_sha256="wrong"
			"event-clock": bad.ownership.clock.bytes_hex="00"
			"rate": bad.physics_fps=90
			"mass": bad.props[prop].physics.mass_kg=false
			"timing-clock": bad.physical_timing.application_clock.bytes_hex="00"
			"timing-group": bad.physical_timing.groups[0].tick+=1
			"timing-limit": bad.physical_timing.maximum_delay_f64le="0000000000000000"
			"timing-approved": bad.physical_timing.quality_approved=true
			"timing-population": bad.physical_timing.groups.pop_back()
			"timing-count": bad.physical_timing.application_clock.count=true
			"timing-decision": bad.physical_timing.contract_satisfied=false
			"collision-name": bad.collision_profile.name="unknown"
			"collision-value": bad.collision_profile.settings[setting]=false
			"collision-extra": bad.collision_profile.settings["undocumented"]=1
			"collision-project": ProjectSettings.set_setting(setting,0.04)
		var candidate = Runtime.new()
		var accepted: bool = candidate.bind(parent,request.asset_folder,bad)==OK
		ProjectSettings.set_setting(setting,saved_setting)
		if accepted or parent.get_child_count()!=child_count: fail("Malformed staged prop runtime leaked participants: "+fault); return
		result.malformed_rejected+=1
	runtime=Runtime.new()
	if runtime.bind(parent,request.asset_folder,config)!=OK: fail("Packaged actual actors/props rejected: "+runtime.last_error); return
	result.engine=Engine.get_version_info(); result.mode=config.object_modes; result.extraction={}
	result.collision_settings=runtime.collision_settings.duplicate(true); result.continuous_cd={}
	for id in runtime.bodies: result.continuous_cd[id]=runtime.bodies[id].continuous_cd
	for id in runtime.loaded.player.actors: result.extraction[id]=runtime.loaded.player.actors[id].extracted
	result.visibility={}
	for id in runtime.loaded.objects: result.visibility[id]=runtime.loaded.objects[id].visible
	runtime.loaded.player.gameplay.connect(func(event): result.events.append({"id":event.id,"source_time_s":event.time_s,"pose_time_s":runtime.loaded.player.pose_time_s,"source_time_f64le":ParentListener.bits(event.time_s),"pose_time_f64le":ParentListener.bits(runtime.loaded.player.pose_time_s)}))
	runtime.owner.actions_applied.connect(func(actions): result.actions.append_array(serial(actions)))
	runtime.owner.faulted.connect(func(reason): result.faults.append(reason); fail(reason))
	runtime.owner.sampled.connect(on_sample)

func prepare(request: Dictionary) -> void:
	var parent := Node3D.new(); root.add_child(parent)
	for item in request.actors:
		var model := Loader.import_model(item.asset_path,int(item.animation_index))
		if model==null: fail("Fixture GLB actor import failed"); return
		parent.add_child(model); var players: Array = []; var skeletons: Array = []
		for node in preload("godot_native_root_adapter.gd").nodes(model):
			if node is AnimationPlayer: players.append(node)
			if node is Skeleton3D: skeletons.append(node)
		if players.size()!=1 or skeletons.size()!=1 or Tracks.install(players[0],skeletons[0],item.payload,item.resource_path)!=OK: fail("Fixture native actor save failed"); return
		model.free()
	var item: Dictionary = request.objects
	var model := Loader.import_model(item.asset_path,0)
	if model==null: fail("Fixture GLB object import failed"); return
	parent.add_child(model); var player: AnimationPlayer = null; var meshes := {}
	for node in preload("godot_native_root_adapter.gd").nodes(model):
		if node is AnimationPlayer: player=node
		if node is MeshInstance3D: meshes[str(node.name)]=node
	if player==null: fail("Fixture object player absent"); return
	var animation := Animation.new(); animation.length=item.duration_s; animation.loop_mode=Animation.LOOP_NONE
	var base := player.get_node(player.root_node)
	for c in item.channels:
		if not meshes.has(c.node_name): fail("Fixture object channel missing"); return
		var kinds := {"translation":Animation.TYPE_POSITION_3D,"rotation":Animation.TYPE_ROTATION_3D,"scale":Animation.TYPE_SCALE_3D}
		var track := animation.add_track(kinds[c.path]); animation.track_set_path(track,base.get_path_to(meshes[c.node_name])); animation.track_set_interpolation_type(track,Animation.INTERPOLATION_LINEAR)
		for i in range(c.times_s.size()):
			var v: Array = c.values[i]; var t: float = c.times_s[i]
			if c.path=="rotation": animation.rotation_track_insert_key(track,t,Quaternion(v[0],v[1],v[2],v[3]).normalized())
			elif c.path=="translation": animation.position_track_insert_key(track,t,Vector3(v[0],v[1],v[2]))
			else: animation.scale_track_insert_key(track,t,Vector3(v[0],v[1],v[2]))
	if ResourceSaver.save(animation,item.resource_path)!=OK: fail("Fixture native object save failed"); return
	var file := FileAccess.open(destination,FileAccess.WRITE); file.store_string(JSON.stringify({"prepared":true})); file.close(); quit(0)

func on_sample(record: Dictionary) -> void:
	var copy: Dictionary = serial(record); copy.scene=Observe.snapshot(runtime.loaded.player); result.records.append(copy)
	var rate: int = runtime.config.physics_fps
	if stage=="forward" and record.tick==int(rate*1.55): stage="pause"; assert(runtime.owner.pause_playback()==OK)
	elif stage=="pause" and record.transport=="paused": stage="preview"; assert(runtime.owner.preview_tick(record.tick-20)==OK)
	elif stage=="preview" and record.transport=="preview": stage="resume"; assert(runtime.owner.resume_playback()==OK)
	elif stage=="resume" and record.command=="resume": stage="tail"
	elif stage=="tail" and record.tick==int(rate*3.0): stage="restart"; assert(runtime.owner.restart_playback()==OK)
	elif stage=="restart" and record.session==1 and record.tick==int(rate*1.4):
		var file := FileAccess.open(destination,FileAccess.WRITE); file.store_string(JSON.stringify(result)); file.close(); quit(0)
