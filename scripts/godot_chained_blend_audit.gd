extends "godot_cycle_blend_audit.gd"
var reentrant_rejections := 0

func audit() -> void:
	var args := OS.get_cmdline_user_args()
	var request = JSON.parse_string(FileAccess.get_file_as_string(args[0]))
	var result: Dictionary={"engine":Engine.get_version_info(),"cases":[]}
	for item in request.cases:
		var runs: Array=[]
		for extract in [false,true]:
			for stride in [0.5,11.0,100.0]:
				var placement := Transform3D(Basis(Vector3.UP,0.65),Vector3(-3,0.4,2))
				var donors: Dictionary={"a":instantiate(item.a,Transform3D.IDENTITY,true),"b":instantiate(item.b,Transform3D.IDENTITY,true)}
				var out := instantiate(item.a,placement,false)
				if not require(not out.is_empty() and not donors.a.is_empty() and not donors.b.is_empty(),"Import"): return
				var blend := Blend.new(); out.actor.add_child(blend)
				if not require(donors.a.adapter.seek_preview(item.initial_frame/30.0)==OK,"Initial phase"): return
				if not require(blend.bind_output(donors.a.adapter,out.skeleton,out.actor,"a",extract)==OK,"Bind"): return
				events=[]; reentrant_rejections=0
				blend.marker.connect(func(e):
					events.append(e)
					if blend.advance(0.0)==ERR_INVALID_PARAMETER: reentrant_rejections+=1)
				var accumulated := Transform3D.IDENTITY
				var stages: Array=[]
				for stage in item.stages:
					var before: Array=[]
					for bone in range(out.skeleton.get_bone_count()): before.append(matrix(out.skeleton.get_bone_global_pose(bone)))
					var before_motion: Transform3D=blend.root_motion_transform
					var event_start: int=events.size()
					if not require(blend.start_blend(donors[stage.target].adapter,stage.duration_frames/30.0,stage.target_frame/30.0,stage.target,stage.policy)==OK,"Chained start"): return
					if not require(blend.root_motion_transform==before_motion and events.size()==event_start,"Start changed root/events"): return
					for bone in range(out.skeleton.get_bone_count()):
						if not require(before[bone]==matrix(out.skeleton.get_bone_global_pose(bone)),"Start changed pose"): return
					var frames: Array=[]
					var cursor := 0.0
					while cursor < stage.total_frames:
						var destination: float=minf(cursor+stride,stage.total_frames)
						if not require(blend.advance((destination-cursor)/30.0)==OK,"Chained advance"): return
						accumulated=accumulated*blend.root_motion_delta
						if extract: out.actor.transform=placement*accumulated
						var bones: Array=[]
						for bone in range(out.skeleton.get_bone_count()): bones.append(matrix(out.skeleton.global_transform*out.skeleton.get_bone_global_pose(bone)))
						frames.append({"at_frame":destination,"bones":bones,"motion":matrix(blend.root_motion_transform),"accumulated":matrix(accumulated)})
						cursor=destination
					if not require(blend.incoming==null and blend.current_id==stage.target,"Handover did not finish"): return
					stages.append({"frames":frames,"events":events.slice(event_start),"start_preserved_state":true,"target_clock_s":blend.current.time_s})
				if not require(reentrant_rejections==events.size(),"Reentrant advance was accepted"): return
				var names: Array=[]
				for bone in range(out.skeleton.get_bone_count()): names.append(out.skeleton.get_bone_name(bone))
				runs.append({"extracted":extract,"stride":stride,"stages":stages,"bone_names":names,"placement":matrix(placement),"reentrant_rejections":reentrant_rejections})
				donors.a.actor.queue_free(); donors.b.actor.queue_free(); out.actor.queue_free()
				await process_frame
		result.cases.append({"id":item.id,"runs":runs})
	var file := FileAccess.open(args[1],FileAccess.WRITE); file.store_string(JSON.stringify(result)); file.close()
	quit(0)
