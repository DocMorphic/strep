extends Node
## Two hidden cycle donors, one output skeleton; retain the latest transition.
## Root alignment preserves the outgoing pelvis pose at transition start.
signal marker(event: Dictionary)
signal marker_reversed(event: Dictionary)
var current: Node
var incoming: Node
var skeleton: Skeleton3D
var space: Node3D
var anchor := Transform3D.IDENTITY
var alignment := Transform3D.IDENTITY
var incoming_alignment := Transform3D.IDENTITY
var root_motion_transform := Transform3D.IDENTITY
var root_motion_delta := Transform3D.IDENTITY
var extracted := false
var elapsed := 0.0
var duration := 0.0
var outgoing_start := 0.0
var incoming_start := 0.0
var policy := "dominant"
var current_id := ""
var incoming_id := ""
var pending: Array = []
var busy := false
var retained: Dictionary = {}
var elapsed_frames := 0.0
var frame_correction := 0.0

func compatible(donor: Node, output: Skeleton3D) -> bool:
	if donor == null or not donor.get("bound") or donor.get("extracted") or donor.skeleton == output: return false
	var source: Skeleton3D = donor.skeleton
	if source.get_bone_count() != output.get_bone_count(): return false
	for b in range(output.get_bone_count()):
		if source.get_bone_name(b) != output.get_bone_name(b) or source.get_bone_parent(b) != output.get_bone_parent(b): return false
		if not source.get_bone_rest(b).is_equal_approx(output.get_bone_rest(b)): return false
	return true

func root_pose(donor: Node) -> Transform3D:
	return donor.root_motion_transform * donor.anchor

func capture(event: Dictionary, donor: Node) -> void:
	pending.append({"event":event.duplicate(true), "donor":donor})

func connect_donor(donor: Node) -> void:
	var callback := capture.bind(donor)
	if not donor.marker.is_connected(callback): donor.marker.connect(callback)
	if not donor.marker_reversed.is_connected(callback): donor.marker_reversed.connect(callback)

func bind_output(donor: Node, output: Skeleton3D, actor: Node3D, source_id: String, extract: bool = false) -> Error:
	if current != null or output == null or actor == null or not actor.is_ancestor_of(output) or source_id.is_empty() or not compatible(donor, output): return ERR_INVALID_PARAMETER
	current=donor; skeleton=output; space=actor; current_id=source_id; extracted=extract
	anchor=root_pose(current); connect_donor(current); apply_pose(0.0)
	return OK

func start_blend(donor: Node, seconds: float, source_time: float, source_id: String, event_policy: String) -> Error:
	if busy or current == null or incoming != null or donor == current or not compatible(donor, skeleton): return ERR_INVALID_PARAMETER
	if donor.root_bone != current.root_bone or source_id.is_empty() or source_id == current_id: return ERR_INVALID_PARAMETER
	if event_policy not in ["dominant", "incoming", "silent"] or not is_finite(seconds) or seconds <= 0.0: return ERR_INVALID_PARAMETER
	if not is_finite(source_time) or source_time < 0.0 or source_time/donor.period > 1000000: return ERR_INVALID_PARAMETER
	if donor.seek_preview(source_time) != OK: return ERR_INVALID_PARAMETER
	incoming=donor; duration=seconds; elapsed=0.0; outgoing_start=current.time_s; incoming_start=source_time
	incoming_id=source_id; policy=event_policy
	incoming_alignment=alignment*root_pose(current)*root_pose(incoming).affine_inverse()
	# A successful new transition replaces the reversible history boundary.
	retained={"outgoing":current,"target":incoming,"id":current_id,"alignment":alignment}
	elapsed_frames=0.0; frame_correction=0.0
	connect_donor(incoming)
	return OK

