extends SceneTree
const Adapter = preload("godot_cycle_adapter.gd")
var forward_events: Array=[]
var reverse_events: Array=[]

func matrix(t: Transform3D) -> Array:
	return [[t.basis.x.x,t.basis.x.y,t.basis.x.z],[t.basis.y.x,t.basis.y.y,t.basis.y.z],[t.basis.z.x,t.basis.z.y,t.basis.z.z],[t.origin.x,t.origin.y,t.origin.z]]

func descendants(n: Node) -> Array:
	var found: Array=[n]
	for child in n.get_children(): found.append_array(descendants(child))
	return found

func require(ok: bool, message: String) -> bool:
	if not ok:
		push_error(message)
		quit(1)
	return ok

func _initialize() -> void: call_deferred("audit")

func audit() -> void:
	var args := OS.get_cmdline_user_args()
	var request = JSON.parse_string(FileAccess.get_file_as_string(args[0]))
	var output: Dictionary={"engine":Engine.get_version_info(),"cases":[]}
	for item in request.cases:
		var runs: Array=[]
		for extract in [false,true]:
			var document := GLTFDocument.new()
			var state := GLTFState.new()
			if not require(document.append_from_file(item.path,state)==OK,"GLB import"): return
			var actor := Node3D.new()
			root.add_child(actor)
			var placement := Transform3D(Basis(Vector3.UP,0.4),Vector3(2,0.3,-1))
			actor.transform=placement
			var model := document.generate_scene(state,30.0,false,false)
			actor.add_child(model)
			await process_frame
			var player: AnimationPlayer
			var skeleton: Skeleton3D
			for node in descendants(model):
				if node is AnimationPlayer: player=node
				if node is Skeleton3D: skeleton=node
			if not require(player!=null and skeleton!=null,"Missing player/skeleton"): return
			var selected := ""
			for name in player.get_animation_list():
				if name!="RESET": selected=name
			var adapter := Adapter.new()
			actor.add_child(adapter)
			adapter.marker.connect(func(e): forward_events.append(e))
			adapter.marker_reversed.connect(func(e): reverse_events.append(e))
			var data = JSON.parse_string(FileAccess.get_file_as_string(item.metadata))
			data.markers=item.probe_markers
			if not require(adapter.bind_cycle(player,skeleton,actor,selected,data,item.path,extract)==OK,"Bind"): return
			var names: Array=[]
			for b in range(skeleton.get_bone_count()): names.append(skeleton.get_bone_name(b))
			for scenario in item.scenarios:
				actor.transform=placement
				forward_events=[]; reverse_events=[]
				if not require(adapter.seek_preview(scenario.start_frame/30.0)==OK,"Initial seek"): return
				if not require(forward_events.is_empty() and reverse_events.is_empty(),"Seek emitted an event"): return
				var accumulated: Transform3D=adapter.root_motion_transform
				if extract: actor.transform=placement*accumulated
				var frames: Array=[]
				var cursor: float=scenario.start_frame
				for destination in scenario.destinations:
					var step: float=destination-cursor
					# At the explicit timeline endpoint consume the actual remaining
					# cursor, not an independently rounded sum of earlier durations.
					var reverse_duration: float=adapter.time_s if destination==0.0 else -step/30.0
					var error: Error=adapter.rewind(reverse_duration,scenario.notify_reverse) if step<0 else adapter.advance(step/30.0)
					if not require(error==OK,"Traversal rejected: "+str([item.id,scenario.id,cursor,destination,adapter.time_s,adapter.time_correction])): return
					accumulated=accumulated*adapter.root_motion_delta
					if extract: actor.transform=placement*accumulated
					var poses: Array=[]
					for b in range(skeleton.get_bone_count()): poses.append(matrix(skeleton.global_transform*skeleton.get_bone_global_pose(b)))
					frames.append({"at_frame":destination,"clock_s":adapter.time_s,"bones":poses,"motion":matrix(adapter.root_motion_transform),"accumulated_delta":matrix(accumulated)})
					cursor=destination
				var prior: Array=[adapter.time_s,adapter.time_correction,matrix(adapter.root_motion_transform),matrix(adapter.root_motion_delta)]
				var event_count: int=forward_events.size()+reverse_events.size()
				for bad in [-1.0,INF,NAN,adapter.period*1025.0,adapter.time_s+adapter.period]:
					if not require(adapter.rewind(bad,true)!=OK,"Invalid rewind accepted"): return
					if not require(prior==[adapter.time_s,adapter.time_correction,matrix(adapter.root_motion_transform),matrix(adapter.root_motion_delta)],"Invalid rewind mutated state"): return
				if not require(event_count==forward_events.size()+reverse_events.size(),"Invalid rewind emitted event"): return
				if not require(adapter.rewind(0.0,true)==OK and adapter.root_motion_delta==Transform3D.IDENTITY,"Zero rewind"): return
				if not require(event_count==forward_events.size()+reverse_events.size(),"Zero rewind emitted event"): return
				runs.append({"scenario":scenario.id,"extracted":extract,"bone_names":names,"frames":frames,"forward_events":forward_events.duplicate(true),"reverse_events":reverse_events.duplicate(true),"placement":matrix(placement),"invalid_rewind_preserves_state":true})
			actor.queue_free()
			await process_frame
		output.cases.append({"id":item.id,"runs":runs})
	var file := FileAccess.open(args[1],FileAccess.WRITE)
	file.store_string(JSON.stringify(output));file.close()
	quit(0)
