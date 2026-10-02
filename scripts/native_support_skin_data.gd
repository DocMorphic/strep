extends SceneTree

func matrix(t: Transform3D) -> Array:
	return [[t.basis.x.x,t.basis.x.y,t.basis.x.z], [t.basis.y.x,t.basis.y.y,t.basis.y.z], [t.basis.z.x,t.basis.z.y,t.basis.z.z], [t.origin.x,t.origin.y,t.origin.z]]

func descendants(node: Node) -> Array:
	var result: Array = [node]
	for child in node.get_children(): result.append_array(descendants(child))
	return result

func _initialize() -> void: call_deferred("run_audit")

func run_audit() -> void:
	var args := OS.get_cmdline_user_args()
	if args.size() != 2:
		push_error("Expected request and output paths"); quit(2); return
	var request = JSON.parse_string(FileAccess.get_file_as_string(args[0]))
	var report: Dictionary = {"engine":Engine.get_version_info(), "cases":[]}
	for item in request.cases:
		var document := GLTFDocument.new(); var state := GLTFState.new()
		if document.append_from_file(item.path,state) != OK:
			push_error("Support skin import failed"); quit(3); return
		var model := document.generate_scene(state,30.0,false,false); root.add_child(model)
		await process_frame
		var skeletons: Array = []
		for node in descendants(model):
			if node is Skeleton3D: skeletons.append(node)
		if skeletons.size() != 1:
			push_error("One imported skeleton required"); quit(4); return
		var skeleton: Skeleton3D = skeletons[0]; var surfaces: Array = []
		for node in descendants(model):
			if not node is MeshInstance3D: continue
			if node.skin == null or node.get_node(node.skeleton) != skeleton:
				push_error("Bound imported skin required"); quit(5); return
			var binds: Array = []
			for bind in range(node.skin.get_bind_count()):
				var bone: int = node.skin.get_bind_bone(bind)
				if str(node.skin.get_bind_name(bind)) != "": bone = skeleton.find_bone(node.skin.get_bind_name(bind))
				if bone < 0 or bone >= skeleton.get_bone_count():
					push_error("Invalid skin bone mapping"); quit(6); return
				binds.append({"bone":str(skeleton.get_bone_name(bone)), "pose":matrix(node.skin.get_bind_pose(bind))})
			for surface in range(node.mesh.get_surface_count()):
				var arrays: Array = node.mesh.surface_get_arrays(surface); var positions: Array = []
				if arrays[Mesh.ARRAY_BONES] == null or arrays[Mesh.ARRAY_WEIGHTS] == null:
					push_error("Missing skin influences"); quit(7); return
				for p in arrays[Mesh.ARRAY_VERTEX]: positions.append([p.x,p.y,p.z])
				surfaces.append({"name":str(node.name),"surface":surface,"positions":positions,"bones":Array(arrays[Mesh.ARRAY_BONES]),"weights":Array(arrays[Mesh.ARRAY_WEIGHTS]),"binds":binds})
		report.cases.append({"id":item.id,"path":item.path,"surfaces":surfaces})
		model.queue_free(); await process_frame
	var file := FileAccess.open(args[1],FileAccess.WRITE)
	file.store_string(JSON.stringify(report,"",true,true)); file.close(); quit(0)
