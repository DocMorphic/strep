extends SceneTree

func descendants(node: Node) -> Array:
	var found: Array = [node]
	for child in node.get_children(): found.append_array(descendants(child))
	return found

func transform_record(node: Node3D) -> Dictionary:
	var t := node.global_transform
	return {"translation_m": [t.origin.x,t.origin.y,t.origin.z],
		"basis_columns": [[t.basis.x.x,t.basis.x.y,t.basis.x.z],
		[t.basis.y.x,t.basis.y.y,t.basis.y.z],[t.basis.z.x,t.basis.z.y,t.basis.z.z]]}

func _initialize() -> void:
	call_deferred("audit")

func audit() -> void:
	var args := OS.get_cmdline_user_args()
	if args.size() != 2:
		quit(2)
		return
	var request = JSON.parse_string(FileAccess.get_file_as_string(args[0]))
	var report: Dictionary = {"engine": Engine.get_version_info(), "compression_disabled": true, "objects": []}
	for item in request.objects:
		var document := GLTFDocument.new()
		var state := GLTFState.new()
		if document.append_from_file(item.path, state, GLTFDocument.IMPORT_FLAG_FORCE_DISABLE_MESH_COMPRESSION) != OK:
			quit(3)
			return
		var model := document.generate_scene(state, 30.0, false, false)
		if model == null:
			quit(4)
			return
		var placement := Node3D.new()
		root.add_child(placement)
		placement.add_child(model)
		await process_frame
		var meshes: Array = []
		for node in descendants(model):
			if node is Skeleton3D or node is AnimationPlayer:
				quit(5)
				return
			if node is MeshInstance3D: meshes.append(node)
		if meshes.size() != 1 or meshes[0].mesh == null or meshes[0].mesh.get_surface_count() != 1:
			quit(6)
			return
		var node: MeshInstance3D = meshes[0]
		var mesh := node.mesh as ArrayMesh
		if mesh == null or mesh.surface_get_primitive_type(0) != Mesh.PRIMITIVE_TRIANGLES:
			quit(7)
			return
		var arrays := node.mesh.surface_get_arrays(0)
		var positions: Array = []
		var normals: Array = []
		var indices: Array = []
		for v in arrays[Mesh.ARRAY_VERTEX]: positions.append([v.x,v.y,v.z])
		for n in arrays[Mesh.ARRAY_NORMAL]: normals.append([n.x,n.y,n.z])
		if arrays[Mesh.ARRAY_INDEX] != null:
			for index in arrays[Mesh.ARRAY_INDEX]: indices.append(index)
		var poses: Array = [transform_record(node)]
		var p: Array = item.grounded_translation_m
		placement.position = Vector3(p[0],p[1],p[2])
		await process_frame
		poses.append(transform_record(node))
		report.objects.append({"id": item.id, "positions": positions, "normals": normals, "indices": indices, "poses": poses})
		placement.queue_free()
		await process_frame
	var output := FileAccess.open(args[1], FileAccess.WRITE)
	if output == null:
		quit(8)
		return
	output.store_string(JSON.stringify(report, "", true, true))
	output.close()
	quit(0)
