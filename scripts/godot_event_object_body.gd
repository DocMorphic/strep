extends RigidBody3D
## One prop, one owned cycle clock. See integrations/godot/OBJECT-EVENTS.md.
## Signals are observations; external gameplay effects are not rolled back.
signal sampled(record: Dictionary)
signal action_applied(event: Dictionary)
signal faulted(reason: String)

var clock: Node
var grip_pose: Callable
var attach_id := ""
var release_id := ""
var physics_fps := 60
var history_limit := 1800
var history: Array = []
var tick := 0
var session := 0
var mode := "parked"
var transport := "live"
var failure := ""
var configured := false
var advancing := false
var started := false
var initial := Transform3D.IDENTITY
var previous_grip := Transform3D.IDENTITY
var held_pose := Transform3D.IDENTITY
var live_snapshot: Dictionary = {}
var pending := ""
var preview_snapshot: Dictionary = {}
var crossings: Array = []
var free_layer := 1
var free_mask := 1

func rigid(t: Transform3D) -> bool:
	return t.is_finite() and abs(t.basis.determinant()-1.0)<0.0001 and t.basis.is_equal_approx(t.basis.orthonormalized())

func bind_prop(adapter: Node, pose_provider: Callable, attach_event: String, release_event: String, rate: int = 60, capacity: int = 1800) -> Error:
	if configured or adapter == null or not adapter.bound or adapter.time_s != 0.0 or not pose_provider.is_valid(): return ERR_INVALID_PARAMETER
	if rate < 30 or rate > 240 or rate % 30 != 0 or Engine.physics_ticks_per_second != rate or capacity < 2 or capacity > 3600: return ERR_INVALID_PARAMETER
	if attach_event.is_empty() or release_event.is_empty() or attach_event == release_event or not rigid(global_transform): return ERR_INVALID_PARAMETER
	var chosen: Dictionary = {}
	for event in adapter.markers:
		var id: String = event.get("event_id", "")
		if id == attach_event or id == release_event:
			var source: Dictionary = event.get("source_event", {})
			if chosen.has(id) or source.get("kind") != "authored" or source.get("requires_review", true) or source.get("id") != id or event.first_cycle != 0: return ERR_INVALID_DATA
			chosen[id] = int(event.phase_frame)
	if chosen.size() != 2 or chosen[attach_event] < 1 or chosen[release_event] <= chosen[attach_event]: return ERR_INVALID_DATA
	clock=adapter; grip_pose=pose_provider; attach_id=attach_event; release_id=release_event
	physics_fps=rate; history_limit=capacity; initial=global_transform; held_pose=initial
	free_layer=collision_layer; free_mask=collision_mask
	# The supplied pose is the prop's center of mass, including its grip offset.
	center_of_mass_mode=CENTER_OF_MASS_MODE_CUSTOM; center_of_mass=Vector3.ZERO
	custom_integrator=true; can_sleep=false
	clock.marker.connect(queue_crossing)
	configured=true
	return OK

func queue_crossing(event: Dictionary) -> void:
	# Only dispatches made by our own fixed step can command this prop.
	# Reverse notifications, unrelated events and later loop repetitions do not.
	if advancing and event.get("cycle", -1) == 0 and event.get("event_id", "") in [attach_id, release_id]: crossings.append(event.duplicate(true))

func pause_playback() -> Error:
	if not started or failure != "" or pending != "" or transport != "live": return ERR_BUSY
	pending="pause"
	return OK

func preview_tick(recorded_tick: int) -> Error:
	if not started or failure != "" or pending != "": return ERR_BUSY
	for record in history:
		if record.tick == recorded_tick:
			preview_snapshot=record.duplicate(true); pending="preview"
			return OK
	return ERR_DOES_NOT_EXIST

func resume_playback() -> Error:
	if not started or failure != "" or pending != "" or transport == "live": return ERR_BUSY
	pending="resume"
	return OK

func restart_playback() -> Error:
	if not configured or failure != "" or pending != "": return ERR_BUSY
	pending="restart"
	return OK

func stop_with_error(reason: String) -> void:
	if failure.is_empty():
		failure=reason; transport="fault"; faulted.emit(reason)

func snapshot(state: PhysicsDirectBodyState3D) -> Dictionary:
	return {"tick":tick,"time_s":clock.time_s,"time_correction":clock.time_correction,
		"pose":state.transform,"velocity":state.linear_velocity,"spin":state.angular_velocity,
		"grip":previous_grip,"mode":mode,"session":session}

