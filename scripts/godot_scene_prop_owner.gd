extends RefCounted
## One shared finite native clock; atomic grip sets, independently simulated props.
signal sampled(record: Dictionary)
signal actions_applied(records: Array)
signal transaction_committed(receipt: Dictionary)
signal faulted(reason: String)
const Clock = preload("native_engine_clock.gd")
const Body = preload("godot_scene_prop_body.gd")
var scene
var plan: Dictionary
var bodies: Dictionary = {}
var providers: Dictionary = {}
var initial: Dictionary = {}
var layers: Dictionary = {}
var members: Dictionary = {}
var modes: Dictionary = {}
var tracking: Dictionary = {}
var desired: Dictionary = {}
var observations: Dictionary = {}
var actions: Array = []
var history: Array = []
var history_limit := 1800
var rate := 240
var tick := -1
var session := 0
var engine_frame := -1
var group_cursor := 0
var source_time := 0.0
var seen: Dictionary = {}
var transport := "live"
var failure := ""
var pending := ""
var preview_record: Dictionary = {}
var live_record: Dictionary = {}
var configured := false
var busy := false
var save_history := true
var last_command := ""
var physics_root_deltas: Dictionary = {}
var physical_timing: Dictionary = {}

static func timing_report(document: Dictionary,physics_rate: int,maximum_delay_bits: Variant) -> Dictionary:
	if physics_rate not in [60,120,240] or not maximum_delay_bits is String or maximum_delay_bits.length()!=16: return {}
	var cap_bytes: PackedByteArray = maximum_delay_bits.hex_decode()
	if cap_bytes.size()!=8 or cap_bytes.hex_encode()!=maximum_delay_bits: return {}
	var cap: float = cap_bytes.decode_double(0)
	if not is_finite(cap) or cap<0.0: return {}
	if not document.get("clock") is Dictionary or not document.get("groups") is Array or not document.get("objects") is Array: return {}
	var times := Clock.decode(document.clock,int(document.clock.get("count",0)))
	if times.is_empty() or document.groups.is_empty() or document.groups.size()>1024: return {}
	var rows: Array = []; var collisions: Array = []; var seen := {}; var previous := -1; var maximum := 0.0
	var bytes := PackedByteArray(); bytes.resize(document.groups.size()*24)
	for index in range(document.groups.size()):
		var group = document.groups[index]
		if not group is Dictionary or not group.get("transitions") is Array or group.transitions.is_empty(): return {}
		var sample = group.get("sample_index")
		if typeof(sample) not in [TYPE_INT,TYPE_FLOAT] or not is_finite(sample) or sample!=int(sample) or sample<=previous or sample>=times.size(): return {}
		previous=int(sample); var time: float = times[previous]
		if time>2147483647.0/physics_rate: return {}
		var at: int = int(ceil(time*physics_rate))
		while float(at)/physics_rate<time: at+=1
		while at>0 and float(at-1)/physics_rate>=time: at-=1
		if at>2147483647: return {}
		var applied: float = float(at)/physics_rate; var delay: float = applied-time
		maximum=max(maximum,delay); bytes.encode_double(index*24,time); bytes.encode_double(index*24+8,applied); bytes.encode_double(index*24+16,delay)
		var names: Array = []
		for transition in group.transitions:
			if not transition is Dictionary or not transition.get("object") is String or transition.object not in document.objects or transition.object in names: return {}
			names.append(transition.object)
			var key: String = transition.object+":"+str(at)
			if seen.has(key): collisions.append({"object":transition.object,"tick":at,"first_group":seen[key],"later_group":index})
			else: seen[key]=index
		rows.append({"group_index":index,"sample_index":previous,"tick":at,"objects":names})
	return {"schema":"strep-scene-prop-physics-timing-v1","physics_fps":physics_rate,"maximum_delay_f64le":maximum_delay_bits,
		"application_clock":{"schema":"strep-physics-event-clock-f64le-v1","count":rows.size(),"bytes_hex":bytes.hex_encode()},
		"groups":rows,"collapsed_prop_transactions":collisions,"within_requested_delay":maximum<=cap,
		"distinct_prop_boundaries":collisions.is_empty(),"contract_satisfied":maximum<=cap and collisions.is_empty(),"quality_approved":false,"release_approved":false}