func apply_pose(weight: float) -> void:
	for b in range(skeleton.get_bone_count()):
		var pose: Transform3D=current.skeleton.get_bone_pose(b)
		if incoming != null: pose=pose.interpolate_with(incoming.skeleton.get_bone_pose(b), weight)
		skeleton.set_bone_pose(b, pose)
	var pelvis: Transform3D=alignment*root_pose(current)
	if incoming != null: pelvis=pelvis.interpolate_with(incoming_alignment*root_pose(incoming), weight)
	root_motion_transform=pelvis*anchor.affine_inverse()
	var relative := space.global_transform.affine_inverse()*skeleton.global_transform
	skeleton.set_bone_global_pose(current.root_bone, relative.affine_inverse()*(anchor if extracted else pelvis))
	skeleton.force_update_all_bone_transforms()

func valid_step(donor: Node, seconds: float) -> bool:
	return seconds/donor.period <= 1024 and (donor.time_s+seconds)/donor.period <= 1000000

func advance(seconds: float) -> Error:
	if not retained.is_empty(): return move_transition(seconds*current.fps,false,true)
	if busy or current == null or not is_finite(seconds) or seconds < 0.0 or not valid_step(current, seconds): return ERR_INVALID_PARAMETER
	if incoming != null and not valid_step(incoming, seconds): return ERR_INVALID_PARAMETER
	if seconds == 0.0:
		root_motion_delta=Transform3D.IDENTITY
		return OK
	busy=true; pending=[]
	var previous := root_motion_transform
	current.advance(seconds)
	if incoming != null:
		incoming.advance(seconds)
		# Derive fade progress from the compensated donor clock, not another sum.
		elapsed=current.time_s-outgoing_start
	apply_pose(clampf(elapsed/duration, 0.0, 1.0) if incoming != null else 0.0)
	root_motion_delta=previous.affine_inverse()*root_motion_transform
	var dispatches := collect_dispatches(false)
	finish_blend()
	for item in dispatches: marker.emit(item.value)
	pending=[]; busy=false
	return OK

func collect_dispatches(reverse: bool) -> Array:
	var dispatches: Array=[]
	for item in pending:
		var is_incoming: bool=item.donor == incoming
		var value: Dictionary=item.event
		# Integer marker frames avoid cancellation around the exact dominance tie.
		var marker_frame: float=value.cycle*roundf(item.donor.period*item.donor.fps)+value.phase_frame
		var at: float=(marker_frame-(incoming_start if is_incoming else outgoing_start)*item.donor.fps)/item.donor.fps
		var accepted := true
		var weight := 1.0
		if incoming != null:
			weight=clampf(at/duration, 0.0, 1.0)
			if at > duration: accepted=is_incoming
			elif policy == "silent": accepted=false
			elif policy == "incoming": accepted=is_incoming
			else: accepted=(is_incoming and weight >= 0.5) or (not is_incoming and weight < 0.5)
		value.source_clip=incoming_id if is_incoming else current_id
		value.source_weight=weight if is_incoming else (1.0-weight if incoming != null else 1.0)
		if accepted: dispatches.append({"at":at, "value":value})
	# Stable insertion sort preserves authored order for simultaneous markers.
	for i in range(1, dispatches.size()):
		var j := i
		while j > 0 and ((dispatches[j].at > dispatches[j-1].at) if reverse else (dispatches[j].at < dispatches[j-1].at)):
			var item: Dictionary=dispatches[j-1]; dispatches[j-1]=dispatches[j]; dispatches[j]=item; j-=1
	return dispatches

func finish_blend() -> void:
	if incoming != null and elapsed >= duration:
		current=incoming; current_id=incoming_id; alignment=incoming_alignment; incoming=null
		# Keep both source origins and IDs for reverse traversal of this transition.

func rewind(seconds: float, notify_crossings: bool = false) -> Error:
	if not retained.is_empty(): return move_transition(seconds*current.fps,true,notify_crossings)
	if busy or current == null or not is_finite(seconds) or seconds < 0.0 or seconds > current.time_s or seconds/current.period > 1024: return ERR_INVALID_PARAMETER
	if seconds == 0.0:
		root_motion_delta=Transform3D.IDENTITY
		return OK
	busy=true; pending=[]
	var previous := root_motion_transform
	current.rewind(seconds,notify_crossings)
	apply_pose(0.0); root_motion_delta=previous.affine_inverse()*root_motion_transform
	for item in collect_dispatches(true): marker_reversed.emit(item.value)
	pending=[]; busy=false
	return OK

