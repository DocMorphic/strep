extends SceneTree
const Clock = preload("godot_scene_clock.gd")
var clock: Node
var result: Dictionary
var stage := "setup"
var active := false

func matrix(t: Transform3D) -> Array:
	var b:=t.basis;var p:=t.origin
	return [[b.x.x,b.y.x,b.z.x,p.x],[b.x.y,b.y.y,b.z.y,p.y],[b.x.z,b.y.z,b.z.z,p.z],[0,0,0,1]]

func capture() -> Dictionary:
	var actors: Dictionary={};var objects: Dictionary={}
	for id in clock.actors:
		var s: Skeleton3D=clock.actors[id].skeleton;var bones: Array=[]
		for bone in range(s.get_bone_count()): bones.append(matrix(s.global_transform*s.get_bone_global_pose(bone)))
		actors[id]=bones
	for id in clock.objects: objects[id]=matrix(clock.objects[id].global_transform)
	return {"stage":stage,"time_s":clock.time_s,"actors":actors,"objects":objects}

func on_sample(_seconds: float) -> void:
	if active: result.records.append(capture())

func on_marker(event: Dictionary, reverse: bool) -> void:
	var entry: Dictionary=event.duplicate(true);entry.observed=capture()
	if reverse: result.reverse.append(entry)
	else: result.forward.append(entry)
	result.reentrant_errors.append(clock.advance(0.1))

func _initialize() -> void: call_deferred("run")

func run() -> void:
	var args:=OS.get_cmdline_user_args();var request=JSON.parse_string(FileAccess.get_file_as_string(args[0]))
	Engine.physics_ticks_per_second=60
	var output: Dictionary={"engine":Engine.get_version_info(),"cases":[],"controls":[]}
	for item in request.cases:
		var parent:=Node3D.new();parent.transform=Transform3D(Basis(Vector3.UP,-0.3),Vector3(-1,0.2,2));root.add_child(parent)
		clock=Clock.new();root.add_child(clock)
		var error: Error=clock.bind_package(item.folder,parent)
		if error!=OK: push_error(clock.last_error);quit(2);return
		result={"id":item.id,"records":[],"forward":[],"reverse":[],"reentrant_errors":[],"bones":{},"finished":0}
		for id in clock.actors:
			var s: Skeleton3D=clock.actors[id].skeleton;var names: Array=[]
			for bone in range(s.get_bone_count()): names.append(s.get_bone_name(bone))
			result.bones[id]=names
		clock.sampled.connect(on_sample)
		clock.marker.connect(func(e):on_marker(e,false));clock.marker_reversed.connect(func(e):on_marker(e,true))
		clock.finished.connect(func():result.finished+=1)
		stage="forward";active=true;clock.restart(true)
		for tick in range(int(item.frames)*2): assert(clock.advance(1.0/60)==OK)
		var count: int=result.forward.size()
		stage="terminal-hold";clock.advance(1.0)
		result.no_terminal_repeat=result.forward.size()==count and result.finished==1
		stage="reverse"
		while clock.time_s>0: assert(clock.rewind(17.0/30,true)==OK)
		var reverse_count: int=result.reverse.size()
		stage="silent-preview";clock.seek_preview(clock.duration_s*0.71);clock.seek_preview(0.0)
		result.silent_preview=result.forward.size()==count and result.reverse.size()==reverse_count
		result.invalid=[clock.seek_preview(-1),clock.seek_preview(clock.duration_s+1),clock.advance(-1),clock.play(0),clock.play(5)]
		result.invalid_unchanged=clock.time_s==0.0
		stage="automatic-forward";assert(clock.play(1)==OK)
		for tick in range(14): await physics_frame
		clock.pause();var paused: float=clock.time_s;stage="paused"
		for tick in range(4): await physics_frame
		result.paused_time_unchanged=clock.time_s==paused
		stage="setup";clock.seek_preview(clock.duration_s);stage="automatic-reverse";clock.play(-2,false)
		for tick in range(14): await physics_frame
		clock.pause()
		result.automatic_reverse_silent=result.reverse.size()==reverse_count
		active=false
		assert(clock.unload()==OK);await process_frame
		result.unloaded=not clock.bound and parent.get_child_count()==0
		output.cases.append(result);clock.queue_free();parent.queue_free();await process_frame
	for item in request.controls:
		var parent:=Node3D.new();root.add_child(parent);var probe:=Clock.new();root.add_child(probe)
		var error: Error=probe.bind_package(item.folder,parent)
		output.controls.append({"id":item.id,"error":error,"reason":probe.last_error,"bound":probe.bound,"children":parent.get_child_count()})
		probe.queue_free();parent.queue_free();await process_frame
	var file:=FileAccess.open(args[1],FileAccess.WRITE);file.store_string(JSON.stringify(output));file.close();quit(0)
