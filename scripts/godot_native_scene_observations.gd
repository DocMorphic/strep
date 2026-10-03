extends RefCounted
const Roots = preload("godot_native_root_adapter.gd")

static func vector(v: Vector3) -> Array: return [v.x, v.y, v.z]
static func matrix(v: Transform3D) -> Array: return [vector(v.basis.x), vector(v.basis.y), vector(v.basis.z), vector(v.origin)]

static func snapshot(scene) -> Dictionary:
	var actors := {}; var objects := {}; var deltas := {}
	for name in scene.actors:
		var helper = scene.actors[name]; var bones: Array = []; var mesh_world := {}
		for bone in range(helper.skeleton.get_bone_count()): bones.append(matrix(helper.skeleton.global_transform * helper.skeleton.get_bone_global_pose(bone)))
		for node in Roots.nodes(helper.actor):
			if node is MeshInstance3D: mesh_world[str(node.get_path())] = matrix(node.global_transform)
		actors[name] = {"time_s": scene.pose_time_s, "bones": bones, "skeleton_world": matrix(helper.skeleton.global_transform), "mesh_world": mesh_world, "actor_world": matrix(helper.actor.global_transform), "root_motion": matrix(helper.root_motion_transform), "root_delta": matrix(scene.root_deltas[name]), "root_in_actor": matrix(helper.actor.global_transform.affine_inverse() * helper.skeleton.global_transform * helper.skeleton.get_bone_global_pose(helper.root_bone))}
	for name in scene.props.objects: objects[name] = matrix(scene.props.objects[name].global_transform)
	for name in scene.root_deltas: deltas[name] = matrix(scene.root_deltas[name])
	return {"pose_time_s": scene.pose_time_s, "playback_time_s": scene.playback_time_s, "actors": actors, "objects": objects, "root_deltas": deltas}

static func skin_data(helper) -> Dictionary:
	var names: Array = []; var meshes: Array = []
	var skeleton: Skeleton3D = helper.skeleton
	for bone in range(skeleton.get_bone_count()): names.append(str(skeleton.get_bone_name(bone)))
	for node in Roots.nodes(helper.actor):
		if not node is MeshInstance3D: continue
		var binds: Array = []
		for bind in range(node.skin.get_bind_count()):
			var name := str(node.skin.get_bind_name(bind))
			var bone: int = skeleton.find_bone(name) if name != "" else node.skin.get_bind_bone(bind)
			if bone < 0 or bone >= names.size(): return {}
			binds.append({"bone": bone, "pose": matrix(node.skin.get_bind_pose(bind))})
		for surface in range(node.mesh.get_surface_count()):
			var arrays: Array = node.mesh.surface_get_arrays(surface); var positions: Array = []
			for point in arrays[Mesh.ARRAY_VERTEX]: positions.append(vector(point))
			meshes.append({"node": str(node.get_path()), "surface": surface, "binds": binds, "positions": positions, "weights": Array(arrays[Mesh.ARRAY_WEIGHTS]), "bones": Array(arrays[Mesh.ARRAY_BONES]), "primitive_type": node.mesh.surface_get_primitive_type(surface), "indices": Array(arrays[Mesh.ARRAY_INDEX]) if arrays[Mesh.ARRAY_INDEX] != null else []})
	return {"bone_names": names, "meshes": meshes, "channels": channels(helper.animation), "duration_s": helper.animation.length}

static func channels(animation: Animation) -> Array:
	var result: Array = []
	for track in range(animation.get_track_count()):
		var values: Array = []; var times: Array = []
		for key in range(animation.track_get_key_count(track)):
			times.append(animation.track_get_key_time(track, key)); var value = animation.track_get_key_value(track, key)
			values.append([value.x, value.y, value.z, value.w] if value is Quaternion else vector(value))
		result.append({"path": str(animation.track_get_path(track)), "type": animation.track_get_type(track), "times_s": times, "values": values})
	return result