static func checked_timing(document: Dictionary,report: Variant,physics_rate: int) -> bool:
	if not report is Dictionary: return false
	var expected := timing_report(document,physics_rate,report.get("maximum_delay_f64le"))
	if expected.is_empty() or not expected.contract_satisfied or report.size()!=expected.size(): return false
	for key in ["schema","maximum_delay_f64le"]:
		if report.get(key)!=expected[key]: return false
	for key in ["within_requested_delay","distinct_prop_boundaries","contract_satisfied","quality_approved","release_approved"]:
		if typeof(report.get(key))!=TYPE_BOOL or report[key]!=expected[key]: return false
	if report.get("physics_fps")!=physics_rate or not report.get("application_clock") is Dictionary: return false
	var clock: Dictionary = report.application_clock
	if typeof(clock.get("count")) not in [TYPE_INT,TYPE_FLOAT]: return false
	if clock.size()!=3 or clock.get("schema")!=expected.application_clock.schema or clock.get("count")!=expected.application_clock.count or clock.get("bytes_hex")!=expected.application_clock.bytes_hex: return false
	if not report.get("collapsed_prop_transactions") is Array or not report.collapsed_prop_transactions.is_empty() or not report.get("groups") is Array or report.groups.size()!=expected.groups.size(): return false
	for index in range(expected.groups.size()):
		var row = report.groups[index]; var other: Dictionary = expected.groups[index]
		if not row is Dictionary or row.size()!=4 or row.get("objects")!=other.objects: return false
		for field in ["group_index","sample_index","tick"]:
			if typeof(row.get(field)) not in [TYPE_INT,TYPE_FLOAT] or row[field]!=other[field]: return false
	return true

static func rigid(t: Transform3D) -> bool:
	return t.is_finite() and abs(t.basis.determinant()-1.0)<0.00001 and t.basis.is_equal_approx(t.basis.orthonormalized())

static func spin_between(a: Basis,b: Basis,seconds: float) -> Vector3:
	var q := (b*a.inverse()).get_rotation_quaternion().normalized()
	if q.w<0.0: q=-q
	var v := Vector3(q.x,q.y,q.z); var length := v.length()
	return Vector3.ZERO if length<1e-12 else v*(2.0*atan2(length,q.w)/length/seconds)

func agree(a: Transform3D,b: Transform3D) -> bool:
	return a.origin.distance_to(b.origin)<=plan.position_tolerance_m and spin_between(a.basis,b.basis,1.0).length()<=plan.rotation_tolerance_rad

static func freeze_containers(value: Variant) -> void:
	if value is Dictionary:
		for child in value.values(): freeze_containers(child)
		value.make_read_only()
	elif value is Array:
		for child in value: freeze_containers(child)
		value.make_read_only()

func commit_receipt(record: Dictionary) -> Dictionary:
	var ids := {}; var source_events: Array = []; var root_modes := {}
	var clock_bytes := PackedByteArray(); clock_bytes.resize(actions.size()*24)
	for index in range(actions.size()):
		var action: Dictionary = actions[index]
		clock_bytes.encode_double(index*24,action.source_time_s)
		clock_bytes.encode_double(index*24+8,action.physics_application_time_s)
		clock_bytes.encode_double(index*24+16,action.application_delay_s)
		for id in action.event_ids: ids[id]=true
	for event in plan.source_events:
		if ids.has(event.id):
			var copy: Dictionary = event.duplicate(true)
			copy.time_s=scene.times[int(event.sample_index)]; source_events.append(copy)
	for id in scene.actors: root_modes[id]="extracted" if scene.actors[id].extracted else "embedded"
	var owner_id := str(get_instance_id())
	var receipt := {"schema":"strep-scene-prop-commit-v1","commit_id":owner_id+":"+str(session)+":"+str(tick),"owner_instance_id":owner_id,
		"source_semantic_sha256":plan.get("source_semantic_sha256",""),"source_clock":plan.clock.duplicate(true),"source_events":source_events,
		"action_clock":{"schema":"strep-scene-prop-action-clock-f64le-v1","count":actions.size(),"bytes_hex":clock_bytes.hex_encode()},"physics_rate_hz":rate,
		"actions":actions.duplicate(true),"record":record.duplicate(true),"actor_root_motion":scene.playback_roots.duplicate(true),"root_modes":root_modes,
		"props_state_phase":"assigned_before_force_integration",
		"scene_pose_time_s":scene.pose_time_s,"scene_playback_time_s":scene.playback_time_s,"quality_approved":false,"release_approved":false}
	freeze_containers(receipt)
	return receipt

