extends Node
## Finite GLB sampled periodically. Caller owns gameplay movement and physics.
signal marker(event: Dictionary)
## Reverse crossings are notifications, not inverse gameplay commands.
signal marker_reversed(event: Dictionary)
var player: AnimationPlayer
var skeleton: Skeleton3D
var space: Node3D
var clip: StringName
var root_bone := -1
var period := 0.0
var fps := 30.0
var cycle := Transform3D.IDENTITY
var anchor := Transform3D.IDENTITY
var root_motion_transform := Transform3D.IDENTITY
var root_motion_delta := Transform3D.IDENTITY
var time_s := 0.0
var time_correction := 0.0
var extracted := false
var markers: Array = []
var bound := false

func decode_matrix(rows: Array) -> Transform3D:
	return Transform3D(Basis(Vector3(rows[0][0], rows[1][0], rows[2][0]), Vector3(rows[0][1], rows[1][1], rows[2][1]), Vector3(rows[0][2], rows[1][2], rows[2][2])), Vector3(rows[0][3], rows[1][3], rows[2][3]))

func matrix_valid(rows: Variant) -> bool:
	if not rows is Array or rows.size() != 4: return false
	for row in rows:
		if not row is Array or row.size() != 4: return false
		for v in row:
			if not (v is float or v is int) or not is_finite(float(v)): return false
	if abs(rows[3][0]) + abs(rows[3][1]) + abs(rows[3][2]) + abs(rows[3][3] - 1.0) > 0.000001: return false
	var t := decode_matrix(rows)
	return abs(t.basis.determinant()-1.0) < 0.00001 and t.basis.is_equal_approx(t.basis.orthonormalized()) and abs(t.origin.y) < 0.000001 and t.basis.y.is_equal_approx(Vector3.UP)

func bind_cycle(p: AnimationPlayer, s: Skeleton3D, actor: Node3D, animation_name: StringName, data: Dictionary, glb_path: String, extract: bool = false) -> Error:
	if bound or p == null or s == null or actor == null or not actor.is_ancestor_of(s) or not p.has_animation(animation_name): return ERR_INVALID_PARAMETER
	if data.get("schema") != "strep-runtime-cycle-v1" or data.get("fps") != 30 or not matrix_valid(data.get("cycle_transform")): return ERR_INVALID_DATA
	if not data.get("glb_sha256") is String or FileAccess.get_sha256(glb_path) != data.glb_sha256: return ERR_INVALID_DATA
	var frames := float(data.get("period_frames", 0))
	if frames != floor(frames) or frames < 5 or frames > 900 or not data.get("root_bone") is String: return ERR_INVALID_DATA
	var bone := s.find_bone(data.root_bone)
	var animation := p.get_animation(animation_name)
	if bone < 0 or animation.loop_mode != Animation.LOOP_NONE or not p.root_motion_track.is_empty() or abs(animation.length-frames/30.0) > 0.00001: return ERR_INVALID_DATA
	if not data.get("markers") is Array: return ERR_INVALID_DATA
	var previous := -1
	for e in data.markers:
		if not e is Dictionary or not e.get("name") is String: return ERR_INVALID_DATA
		var f := float(e.get("phase_frame", -1))
		var first := float(e.get("first_cycle", -1))
		if not is_finite(f) or f != floor(f) or f < 0 or f >= frames or f < previous or first != floor(first) or first < 0 or first > 1: return ERR_INVALID_DATA
		previous = int(f)
	player=p; skeleton=s; space=actor; clip=animation_name; root_bone=bone; period=frames/30.0; cycle=decode_matrix(data.cycle_transform); extracted=extract; markers=data.markers.duplicate(true)
	player.callback_mode_process=AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_MANUAL
	player.play(clip); player.seek(0.0, true, true)
	anchor=space.global_transform.affine_inverse()*skeleton.global_transform*skeleton.get_bone_global_pose(root_bone)
	bound=true
	return seek_preview(0.0)

func power(n: int) -> Transform3D:
	var value := Transform3D.IDENTITY
	var factor := cycle
	while n > 0:
		if n & 1: value=value*factor
		factor=factor*factor
		n=n>>1
	return value