func restore(state: PhysicsDirectBodyState3D, record: Dictionary) -> void:
	tick=record.tick; mode=record.mode; previous_grip=record.grip; held_pose=record.pose
	clock.seek_preview(record.time_s); clock.time_correction=record.time_correction
	grip_pose.call()
	state.transform=record.pose; state.linear_velocity=record.velocity; state.angular_velocity=record.spin

func _integrate_forces(state: PhysicsDirectBodyState3D) -> void:
	if not configured: return
	if abs(state.step-1.0/physics_fps)>0.00000001: stop_with_error("Physics step changed; fixed authored-event timing required")
	var command := pending
	pending=""
	var just_restored := false
	if failure.is_empty() and (not started or command=="restart"):
		if started: session+=1
		started=true; tick=0; mode="parked"; transport="live"; history.clear(); crossings.clear()
		clock.restart(false); previous_grip=grip_pose.call(); held_pose=initial
		state.transform=initial; state.linear_velocity=Vector3.ZERO; state.angular_velocity=Vector3.ZERO
		just_restored=true
	elif failure.is_empty() and command in ["pause","preview"]:
		if transport=="live": live_snapshot=history.back().duplicate(true)
		restore(state, preview_snapshot if command=="preview" else live_snapshot)
		transport="preview" if command=="preview" else "paused"
	elif failure.is_empty() and command=="resume":
		restore(state,live_snapshot); transport="live"; just_restored=true
	elif failure.is_empty() and transport=="live":
		if abs(clock.time_s-float(tick)/physics_fps)>0.000000001:
			stop_with_error("Another driver changed the owned animation clock")
		else:
			advancing=true
			var error: Error = clock.advance(1.0/physics_fps)
			advancing=false
			if error != OK: stop_with_error("Animation advance rejected")
			tick+=1
			var current: Transform3D = grip_pose.call()
			if not rigid(current):
				stop_with_error("Grip provider must return a finite, rigid world transform")
				current=previous_grip; crossings.clear()
			var velocity := (current.origin-previous_grip.origin)*physics_fps
			var delta_q := (current.basis*previous_grip.basis.inverse()).get_rotation_quaternion().normalized()
			if delta_q.w<0.0: delta_q=-delta_q
			# Avoid Quaternion.get_axis()'s near-identity shortcut: its returned
			# vector is not a unit axis for tiny deltas, suppressing release spin.
			var imaginary := Vector3(delta_q.x,delta_q.y,delta_q.z)
			var sine_half := imaginary.length()
			var spin := Vector3.ZERO
			if sine_half>0.000000000001: spin=imaginary*(2.0*atan2(sine_half,delta_q.w)/sine_half)*physics_fps
			for event in crossings:
				if abs(event.time_s-clock.time_s)>0.00000001:
					stop_with_error("Event crossed away from its authored physics boundary"); break
				var action := ""
				if event.event_id==attach_id and mode=="parked": mode="held"; action="attach"
				elif event.event_id==release_id and mode=="held": mode="released"; action="release"
				if action!="":
					state.transform=current; held_pose=current
					state.linear_velocity=velocity if action=="release" else Vector3.ZERO
					state.angular_velocity=spin if action=="release" else Vector3.ZERO
					var observed: Dictionary = event.duplicate(true)
					observed.action=action; observed.session=session; observed.tick=tick
					observed.pose=current; observed.velocity=state.linear_velocity; observed.spin=state.angular_velocity
					action_applied.emit(observed)
			crossings.clear(); previous_grip=current
			if mode=="held": held_pose=current
	if not rigid(previous_grip): stop_with_error("Grip provider returned an invalid transform")
	var dynamic := failure.is_empty() and transport=="live" and mode=="released"
	if dynamic: held_pose=state.transform
	state.collision_layer=free_layer if dynamic else 0
	state.collision_mask=free_mask if dynamic else 0
	if not dynamic:
		state.transform=held_pose; state.linear_velocity=Vector3.ZERO; state.angular_velocity=Vector3.ZERO
	var record := snapshot(state)
	if transport=="live" and (not just_restored or command!="resume"):
		history.append(record.duplicate(true))
		if history.size()>history_limit: history.pop_front()
	var observed: Dictionary = record.duplicate(true)
	observed.transport=transport; observed.command=command; observed.failure=failure
	observed.collision_layer=state.collision_layer; observed.collision_mask=state.collision_mask
	observed.step_s=state.step; observed.gravity=state.total_gravity; observed.contacts=[]
	for index in range(state.get_contact_count()):
		var collider := state.get_contact_collider_object(index)
		observed.contacts.append(str(collider.get_meta("strep_collider_id","unknown")) if collider != null else "unknown")
	sampled.emit(observed)
	if dynamic: state.integrate_forces()