func bind(native_scene,document: Dictionary,props: Dictionary,grips: Dictionary,physics_rate: int = 240,capacity: int = 1800,timing_contract: Variant = null) -> Error:
	if configured or native_scene == null or not native_scene.bound or native_scene.playback_time_s != null or native_scene.pose_time_s != 0.0 or native_scene.has_meta("strep_prop_owner"): return ERR_INVALID_PARAMETER
	if physics_rate not in [60,120,240] or Engine.physics_ticks_per_second != physics_rate or capacity<2 or capacity>3600: return ERR_INVALID_PARAMETER
	if document.get("schema") != "strep-scene-prop-ownership-v1" or not document.get("clock") is Dictionary or not document.get("objects") is Array or not document.get("grips") is Dictionary or not document.get("groups") is Array or not document.get("source_events") is Array: return ERR_INVALID_DATA
	var decoded := Clock.decode(document.clock,int(document.clock.get("count",0)))
	if decoded.is_empty() or decoded != native_scene.times or props.size()<1 or props.size()>32 or document.objects.size()!=props.size(): return ERR_INVALID_DATA
	for field in ["position_tolerance_m","rotation_tolerance_rad"]:
		var limit = document.get(field)
		if typeof(limit) not in [TYPE_INT,TYPE_FLOAT] or not is_finite(limit) or limit<=0.0 or limit>0.01: return ERR_INVALID_DATA
	if document.grips.size()<1 or document.grips.size()>64 or grips.size()!=document.grips.size() or document.groups.size()>1024: return ERR_INVALID_DATA
	var checked := {}; var occupancy := {}; var source_events := {}; var last := -1
	if document.source_events.size()!=native_scene.events.events.size(): return ERR_INVALID_DATA
	for index in range(document.source_events.size()):
		var contract = document.source_events[index]; var event = native_scene.events.events[index]
		if not contract is Dictionary or contract.size()!=7: return ERR_INVALID_DATA
		for field in ["id","name","actor","kind","sample_index","timing_confirmed","runtime_dispatch_allowed"]:
			if not contract.has(field) or contract[field]!=event.get(field): return ERR_INVALID_DATA
		source_events[event.id]=event
	for id in document.objects:
		if not id is String or checked.has(id) or not props.get(id) is RigidBody3D: return ERR_INVALID_DATA
		var body: RigidBody3D = props[id]
		if body.get_script()!=Body or body.strep_manager != null or not body.is_inside_tree() or body.freeze or not rigid(body.global_transform): return ERR_INVALID_DATA
		if native_scene.props != null and body in native_scene.props.objects.values(): return ERR_INVALID_DATA
		checked[id]=[]
	for id in document.grips:
		var binding = document.grips[id]
		if not binding is Dictionary or binding.size()!=1 or not native_scene.actors.has(binding.get("actor")) or not grips.get(id) is Callable or not grips[id].is_valid(): return ERR_INVALID_DATA
	for group in document.groups:
		if not group is Dictionary or not group.get("transitions") is Array: return ERR_INVALID_DATA
		var index = group.get("sample_index")
		if typeof(index) not in [TYPE_INT,TYPE_FLOAT] or index!=int(index) or index<=last or index<0 or index>=decoded.size(): return ERR_INVALID_DATA
		last=int(index); var changed := {}; var next := checked.duplicate(true)
		for transition in group.transitions:
			if not transition is Dictionary or not checked.has(transition.get("object")) or changed.has(transition.object) or transition.get("before")!=checked[transition.object] or not transition.get("after") is Array or not transition.get("changes") is Array: return ERR_INVALID_DATA
			changed[transition.object]=true; var pairs := {}; var proposed: Array = checked[transition.object].duplicate()
			for command in transition.changes:
				if not command is Dictionary or command.size()!=4 or command.get("object")!=transition.object or not document.grips.has(command.get("grip")) or pairs.has(command.grip): return ERR_INVALID_DATA
				pairs[command.grip]=true; var event = source_events.get(command.get("event_id"))
				if event == null or not event.runtime_dispatch_allowed or event.sample_index!=index or event.actor!=document.grips[command.grip].actor: return ERR_INVALID_DATA
				if command.get("action")=="release" and command.grip in proposed: proposed.erase(command.grip)
				elif command.get("action")=="acquire" and command.grip not in proposed: proposed.append(command.grip)
				else: return ERR_INVALID_DATA
			proposed.sort()
			if proposed!=transition.after or transition.get("mode")!=("held" if not proposed.is_empty() else "released") or transition.get("last_grip_released")!=(not transition.before.is_empty() and proposed.is_empty()): return ERR_INVALID_DATA
			next[transition.object]=proposed
		occupancy.clear()
		for list in next.values():
			for grip in list:
				if occupancy.has(grip): return ERR_INVALID_DATA
				occupancy[grip]=true
		checked=next
	if timing_contract!=null:
		if not checked_timing(document,timing_contract,physics_rate): return ERR_INVALID_DATA
		physical_timing=timing_contract.duplicate(true)
	# Whole source/participant/transition preflight precedes body mutation.
	scene=native_scene; plan=document.duplicate(true); bodies=props.duplicate(); providers=grips.duplicate(); rate=physics_rate; history_limit=capacity
	scene.set_meta("strep_prop_owner",get_instance_id())
	for id in bodies:
		var body: RigidBody3D = bodies[id]
		initial[id]=body.global_transform; layers[id]=[body.collision_layer,body.collision_mask]
		body.strep_manager=self; body.strep_prop_id=id; body.custom_integrator=true; body.can_sleep=false
		body.center_of_mass_mode=RigidBody3D.CENTER_OF_MASS_MODE_CUSTOM; body.center_of_mass=Vector3.ZERO
	configured=true
	return OK

