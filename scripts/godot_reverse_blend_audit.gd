extends "godot_cycle_blend_audit.gd"
var reverse_events: Array=[]
var rejected_callbacks := 0

func audit() -> void:
	var args := OS.get_cmdline_user_args()
	var request = JSON.parse_string(FileAccess.get_file_as_string(args[0]))
	var result: Dictionary={"engine":Engine.get_version_info(),"cases":[]}
	for item in request.cases:
		var runs: Array=[]
		for extract in [false,true]:
			for event_policy in ["dominant","incoming","silent"]:
				for notify in [false,true]:
					for stride in [11.0,100.0]:
						for clock_unit in ["frames","seconds"]:
							var placement := Transform3D(Basis(Vector3.UP,0.4),Vector3(2,0.3,-1))
							var a := instantiate(item.a,Transform3D.IDENTITY,true)
							var b := instantiate(item.b,Transform3D.IDENTITY,true)
							var out := instantiate(item.a,placement,false)
							if not require(not a.is_empty() and not b.is_empty() and not out.is_empty(),"Import"): return
							var blend := Blend.new(); out.actor.add_child(blend)
							if not require(a.adapter.seek_preview(item.start_a/30.0)==OK,"Start phase"): return
							if not require(blend.bind_output(a.adapter,out.skeleton,out.actor,"a",extract)==OK,"Bind"): return
							if not require(blend.start_blend(b.adapter,item.duration_frames/30.0,item.start_b/30.0,"b",event_policy)==OK,"Start blend"): return
							events=[]; reverse_events=[]; rejected_callbacks=0
							blend.marker.connect(func(e): events.append(e))
							blend.marker_reversed.connect(func(e):
								reverse_events.append(e)
								if blend.rewind(0.0)==ERR_INVALID_PARAMETER and blend.advance(0.0)==ERR_INVALID_PARAMETER and blend.start_blend(a.adapter,1.0,0.0,"a","dominant")==ERR_INVALID_PARAMETER: rejected_callbacks+=1)
							var cursor := 0.0
							var accumulated := Transform3D.IDENTITY
							var stages: Array=[]
							for target in item.destinations if clock_unit=="frames" else item.seconds_destinations:
								var frames: Array=[]
								var reverse: bool=target < cursor
								var before_forward: int=events.size(); var before_reverse: int=reverse_events.size()
								while cursor != target:
									var destination: float=maxf(cursor-stride,target) if reverse else minf(cursor+stride,target)
									var seconds: float=absf(destination-cursor)/30.0
									# At the explicit retained-history boundary consume the exposed cursor.
									if reverse and destination==0.0: seconds=blend.elapsed_frames/30.0
									var status: int
									if clock_unit=="frames": status=blend.rewind_frames(absf(destination-cursor),notify) if reverse else blend.advance_frames(absf(destination-cursor))
									else: status=blend.rewind(seconds,notify) if reverse else blend.advance(seconds)
									if not require(status==OK,"Mixed advance/rewind"): return
									accumulated=accumulated*blend.root_motion_delta
									if extract: out.actor.transform=placement*accumulated
									var bones: Array=[]
									for bone in range(out.skeleton.get_bone_count()): bones.append(matrix(out.skeleton.global_transform*out.skeleton.get_bone_global_pose(bone)))
									frames.append({"at_frame":destination,"bones":bones,"motion":matrix(blend.root_motion_transform),"accumulated":matrix(accumulated)})
									cursor=destination
								var preserved: Array=[a.adapter.time_s,b.adapter.time_s,matrix(blend.root_motion_transform),matrix(blend.root_motion_delta),events.size(),reverse_events.size(),blend.current_id,blend.incoming_id]
								for bad in [-1.0,NAN,INF,(cursor+1.0)/30.0]:
									if not require(blend.rewind(bad,true)!=OK,"Invalid rewind accepted"): return
									if not require(preserved==[a.adapter.time_s,b.adapter.time_s,matrix(blend.root_motion_transform),matrix(blend.root_motion_delta),events.size(),reverse_events.size(),blend.current_id,blend.incoming_id],"Invalid rewind mutated state"): return
								if not require(blend.rewind(0.0,true)==OK and blend.root_motion_delta==Transform3D.IDENTITY,"Zero rewind"): return
								stages.append({"frames":frames,"forward_events":events.slice(before_forward),"reverse_events":reverse_events.slice(before_reverse)})
							var names: Array=[]
							for bone in range(out.skeleton.get_bone_count()): names.append(out.skeleton.get_bone_name(bone))
							runs.append({"clock_unit":clock_unit,"extracted":extract,"policy":event_policy,"notify":notify,"stride":stride,"stages":stages,"bone_names":names,"placement":matrix(placement),"reentrant_rejections":rejected_callbacks,"invalid_requests_preserve_state":true})
							a.actor.queue_free(); b.actor.queue_free(); out.actor.queue_free()
							await process_frame
		result.cases.append({"id":item.id,"runs":runs})
	var file := FileAccess.open(args[1],FileAccess.WRITE); file.store_string(JSON.stringify(result)); file.close()
	quit(0)
