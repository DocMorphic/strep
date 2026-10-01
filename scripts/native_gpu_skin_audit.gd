extends SceneTree

func nodes(node: Node) -> Array:
	var result: Array = [node]
	for child in node.get_children(): result.append_array(nodes(child))
	return result

func vector(a: Array) -> Vector3: return Vector3(a[0], a[1], a[2])
func matrix(t: Transform3D) -> Array:
	return [[t.basis.x.x,t.basis.x.y,t.basis.x.z], [t.basis.y.x,t.basis.y.y,t.basis.y.z], [t.basis.z.x,t.basis.z.y,t.basis.z.z], [t.origin.x,t.origin.y,t.origin.z]]
func _initialize() -> void: call_deferred("run")

func run() -> void:
	var args := OS.get_cmdline_user_args()
	var request = JSON.parse_string(FileAccess.get_file_as_string(args[0]))
	var output: Dictionary = {"engine":Engine.get_version_info(), "adapter":RenderingServer.get_video_adapter_name(), "driver":RenderingServer.get_current_rendering_driver_name(), "renderer":RenderingServer.get_current_rendering_method(), "cases":[]}
	var viewport := SubViewport.new(); viewport.size = Vector2i(512,512)
	viewport.own_world_3d = true; viewport.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	root.add_child(viewport)
	var world := Node3D.new(); viewport.add_child(world)
	var environment := WorldEnvironment.new(); environment.environment = Environment.new()
	environment.environment.background_mode = Environment.BG_COLOR
	environment.environment.background_color = Color.BLACK; world.add_child(environment)
	var camera := Camera3D.new(); world.add_child(camera)
	camera.projection = Camera3D.PROJECTION_ORTHOGONAL; camera.near = 0.01; camera.far = 100; camera.current = true
	var material := StandardMaterial3D.new(); material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	material.albedo_color = Color.WHITE; material.cull_mode = BaseMaterial3D.CULL_DISABLED
	for item in request.cases:
		var reference_data = JSON.parse_string(FileAccess.get_file_as_string(item.reference))
		var records: Array = []; var imported_surfaces: Array = []
		for broken in [false,true]:
			var document := GLTFDocument.new(); var state := GLTFState.new()
			assert(document.append_from_file(item.path,state) == OK)
			var actor := Node3D.new(); world.add_child(actor)
			var rotation: Array = item.placement.rotation_xyzw
			actor.quaternion = Quaternion(rotation[0],rotation[1],rotation[2],rotation[3]); actor.position = vector(item.placement.translation_m)
			var model := document.generate_scene(state,30.0,false,false); actor.add_child(model)
			var player: AnimationPlayer; var skeleton: Skeleton3D
			for node in nodes(model):
				if node is AnimationPlayer: player = node
				if node is Skeleton3D: skeleton = node
			assert(player != null and skeleton != null)
			var changed := 0
			for node in nodes(model):
				if node is MeshInstance3D:
					node.material_override = material
					assert(node.skin != null and node.get_node(node.skeleton) == skeleton)
					if broken: node.skin = node.skin.duplicate()
					var binds: Array = []
					for bind in range(node.skin.get_bind_count()):
						var bone: int = node.skin.get_bind_bone(bind)
						if str(node.skin.get_bind_name(bind)) != "": bone = skeleton.find_bone(node.skin.get_bind_name(bind))
						assert(bone >= 0 and bone < skeleton.get_bone_count())
						if broken and skeleton.get_bone_name(bone) == "LeftForeArm":
							var pose: Transform3D = node.skin.get_bind_pose(bind); pose.origin.x += 0.05
							node.skin.set_bind_pose(bind,pose); changed += 1
						binds.append({"bone":str(skeleton.get_bone_name(bone)), "pose":matrix(node.skin.get_bind_pose(bind))})
					if not broken:
						for surface in range(node.mesh.get_surface_count()):
							var arrays: Array = node.mesh.surface_get_arrays(surface); var positions: Array = []
							for p in arrays[Mesh.ARRAY_VERTEX]: positions.append([p.x,p.y,p.z])
							imported_surfaces.append({"name":str(node.name),"surface":surface,"positions":positions,"bones":Array(arrays[Mesh.ARRAY_BONES]),"weights":Array(arrays[Mesh.ARRAY_WEIGHTS]),"binds":binds})
			assert(not broken or changed > 0)
			var animation := ResourceLoader.load(item.animation,"Animation",ResourceLoader.CACHE_MODE_IGNORE) as Animation
			assert(animation != null)
			for library_name in player.get_animation_library_list(): player.remove_animation_library(library_name)
			var library := AnimationLibrary.new(); assert(library.add_animation("Native",animation) == OK)
			assert(player.add_animation_library("",library) == OK)
			player.callback_mode_process = AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_MANUAL; player.play("Native")
			for sample in reference_data.samples:
				if broken and not sample.is_event: continue
				player.seek(float(sample.time_s),true)
				var arrays: Array = []; arrays.resize(Mesh.ARRAY_MAX)
				var vertices := PackedVector3Array()
				for p in sample.vertices: vertices.append(vector(p))
				arrays[Mesh.ARRAY_VERTEX] = vertices; arrays[Mesh.ARRAY_INDEX] = PackedInt32Array(reference_data.indices)
				var reference := MeshInstance3D.new(); reference.mesh = ArrayMesh.new()
				reference.mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays); reference.material_override = material; world.add_child(reference)
				for framing in ["body","hand"]:
					if broken and framing != "hand": continue
					camera.size = float(sample.body_size if framing == "body" else 0.30)
					var center := vector(sample.body_center if framing == "body" else sample.hand_center)
					for view in range(request.views.size()):
						camera.position = center+vector(request.views[view])*5.0; camera.look_at(center)
						var prefix: String = item.id+"-"+("broken" if broken else "native")+"-"+str(sample.index)+"-"+framing+"-"+str(view)
						for kind in ["gpu","reference"]:
							actor.visible = kind == "gpu"; reference.visible = kind == "reference"
							for tick in range(3):
								await process_frame; RenderingServer.force_draw(false)
							var image := viewport.get_texture().get_image(); assert(image != null and not image.is_empty())
							assert(image.save_png(args[1]+"/"+prefix+"-"+kind+".png") == OK)
						records.append({"prefix":prefix,"time_s":sample.time_s,"actual_time_s":player.current_animation_position,"sample":sample.index,"framing":framing,"view":view,"broken":broken,"changed_binds":changed})
				reference.queue_free(); await process_frame
			actor.queue_free(); await process_frame
		output.cases.append({"id":item.id,"surfaces":imported_surfaces,"records":records})
	var file := FileAccess.open(args[1]+"/engine-output.json",FileAccess.WRITE)
	file.store_string(JSON.stringify(output,"",true,true)); file.close()
	viewport.queue_free(); await process_frame; quit(0)