func stop(reason: String) -> void:
	if failure.is_empty(): failure=reason; transport="fault"; faulted.emit(reason)

func pose(id: String,grips: Array) -> Variant:
	if grips.is_empty(): return null
	var names := grips.duplicate(); names.sort(); var selected: Variant = null
	for key in names:
		var expected_time: float = scene.pose_time_s
		var candidate = providers[key].call(id)
		if scene.pose_time_s!=expected_time or scene.playback_time_s!=expected_time: stop("Grip provider changed the owned scene clock"); return null
		if not candidate is Transform3D or not rigid(candidate): stop("Grip provider returned a nonrigid world transform"); return null
		if selected == null: selected=candidate
		elif not agree(selected,candidate): stop("Active grips request incompatible prop poses; no averaging"); return null
	return selected

func command(value: String) -> Error:
	if value not in ["pause","resume","restart"]: return ERR_INVALID_PARAMETER
	if not configured or busy or failure!="" or pending!="": return ERR_BUSY
	if value=="pause" and (tick<0 or transport!="live"): return ERR_BUSY
	if value=="resume" and transport=="live": return ERR_BUSY
	pending=value; return OK

func pause_playback() -> Error: return command("pause")
func resume_playback() -> Error: return command("resume")
func restart_playback() -> Error: return command("restart")
func preview_tick(value: int) -> Error:
	if tick<0 or pending!="" or failure!="" or busy: return ERR_BUSY
	for record in history:
		if record.tick==value: preview_record=record.duplicate(true); pending="preview"; return OK
	return ERR_DOES_NOT_EXIST

