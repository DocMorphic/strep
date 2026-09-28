extends SceneTree
const Adapter = preload("godot_cycle_adapter.gd")
var received: Array = []
func matrix(t: Transform3D) -> Array:
	return [[t.basis.x.x,t.basis.x.y,t.basis.x.z],[t.basis.y.x,t.basis.y.y,t.basis.y.z],[t.basis.z.x,t.basis.z.y,t.basis.z.z],[t.origin.x,t.origin.y,t.origin.z]]
func descendants(n: Node) -> Array:
	var found: Array=[n]
	for child in n.get_children(): found.append_array(descendants(child))
	return found
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
			assert(document.append_from_file(item.path,state)==OK)
			var actor := Node3D.new()
			root.add_child(actor)
			var initial := Transform3D(Basis(Vector3.UP,0.4),Vector3(2,0.3,-1))
			actor.transform=initial
			var model := document.generate_scene(state,30.0,false,false)
			actor.add_child(model)
			await process_frame
			var player: AnimationPlayer
			var skeleton: Skeleton3D
			for node in descendants(model):
				if node is AnimationPlayer: player=node
				if node is Skeleton3D: skeleton=node
			assert(player != null and skeleton != null)
			var selected := ""
			for name in player.get_animation_list():
				if name != "RESET": selected=name
			var adapter := Adapter.new()
			actor.add_child(adapter)
			adapter.marker.connect(func(e): received.append(e))
			var data = JSON.parse_string(FileAccess.get_file_as_string(item.metadata))
			var bad: Dictionary=data.duplicate(true)
			bad.glb_sha256="bad"
			assert(adapter.bind_cycle(player,skeleton,actor,selected,bad,item.path,extract) != OK)
			# Explicitly synthetic dispatch probes; never inserted in the user's runtime metadata.
			data.markers=item.probe_markers
			assert(adapter.bind_cycle(player,skeleton,actor,selected,data,item.path,extract)==OK)
			assert(adapter.bind_cycle(player,skeleton,actor,selected,data,item.path,extract)!=OK)
			var names: Array=[]
			for b in range(skeleton.get_bone_count()): names.append(skeleton.get_bone_name(b))
			for stride in [0.5,17.0,float(data.period_frames)*2.0+3.0]:
				actor.transform=initial
				received=[]
				assert(adapter.restart(true)==OK)
				var accumulated := Transform3D.IDENTITY
				var frames: Array=[]
				var cursor := 0.0
				while cursor < float(data.period_frames)*3.0:
					var next: float=minf(cursor+stride,float(data.period_frames)*3.0)
					assert(adapter.advance((next-cursor)/30.0)==OK)
					accumulated=accumulated*adapter.root_motion_delta
					if extract: actor.transform=initial*accumulated
					var poses: Array=[]
					for b in range(skeleton.get_bone_count()): poses.append(matrix(skeleton.global_transform*skeleton.get_bone_global_pose(b)))
					frames.append({"at_frame":next,"bones":poses,"motion":matrix(adapter.root_motion_transform),"accumulated_delta":matrix(accumulated)})
					cursor=next
				var prior: float=adapter.time_s
				assert(adapter.advance(-1.0)!=OK and adapter.advance(INF)!=OK and adapter.advance(adapter.period*1025)!=OK)
				assert(adapter.time_s==prior)
				var count := received.size()
				assert(adapter.advance(0.0)==OK and count==received.size())
				var events := received.duplicate(true)
				received=[]
				for seek in [0.0,adapter.period,adapter.period*2.3,adapter.period*3.0]: assert(adapter.seek_preview(seek)==OK)
				assert(received.is_empty())
				runs.append({"extracted":extract,"stride":stride,"bone_names":names,"frames":frames,"events":events,"silent_seek":true,"rejected_invalid_steps":true,"placement":matrix(initial)})
			actor.queue_free()
			await process_frame
		output.cases.append({"id":item.id,"runs":runs})
	var file := FileAccess.open(args[1],FileAccess.WRITE)
	file.store_string(JSON.stringify(output));file.close()
	quit(0)
