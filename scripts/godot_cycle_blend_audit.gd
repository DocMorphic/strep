extends SceneTree
const Cycle = preload("godot_cycle_adapter.gd")
const Blend = preload("godot_cycle_blend.gd")
var events: Array=[]

func matrix(t: Transform3D) -> Array:
	return [[t.basis.x.x,t.basis.x.y,t.basis.x.z],[t.basis.y.x,t.basis.y.y,t.basis.y.z],[t.basis.z.x,t.basis.z.y,t.basis.z.z],[t.origin.x,t.origin.y,t.origin.z]]

func descendants(n: Node) -> Array:
	var found: Array=[n]
	for child in n.get_children(): found.append_array(descendants(child))
	return found

func require(ok: bool, message: String) -> bool:
	if not ok:
		push_error(message); quit(1)
	return ok

func instantiate(item: Dictionary, placement: Transform3D, donor: bool) -> Dictionary:
	var doc := GLTFDocument.new()
	var state := GLTFState.new()
	if doc.append_from_file(item.path,state) != OK: return {}
	var actor := Node3D.new(); root.add_child(actor); actor.transform=placement
	var model := doc.generate_scene(state,30.0,false,false); actor.add_child(model)
	var player: AnimationPlayer
	var skeleton: Skeleton3D
	for node in descendants(model):
		if node is AnimationPlayer: player=node
		if node is Skeleton3D: skeleton=node
	if player == null or skeleton == null: return {}
	var selected := ""
	for name in player.get_animation_list():
		if name != "RESET": selected=name
	var adapter := Cycle.new(); actor.add_child(adapter)
	if donor:
		var data = JSON.parse_string(FileAccess.get_file_as_string(item.metadata))
		data.markers=item.probe_markers
		if adapter.bind_cycle(player,skeleton,actor,selected,data,item.path,false) != OK: return {}
		actor.visible=false
	else:
		player.stop(); player.callback_mode_process=AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_MANUAL
	return {"actor":actor,"skeleton":skeleton,"adapter":adapter}

func _initialize() -> void: call_deferred("audit")

func audit() -> void:
	var args := OS.get_cmdline_user_args()
	var request = JSON.parse_string(FileAccess.get_file_as_string(args[0]))
	var result: Dictionary={"engine":Engine.get_version_info(),"cases":[]}
	for item in request.cases:
		var runs: Array=[]
		var incompatible := instantiate(item.incompatible,Transform3D.IDENTITY,true)
		if not require(not incompatible.is_empty(),"Incompatible fixture import"): return
		for extract in [false,true]:
			for event_policy in ["dominant","incoming","silent"]:
				for stride in [0.5,7.0,90.0]:
					var placement := Transform3D(Basis(Vector3.UP,0.4),Vector3(2,0.3,-1))
					var a := instantiate(item.a,Transform3D.IDENTITY,true)
					var b := instantiate(item.b,Transform3D.IDENTITY,true)
					var out := instantiate(item.a,placement,false)
					if not require(not a.is_empty() and not b.is_empty() and not out.is_empty(),"Import"): return
					var blend := Blend.new(); out.actor.add_child(blend)
					if not require(a.adapter.seek_preview(item.start_a/30.0)==OK,"Start A"): return
					if not require(blend.bind_output(a.adapter,out.skeleton,out.actor,"a",extract)==OK,"Bind output"): return
					var before: Array=[matrix(blend.root_motion_transform),matrix(out.skeleton.get_bone_global_pose(a.adapter.root_bone))]
					for bad in [0.0,-1.0,NAN,INF]:
						if not require(blend.start_blend(b.adapter,bad,item.start_b/30.0,"b",event_policy)!=OK,"Bad duration accepted"): return
					if not require(blend.start_blend(a.adapter,1.0,0.0,"a",event_policy)!=OK,"Same donor accepted"): return
					if not require(blend.start_blend(incompatible.adapter,1.0,0.0,"wrong_rig",event_policy)!=OK,"Incompatible rig accepted"): return
					if not require(blend.start_blend(b.adapter,1.0,0.0,"b","unknown")!=OK,"Bad event policy accepted"): return
					if not require(blend.start_blend(b.adapter,item.duration_frames/30.0,item.start_b/30.0,"b",event_policy)==OK,"Start blend"): return
					if not require(before==[matrix(blend.root_motion_transform),matrix(out.skeleton.get_bone_global_pose(a.adapter.root_bone))],"Start blend discontinuity"): return
					if not require(blend.start_blend(b.adapter,1.0,0.0,"b",event_policy)!=OK,"Active blend replaced"): return
					events=[]; blend.marker.connect(func(e): events.append(e))
					var clock := 0.0
					var accumulated := Transform3D.IDENTITY
					var frames: Array=[]
					while clock < item.total_frames:
						var destination: float=minf(clock+stride,item.total_frames)
						if not require(blend.advance((destination-clock)/30.0)==OK,"Advance"): return
						accumulated=accumulated*blend.root_motion_delta
						if extract: out.actor.transform=placement*accumulated
						var bones: Array=[]
						for j in range(out.skeleton.get_bone_count()): bones.append(matrix(out.skeleton.global_transform*out.skeleton.get_bone_global_pose(j)))
						frames.append({"at_frame":destination,"bones":bones,"motion":matrix(blend.root_motion_transform),"accumulated":matrix(accumulated)})
						clock=destination
					var preserved: Array=[blend.current.time_s,matrix(blend.root_motion_transform),matrix(blend.root_motion_delta),events.size()]
					for bad in [-1.0,NAN,INF,blend.current.period*1025.0]:
						if not require(blend.advance(bad)!=OK,"Bad advance accepted"): return
						if not require(preserved==[blend.current.time_s,matrix(blend.root_motion_transform),matrix(blend.root_motion_delta),events.size()],"Bad advance changed state"): return
					if not require(blend.advance(0.0)==OK and blend.root_motion_delta==Transform3D.IDENTITY and events.size()==preserved[3],"Zero step"): return
					var names: Array=[]
					for j in range(out.skeleton.get_bone_count()): names.append(out.skeleton.get_bone_name(j))
					runs.append({"extracted":extract,"policy":event_policy,"stride":stride,"frames":frames,"events":events.duplicate(true),"bone_names":names,"placement":matrix(placement),"invalid_requests_preserve_state":true})
					a.actor.queue_free(); b.actor.queue_free(); out.actor.queue_free()
					await process_frame
		result.cases.append({"id":item.id,"runs":runs})
		incompatible.actor.queue_free()
	var file := FileAccess.open(args[1],FileAccess.WRITE); file.store_string(JSON.stringify(result)); file.close()
	quit(0)