func restore(record: Dictionary) -> void:
	tick=record.tick; group_cursor=record.group_cursor; members=record.members.duplicate(true); modes=record.modes.duplicate(true); tracking=record.tracking.duplicate(true); source_time=record.source_time_s
	if scene.seek_preview(source_time)!=OK: stop("Scene snapshot preview rejected")
	desired=record.props.duplicate(true)

func prepare_step() -> void:
	actions.clear(); observations.clear(); desired.clear()
	var request := pending; pending=""; last_command=request; save_history=true
	if tick<0 or request=="restart":
		if tick>=0: session+=1
		if scene.restart()!=OK: stop("Owned scene restart rejected"); return
		tick=0; source_time=0.0; group_cursor=0; transport="live"; history.clear(); members.clear(); modes.clear(); tracking.clear()
		for id in bodies:
			members[id]=[]; modes[id]="parked"; tracking[id]={"pose":initial[id],"time_s":0.0}
			desired[id]={"pose":initial[id],"velocity":Vector3.ZERO,"spin":Vector3.ZERO}
	elif request in ["pause","preview"]:
		if transport=="live": live_record=history.back().duplicate(true)
		restore(preview_record if request=="preview" else live_record); transport="preview" if request=="preview" else "paused"; return
	elif request=="resume": restore(live_record); transport="live"; save_history=false; return
	elif transport!="live":
		for id in bodies: desired[id]={"pose":tracking[id].pose,"velocity":Vector3.ZERO,"spin":Vector3.ZERO}
		return
	else:
		if scene.playback_time_s!=source_time or scene.pose_time_s!=source_time: stop("Another driver changed the owned scene clock"); return
		tick+=1
	var target: float = min(float(tick)/rate,scene.times[-1])
	while group_cursor<plan.groups.size():
		var group: Dictionary = plan.groups[group_cursor]; var time: float = scene.times[int(group.sample_index)]
		if time>target: break
		if not physical_timing.is_empty() and physical_timing.groups[group_cursor].tick!=tick: stop("Ownership boundary differs from declared physical timing"); return
		if not scene.advance_to(time).valid: stop("Native ownership event advance rejected"); return
		var commits := {}; var planned_actions: Array = []
		for transition in group.transitions:
			var id: String = transition.object; var before: Array = members[id]; var after: Array = transition.after
			if before!=transition.before: stop("Grip membership differs from bound plan"); return
			var old_pose = pose(id,before); var new_pose = pose(id,after)
			if failure!="": return
			if new_pose!=null:
				var incoming: Transform3D = old_pose if old_pose!=null else (initial[id] if modes[id]=="parked" else PhysicsServer3D.body_get_direct_state(bodies[id].get_rid()).transform)
				if not agree(incoming,new_pose): stop("Acquisition/handoff would snap the prop beyond declared bounds"); return
			var action := {"object":id,"before":before.duplicate(),"after":after.duplicate(),"event_ids":[],"source_time_s":time,"physics_application_time_s":float(tick)/rate,"application_delay_s":float(tick)/rate-time,"tick":tick,"session":session,"last_grip_released":transition.last_grip_released}
			for c in transition.changes:
				if c.event_id not in action.event_ids: action.event_ids.append(c.event_id)
			var sample := {"pose":new_pose if new_pose!=null else old_pose,"velocity":Vector3.ZERO,"spin":Vector3.ZERO}
			if transition.last_grip_released:
				var elapsed: float = time-tracking[id].time_s
				if elapsed<=0.0: stop("Release has no incoming held-pose interval"); return
				sample.velocity=(old_pose.origin-tracking[id].pose.origin)/elapsed
				sample.spin=spin_between(tracking[id].pose.basis,old_pose.basis,elapsed)
			action.pose=sample.pose; action.velocity=sample.velocity; action.spin=sample.spin
			commits[id]={"members":after.duplicate(),"mode":transition.mode,"sample":sample,"time_s":time}; planned_actions.append(action)
		# All prop/grip checks finish before applying this logical transaction.
		for id in commits:
			var c: Dictionary = commits[id]; members[id]=c.members; modes[id]=c.mode; desired[id]=c.sample
			tracking[id]={"pose":c.sample.pose,"time_s":c.time_s}
		actions.append_array(planned_actions); group_cursor+=1
	if not scene.advance_to(target).valid: stop("Shared native clock advance rejected"); return
	source_time=target
	for id in bodies:
		if modes[id]=="held":
			var held = pose(id,members[id])
			if failure!="": return
			desired[id]={"pose":held,"velocity":Vector3.ZERO,"spin":Vector3.ZERO}; tracking[id]={"pose":held,"time_s":target}
		elif modes[id]=="parked": desired[id]={"pose":initial[id],"velocity":Vector3.ZERO,"spin":Vector3.ZERO}