func sample(seconds: float) -> void:
	var cycles := int(floor(seconds/period))
	var phase := seconds-cycles*period
	player.seek(phase, true, true)
	var relative := space.global_transform.affine_inverse()*skeleton.global_transform
	var original := relative*skeleton.get_bone_global_pose(root_bone)
	var placed := power(cycles)*original
	root_motion_transform=placed*anchor.affine_inverse()
	skeleton.set_bone_global_pose(root_bone, relative.affine_inverse()*(anchor if extracted else placed))
	skeleton.force_update_all_bone_transforms()

func seek_preview(seconds: float) -> Error:
	if not bound or not is_finite(seconds) or seconds < 0 or seconds/period > 1000000: return ERR_INVALID_PARAMETER
	sample(seconds); time_s=seconds; time_correction=0.0; root_motion_delta=Transform3D.IDENTITY
	return OK

func restart(dispatch_initial: bool = false) -> Error:
	var error := seek_preview(0.0)
	if error != OK: return error
	if dispatch_initial:
		for e in markers:
			if e.phase_frame == 0 and e.first_cycle == 0: dispatch(e, 0)
	return OK

func dispatch(event: Dictionary, cycle_number: int) -> void:
	var value := event.duplicate(true)
	value.cycle=cycle_number; value.time_s=cycle_number*period+float(event.phase_frame)/fps
	marker.emit(value)

func advance(seconds: float) -> Error:
	if not bound or not is_finite(seconds) or seconds < 0 or seconds/period > 1024 or (time_s+seconds)/period > 1000000: return ERR_INVALID_PARAMETER
	if seconds == 0.0:
		root_motion_delta=Transform3D.IDENTITY
		return OK
	var before := time_s
	# Compensated clock accumulation avoids losing exact wrap events to repeated
	# 1/30 or 1/60 additions. No early-event epsilon or tolerance is used.
	var increment := seconds-time_correction
	var after := before+increment
	time_correction=(after-before)-increment
	var previous := root_motion_transform
	sample(after); time_s=after; root_motion_delta=previous.affine_inverse()*root_motion_transform
	# Open-left, closed-right interval: a marker at the starting cursor never repeats.
	for n in range(int(floor(before/period)), int(floor(after/period))+1):
		for e in markers:
			var at := n*period+float(e.phase_frame)/fps
			if n >= int(e.first_cycle) and at > before and at <= after: dispatch(e,n)
	return OK

func rewind(seconds: float, notify_crossings: bool = false) -> Error:
	# Keep advance's forward-only contract. Rewinding is explicit and silent by
	# default, so existing sound/spawn/grasp listeners cannot fire accidentally.
	if not bound or not is_finite(seconds) or seconds < 0 or seconds/period > 1024: return ERR_INVALID_PARAMETER
	if seconds == 0.0:
		root_motion_delta=Transform3D.IDENTITY
		return OK
	var before := time_s
	var increment := -seconds-time_correction
	# Consuming exactly the exposed remaining clock reaches zero exactly.
	# This is an explicit endpoint request, not an epsilon or an early crossing.
	var after := 0.0 if seconds == before else before+increment
	if not is_finite(after) or after < 0 or after/period > 1000000: return ERR_INVALID_PARAMETER
	var correction := 0.0 if seconds == before else (after-before)-increment
	var previous := root_motion_transform
	sample(after); time_s=after; time_correction=correction
	root_motion_delta=previous.affine_inverse()*root_motion_transform
	if notify_crossings:
		# Closed destination, open origin. Simultaneous markers use reverse
		# metadata order, the inverse of forward dispatch's total ordering.
		for n in range(int(floor(before/period)), int(floor(after/period))-1, -1):
			for i in range(markers.size()-1, -1, -1):
				var e: Dictionary=markers[i]
				var at := n*period+float(e.phase_frame)/fps
				if n >= int(e.first_cycle) and at >= after and at < before:
					var value := e.duplicate(true)
					value.cycle=n; value.time_s=at; value.direction=-1
					marker_reversed.emit(value)
	return OK