func advance_frames(frames: float) -> Error:
	if retained.is_empty(): return ERR_INVALID_PARAMETER
	return move_transition(frames,false,true)

func rewind_frames(frames: float, notify_crossings: bool = false) -> Error:
	if retained.is_empty(): return ERR_INVALID_PARAMETER
	return move_transition(frames,true,notify_crossings)

func move_transition(frames: float, reverse: bool, notify_crossings: bool) -> Error:
	if busy or not is_finite(frames) or frames < 0.0: return ERR_INVALID_PARAMETER
	if not is_instance_valid(retained.outgoing) or not is_instance_valid(retained.target): return ERR_INVALID_PARAMETER
	var fps: float=retained.outgoing.fps
	var seconds: float=frames/fps
	var before := elapsed_frames
	var increment: float=(-frames if reverse else frames)-frame_correction
	var after := before+increment
	if reverse and frames == before: after=0.0
	if not is_finite(after) or after < 0.0: return ERR_INVALID_PARAMETER
	for pair in [[retained.outgoing,outgoing_start],[retained.target,incoming_start]]:
		if seconds/pair[0].period > 1024 or (pair[1]+after/fps)/pair[0].period > 1000000: return ERR_INVALID_PARAMETER
	if seconds == 0.0:
		root_motion_delta=Transform3D.IDENTITY
		return OK
	busy=true; pending=[]
	var previous := root_motion_transform
	frame_correction=0.0 if after==0.0 else (after-before)-increment
	elapsed_frames=after; elapsed=after/fps
	current=retained.outgoing; current_id=retained.id; alignment=retained.alignment
	incoming=retained.target
	current.seek_preview(outgoing_start+elapsed); incoming.seek_preview(incoming_start+elapsed)
	apply_pose(clampf(elapsed/duration,0.0,1.0))
	root_motion_delta=previous.affine_inverse()*root_motion_transform
	var dispatches: Array=[]
	if notify_crossings:
		for pair in [[current,outgoing_start,current_id,false],[incoming,incoming_start,incoming_id,true]]:
			var donor: Node=pair[0]
			var origin: float=pair[1]*fps
			var period: float=roundf(donor.period*fps)
			for cycle_number in range(int(floor((origin+minf(before,after))/period)),int(floor((origin+maxf(before,after))/period))+1):
				for event in donor.markers:
					var source_frame: float=cycle_number*period+event.phase_frame
					var at := source_frame-origin
					var crossed: bool=(at>=after and at<before) if reverse else (at>before and at<=after)
					if not crossed or cycle_number<int(event.first_cycle): continue
					var weight: float=clampf(at/(duration*fps),0.0,1.0)
					var accepted: bool=pair[3] if at>duration*fps else (false if policy=="silent" else (pair[3] if policy=="incoming" else (pair[3] == (weight>=0.5))))
					if not accepted: continue
					var value: Dictionary=event.duplicate(true)
					value.cycle=cycle_number; value.time_s=source_frame/fps; value.source_clip=pair[2]; value.source_weight=weight if pair[3] else 1.0-weight
					if reverse: value.direction=-1
					dispatches.append({"at":at,"value":value})
		# Sort forward stably, then reverse the complete ordering including ties.
		for i in range(1,dispatches.size()):
			var j := i
			while j>0 and dispatches[j].at<dispatches[j-1].at:
				var item: Dictionary=dispatches[j-1]; dispatches[j-1]=dispatches[j]; dispatches[j]=item; j-=1
		if reverse: dispatches.reverse()
	finish_blend()
	for item in dispatches:
		if reverse: marker_reversed.emit(item.value)
		else: marker.emit(item.value)
	pending=[]; busy=false
	return OK
