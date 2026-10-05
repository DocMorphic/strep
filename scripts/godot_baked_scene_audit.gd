extends SceneTree
const Loader = preload("godot_baked_scene_loader.gd")
const Roots = preload("godot_native_root_adapter.gd")
const Clock = preload("native_engine_clock.gd")
var destination := ""
var loaded := {}
var motion
var parent: Node3D
var boot: Node3D
var phase := "callbacks"
var report := {"schema":"strep-baked-scene-audit-v1","faults":[],"frames":[],"callbacks":[],"skipped_callbacks":[],"restart_callbacks":[],"boot_callbacks":[],"invalid_bindings_rejected":0,"no_binding_leaks":true,"collision_objects":0}

static func bits(value: float) -> String:
	var b := PackedByteArray(); b.resize(8); b.encode_double(0,value); return b.hex_encode()

static func matrix_bits(value: Transform3D) -> String:
	var b := PackedByteArray(); b.resize(128)
	for r in range(4):
		for c in range(4):
			var v: float = (1.0 if c==3 else 0.0) if r==3 else (value.origin[r] if c==3 else value.basis[c][r])
			b.encode_double((r*4+c)*8,v)
	return b.hex_encode()

func snapshot(player) -> Dictionary:
	var actors := {}; var objects := {}; var roots := {}; var deltas := {}
	for id in player.actors:
		var helper = player.actors[id]; var bones := {}
		for i in range(helper.skeleton.get_bone_count()): bones[str(helper.skeleton.get_bone_name(i))]=matrix_bits(helper.skeleton.global_transform*helper.skeleton.get_bone_global_pose(i))
		actors[id]=bones
		roots[id]=matrix_bits(helper.root_motion_transform); deltas[id]=matrix_bits(player.root_deltas[id])
	for id in player.props.objects: objects[id]=matrix_bits(player.props.objects[id].global_transform)
	return {"time_f64le":bits(player.pose_time_s),"actors":actors,"objects":objects,"root_motion":roots,"root_deltas":deltas}

func callback(event: Dictionary) -> void:
	var row := snapshot(motion); row.id=event.id; report[phase].append(row)

func finish(code: int) -> void:
	var file := FileAccess.open(destination,FileAccess.WRITE); file.store_string(JSON.stringify(report,"",true,true)); file.close()
	if motion!=null and motion.gameplay.is_connected(callback): motion.gameplay.disconnect(callback)
	motion=null; loaded.clear()
	if is_instance_valid(parent): parent.free()
	if is_instance_valid(boot): boot.free()
	quit(code)

func _initialize() -> void: call_deferred("begin")
func begin() -> void:
	var args := OS.get_cmdline_user_args(); destination=args[1]
	var request = JSON.parse_string(FileAccess.get_file_as_string(args[0])); report.request_sha256=FileAccess.get_sha256(args[0])
	var config: Dictionary = request.config; var queries := Clock.decode(request.clock,int(request.clock.count))
	parent=Node3D.new(); root.add_child(parent)
	for fault in ["asset","source-end","parent-scale","root","prop-name","rate","clock","placement","root-mode","end-policy","physics","approval"]:
		var bad: Dictionary = config.duplicate(true)
		match fault:
			"asset": bad.actors[0].asset.sha256="wrong"
			"source-end": bad.source_duration_s+=1.0
			"parent-scale": bad.parent_world_transform[0][0]=2.0
			"root": bad.actors[0].root_bone="Missing"
			"prop-name": bad.objects.names.append(bad.objects.names[0])
			"rate": bad.physics_fps=30
			"clock": bad.clock.bytes_hex="00"
			"placement": bad.actors[0].placement[3][0]=1.0
			"root-mode": bad.root_mode="extracted"
			"end-policy": bad.actor_end_policy="loop"
			"physics": bad.live_prop_physics=true
			"approval": bad.quality_approved=true
		var before := parent.get_child_count(); var rejected := Loader.load_scene(parent,request.folder,bad)
		if rejected.is_empty(): report.invalid_bindings_rejected+=1
		else: rejected.container.free(); rejected.clear()
		if parent.get_child_count()!=before: report.no_binding_leaks=false
	loaded=Loader.load_scene(parent,request.folder,config)
	if loaded.is_empty(): report.faults.append("Saved composed binding failed: "+Loader.last_error); finish(2); return
	motion=loaded.player; motion.gameplay.connect(callback); report.object_key_envelope_s=motion.props.animation.length
	for node in Roots.nodes(loaded.container):
		if node is CollisionObject3D: report.collision_objects+=1
	for time in queries:
		if not motion.advance_to(time).valid: report.faults.append("Shared advance failed"); finish(2); return
		report.frames.append(snapshot(motion))
	var count: int = report.callbacks.size()
	motion.seek_preview(0.0); motion.seek_preview(config.duration_s); report.preview_silent=report.callbacks.size()==count
	motion.seek_preview(0.0); motion.advance_to(config.duration_s); report.repeat_silent=report.callbacks.size()==count
	report.repeat_root_delta_identity=true
	for delta in motion.root_deltas.values():
		if delta!=Transform3D.IDENTITY: report.repeat_root_delta_identity=false
	report.backward_rejected=not motion.advance_to(0.0).valid
	report.invalid_time_rejected=not motion.advance_to(float(config.duration_s)+0.00001).valid and motion.seek_preview(-0.1)!=OK
	var world: Transform3D = loaded.container.global_transform; loaded.container.position.x+=1.0
	report.moved_parent_rejected=not motion.advance_to(config.duration_s).valid; loaded.container.global_transform=world
	motion.restart(); phase="skipped_callbacks"; motion.advance_to(config.duration_s)
	motion.restart(); phase="restart_callbacks"
	for time in queries: motion.advance_to(time)
	motion.gameplay.disconnect(callback); motion=null; loaded.container.free(); loaded.clear()
	var packed := load("res://baked-runtime-v1/scene.tscn") as PackedScene
	if packed==null: report.faults.append("Exported main scene missing"); finish(2); return
	boot=packed.instantiate(); root.add_child(boot); boot.set_process(false); report.boot_bound=boot.motion!=null
	if not report.boot_bound: report.faults.append("Exported main scene failed"); finish(2); return
	motion=boot.motion; phase="boot_callbacks"; motion.gameplay.connect(callback); motion.advance_to(config.duration_s); report.boot_frame=snapshot(motion)
	finish(0)