func integrate_body(body: RigidBody3D,state: PhysicsDirectBodyState3D) -> void:
	if not configured: return
	var frame := Engine.get_physics_frames(); var id: String = body.strep_prop_id
	if frame!=engine_frame:
		if engine_frame>=0 and seen.size()!=bodies.size(): stop("A bound prop missed the shared physics boundary")
		engine_frame=frame; seen.clear(); busy=true
		var before_roots: Dictionary = scene.playback_roots.duplicate()
		if failure.is_empty(): prepare_step()
		physics_root_deltas.clear()
		for actor_id in scene.actors:
			physics_root_deltas[actor_id]=before_roots[actor_id].affine_inverse()*scene.playback_roots[actor_id] if failure.is_empty() and transport=="live" and last_command not in ["restart","resume"] else Transform3D.IDENTITY
	if not bodies.has(id) or bodies[id]!=body or seen.has(id): stop("Unexpected or repeated prop integration")
	if abs(state.step-1.0/rate)>1e-9: stop("Physics clock changed")
	seen[id]=true
	var dynamic: bool = failure.is_empty() and transport=="live" and modes.get(id)=="released"
	if desired.has(id) and failure.is_empty():
		state.transform=desired[id].pose; state.linear_velocity=desired[id].velocity; state.angular_velocity=desired[id].spin
	if not dynamic:
		state.transform=tracking[id].pose if failure.is_empty() else (history.back().props[id].pose if not history.is_empty() else initial[id])
		state.linear_velocity=Vector3.ZERO; state.angular_velocity=Vector3.ZERO
	state.collision_layer=layers[id][0] if dynamic else 0; state.collision_mask=layers[id][1] if dynamic else 0
	var contacts: Array = []
	for index in range(state.get_contact_count()):
		var collider := state.get_contact_collider_object(index)
		contacts.append(str(collider.get_meta("strep_collider_id","unknown")) if collider!=null else "unknown")
	observations[id]={"pose":state.transform,"velocity":state.linear_velocity,"spin":state.angular_velocity,"contacts":contacts,"collision_layer":state.collision_layer,"collision_mask":state.collision_mask,"step_s":state.step,"gravity":state.total_gravity,"inverse_mass":state.inverse_mass,"inverse_inertia":state.inverse_inertia,"direct_state_class":state.get_class()}
	if modes.get(id)=="released": tracking[id]={"pose":state.transform,"time_s":source_time}
	if dynamic: state.integrate_forces()
	if seen.size()==bodies.size():
		var record := {"tick":tick,"session":session,"source_time_s":source_time,"group_cursor":group_cursor,"members":members.duplicate(true),"modes":modes.duplicate(),"tracking":tracking.duplicate(true),"props":observations.duplicate(true),"physics_root_deltas":physics_root_deltas.duplicate(),"transport":transport,"failure":failure,"command":last_command}
		if transport=="live" and save_history:
			history.append(record.duplicate(true))
			if history.size()>history_limit: history.pop_front()
		var receipt: Dictionary = commit_receipt(record) if not actions.is_empty() and failure.is_empty() else {}
		var applied: Array = actions.duplicate(true)
		busy=false
		if not receipt.is_empty():
			transaction_committed.emit(receipt)
			actions_applied.emit(applied)
		sampled.emit(record)
