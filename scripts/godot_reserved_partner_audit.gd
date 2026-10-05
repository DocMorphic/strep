extends SceneTree

func descendants(node: Node) -> Array:
	var found: Array = [node]
	for child in node.get_children(): found.append_array(descendants(child))
	return found

func vector(v: Vector3) -> Array: return [v.x,v.y,v.z]
func matrix(t: Transform3D) -> Array: return [vector(t.basis.x),vector(t.basis.y),vector(t.basis.z),vector(t.origin)]
func _initialize() -> void: call_deferred("audit")

func audit() -> void:
	var args := OS.get_cmdline_user_args()
	if args.size() != 2:
		quit(2)
		return
	var request = JSON.parse_string(FileAccess.get_file_as_string(args[0]))
	var report: Dictionary = {"engine":Engine.get_version_info(),"compression_disabled":true,"gpu_skin_baked":false,"animation_played":false,"pairs":[]}
	for item in request.pairs:
		var holder := Node3D.new()
		root.add_child(holder)
		var actors: Dictionary = {}
		for name in ["A","B"]:
			var entry = item.actors[name]
			var document := GLTFDocument.new()
			var state := GLTFState.new()
			if document.append_from_file(entry.path,state,GLTFDocument.IMPORT_FLAG_FORCE_DISABLE_MESH_COMPRESSION) != OK:
				quit(3)
				return
			var model := document.generate_scene(state,30.0,false,false)
			if model == null:
				quit(4)
				return
			var placement := Node3D.new()
			holder.add_child(placement)
			var p: Array = entry.placement.translation_m
			var q: Array = entry.placement.rotation_xyzw
			placement.transform = Transform3D(Basis(Quaternion(q[0],q[1],q[2],q[3])),Vector3(p[0],p[1],p[2]))
			placement.add_child(model)
			await process_frame
			var skeletons: Array = []
			var nonreset: Array = []
			for node in descendants(model):
				if node is Skeleton3D: skeletons.append(node)
				if node is AnimationPlayer:
					for clip in node.get_animation_list():
						if clip != "RESET": nonreset.append(str(clip))
			if skeletons.size() != 1 or nonreset.size() != 0:
				quit(5)
				return
			var skeleton: Skeleton3D = skeletons[0]
			var names: Array = []
			var parents: Array = []
			var bones: Array = []
			for bone in range(skeleton.get_bone_count()):
				names.append(str(skeleton.get_bone_name(bone)))
				parents.append(skeleton.get_bone_parent(bone))
				bones.append(matrix(skeleton.global_transform*skeleton.get_bone_global_pose(bone)))
			var meshes: Array = []
			var mesh_world: Array = []
			for node in descendants(model):
				if not node is MeshInstance3D: continue
				if node.mesh == null or node.skin == null or node.get_node_or_null(node.skeleton) != skeleton:
					quit(6)
					return
				var binds: Array = []
				for bind in range(node.skin.get_bind_count()):
					var bind_name := str(node.skin.get_bind_name(bind))
					var bone: int = skeleton.find_bone(bind_name) if bind_name != "" else node.skin.get_bind_bone(bind)
					if bone < 0 or bone >= names.size():
						quit(7)
						return
					binds.append({"bone":bone,"pose":matrix(node.skin.get_bind_pose(bind))})
				mesh_world.append({"node":str(node.get_path()),"matrix":matrix(node.global_transform)})
				for surface in range(node.mesh.get_surface_count()):
					var arrays: Array = node.mesh.surface_get_arrays(surface)
					if arrays[Mesh.ARRAY_WEIGHTS] == null or arrays[Mesh.ARRAY_BONES] == null:
						quit(8)
						return
					var points: Array = []
					for v in arrays[Mesh.ARRAY_VERTEX]: points.append(vector(v))
					meshes.append({"node":str(node.get_path()),"surface":surface,"positions":points,
						"bones":Array(arrays[Mesh.ARRAY_BONES]),"weights":Array(arrays[Mesh.ARRAY_WEIGHTS]),"binds":binds,
						"indices":Array(arrays[Mesh.ARRAY_INDEX]) if arrays[Mesh.ARRAY_INDEX] != null else [],
						"primitive_type":node.mesh.surface_get_primitive_type(surface)})
			if meshes.size() == 0:
				quit(9)
				return
			actors[name] = {"rig_id":entry.rig_id,"bone_names":names,"bone_parents":parents,"bones_world":bones,
				"placement_world":matrix(placement.global_transform),"skeleton_world":matrix(skeleton.global_transform),
				"mesh_world":mesh_world,"meshes":meshes,"nonreset_animations":nonreset}
		report.pairs.append({"id":item.id,"actors":actors})
		holder.queue_free()
		await process_frame
	var output := FileAccess.open(args[1],FileAccess.WRITE)
	if output == null:
		quit(10)
		return
	output.store_string(JSON.stringify(report,"",true,true))
	output.close()
	quit(0)
