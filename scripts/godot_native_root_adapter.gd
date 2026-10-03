extends RefCounted
## Finite native LINEAR bone resources. Exclusive ownership of actor/player/poses.
## Absolute authored clock; no event dispatch, physics, looping or blending.
const Preview = preload("native_godot_preview.gd")
var player: AnimationPlayer
var skeleton: Skeleton3D
var actor: Node3D
var animation: Animation
var root_bone := -1
var base_poses: Array[Transform3D] = []
var placement := Transform3D.IDENTITY
var relative := Transform3D.IDENTITY
var anchor := Transform3D.IDENTITY
var root_motion_transform := Transform3D.IDENTITY
var root_motion_delta := Transform3D.IDENTITY
var time_s := 0.0
var extracted := false
var bound := false
var skeleton_version := 0

static func rigid(value: Transform3D) -> bool:
	return value.is_finite() and abs(value.basis.determinant() - 1.0) <= 0.00001 and value.basis.is_equal_approx(value.basis.orthonormalized())

static func nodes(node: Node) -> Array:
	var found: Array = [node]
	for child in node.get_children(): found.append_array(nodes(child))
	return found

static func eligible(p: AnimationPlayer, s: Skeleton3D, a: Node3D, clip: StringName, root_name: StringName) -> bool:
	if p == null or s == null or a == null or not a.is_inside_tree() or not a.is_ancestor_of(s) or not a.is_ancestor_of(p) or not p.has_animation(clip): return false
	if not p.root_motion_track.is_empty() or s.show_rest_only or s.motion_scale != 1.0: return false
	var bone := s.find_bone(root_name)
	if bone < 0 or not rigid(a.global_transform) or not rigid(a.global_transform.affine_inverse() * s.global_transform): return false
	# Whole skeleton closure also preserves unweighted gameplay/attachment bones.
	for index in range(s.get_bone_count()):
		var parent := index
		while parent >= 0 and parent != bone: parent = s.get_bone_parent(parent)
		if parent != bone or not s.is_bone_enabled(index) or not rigid(s.get_bone_rest(index)) or not rigid(s.get_bone_pose(index)): return false
	var meshes := 0
	for node in nodes(a):
		if node is SkeletonModifier3D or node is AnimationTree: return false
		if node is Skeleton3D and node != s: return false
		if node is AnimationPlayer and node != p: return false
		if node is MeshInstance3D:
			if node.mesh == null or node.skin == null or node.get_node_or_null(node.skeleton) != s or node.get_blend_shape_count() != 0: return false
			meshes += 1
	if meshes == 0: return false
	var source := p.get_animation(clip)
	if not is_finite(source.length) or source.length <= 0.0 or source.loop_mode != Animation.LOOP_NONE or source.get_track_count() == 0: return false
	var root_node := p.get_node_or_null(p.root_node)
	if root_node == null: return false
	var skeleton_path := str(root_node.get_path_to(s))
	var targets := {}
	for track in range(source.get_track_count()):
		var path := source.track_get_path(track)
		var kind := source.track_get_type(track)
		if path.get_subname_count() != 1 or str(path.get_concatenated_names()) != skeleton_path or s.find_bone(path.get_subname(0)) < 0: return false
		if kind not in [Animation.TYPE_POSITION_3D, Animation.TYPE_ROTATION_3D, Animation.TYPE_SCALE_3D] or source.track_get_interpolation_type(track) != Animation.INTERPOLATION_LINEAR or source.track_get_key_count(track) == 0 or not source.track_is_enabled(track): return false
		var target := str(path) + ":" + str(kind)
		if targets.has(target): return false
		targets[target] = true
		var previous := -1.0
		for key in range(source.track_get_key_count(track)):
			var time := source.track_get_key_time(track, key)
			if not is_finite(time) or time < 0.0 or time > source.length or time <= previous: return false
			previous = time
			var value = source.track_get_key_value(track, key)
			if kind == Animation.TYPE_ROTATION_3D:
				if not value is Quaternion or not value.is_finite() or abs(value.length_squared() - 1.0) > 0.00001: return false
			else:
				if not value is Vector3 or not value.is_finite(): return false
				if kind == Animation.TYPE_SCALE_3D and value != Vector3.ONE: return false
	return true

func bind(p: AnimationPlayer, s: Skeleton3D, a: Node3D, clip: StringName, root_name: StringName, extract: bool = false) -> Error:
	# All eligibility checks precede scene/player mutation. No inferred root.
	if bound or not eligible(p, s, a, clip, root_name): return ERR_INVALID_PARAMETER
	player = p; skeleton = s; actor = a; root_bone = s.find_bone(root_name); extracted = extract
	animation = p.get_animation(clip).duplicate(true) as Animation
	placement = actor.global_transform
	relative = placement.affine_inverse() * skeleton.global_transform
	for bone in range(skeleton.get_bone_count()): base_poses.append(skeleton.get_bone_pose(bone))
	skeleton_version = skeleton.get_version()
	player.callback_mode_process = AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_MANUAL
	player.play(clip)
	_evaluate(0.0)
	anchor = relative * skeleton.get_bone_global_pose(root_bone)
	bound = true
	return seek_preview(0.0)

func _evaluate(seconds: float) -> void:
	# Restore ALL channels, including an unanimated root. Otherwise a previous
	# extraction leaks its anchored pose into subsequent native evaluations.
	for bone in range(base_poses.size()): skeleton.set_bone_pose(bone, base_poses[bone])
	Preview.seek(player, skeleton, animation, seconds)
	skeleton.force_update_all_bone_transforms()

func _sample(seconds: float) -> void:
	_evaluate(seconds)
	var original := relative * skeleton.get_bone_global_pose(root_bone)
	# Actor-local left action, NOT inverse(anchor)*original from reference tracks.
	root_motion_transform = original * anchor.affine_inverse()
	if extracted:
		skeleton.set_bone_global_pose(root_bone, relative.affine_inverse() * anchor)
		actor.global_transform = placement * root_motion_transform
	else:
		actor.global_transform = placement
	skeleton.force_update_all_bone_transforms()

func _valid(seconds: float) -> bool:
	return bound and is_finite(seconds) and seconds >= 0.0 and seconds <= animation.length and skeleton.get_version() == skeleton_version

func seek_preview(seconds: float) -> Error:
	# Silent arbitrary-order preview. Terminal native key is evaluated directly.
	if not _valid(seconds): return ERR_INVALID_PARAMETER
	_sample(seconds); time_s = seconds; root_motion_delta = Transform3D.IDENTITY
	return OK

func advance_to(seconds: float) -> Error:
	# Absolute clock prevents accumulated floating-point drift and early events.
	if not _valid(seconds) or seconds < time_s: return ERR_INVALID_PARAMETER
	if seconds == time_s:
		root_motion_delta = Transform3D.IDENTITY
		return OK
	var previous := root_motion_transform
	_sample(seconds); time_s = seconds
	root_motion_delta = previous.affine_inverse() * root_motion_transform
	return OK
