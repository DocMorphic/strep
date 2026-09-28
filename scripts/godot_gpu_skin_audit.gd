extends SceneTree
const Adapter = preload("godot_cycle_adapter.gd")
func nodes(n: Node) -> Array:
	var result: Array=[n]
	for child in n.get_children(): result.append_array(nodes(child))
	return result
func vector(a: Array) -> Vector3: return Vector3(a[0],a[1],a[2])
func _initialize() -> void: call_deferred("run")
func run() -> void:
	var args := OS.get_cmdline_user_args()
	var request = JSON.parse_string(FileAccess.get_file_as_string(args[0]))
	var output: Dictionary={"engine":Engine.get_version_info(),"adapter":RenderingServer.get_video_adapter_name(),"driver":RenderingServer.get_current_rendering_driver_name(),"renderer":RenderingServer.get_current_rendering_method(),"cases":[]}
	var viewport := SubViewport.new()
	viewport.size=Vector2i(512,512)
	viewport.own_world_3d=true
	viewport.render_target_update_mode=SubViewport.UPDATE_ALWAYS
	root.add_child(viewport)
	var world := Node3D.new();viewport.add_child(world)
	var env := WorldEnvironment.new();env.environment=Environment.new()
	env.environment.background_mode=Environment.BG_COLOR;env.environment.background_color=Color.BLACK
	world.add_child(env)
	var camera := Camera3D.new();world.add_child(camera)
	camera.projection=Camera3D.PROJECTION_ORTHOGONAL;camera.near=0.01;camera.far=100;camera.current=true
	var material := StandardMaterial3D.new()
	material.shading_mode=BaseMaterial3D.SHADING_MODE_UNSHADED
	material.albedo_color=Color.WHITE;material.cull_mode=BaseMaterial3D.CULL_DISABLED
	for item in request.cases:
		var points_data = JSON.parse_string(FileAccess.get_file_as_string(item.reference))
		var records: Array=[]
		for extract in [false,true]:
			var document := GLTFDocument.new();var state := GLTFState.new()
			assert(document.append_from_file(item.path,state)==OK)
			var actor := Node3D.new();world.add_child(actor)
			var placement := Transform3D(Basis(Vector3.UP,0.4),Vector3(2,0.3,-1));actor.transform=placement
			var model := document.generate_scene(state,30.0,false,false);actor.add_child(model)
			var player: AnimationPlayer;var skeleton: Skeleton3D
			var mesh_count := 0
			for node in nodes(model):
				if node is AnimationPlayer: player=node
				if node is Skeleton3D: skeleton=node
				if node is MeshInstance3D:
					node.material_override=material;mesh_count+=1
			assert(player != null and skeleton != null and mesh_count>0)
			var clip := ""
			for name in player.get_animation_list():
				if name != "RESET": clip=name
			var adapter := Adapter.new();actor.add_child(adapter)
			var data = JSON.parse_string(FileAccess.get_file_as_string(item.metadata))
			assert(adapter.bind_cycle(player,skeleton,actor,clip,data,item.path,extract)==OK)
			for sample in points_data.samples:
				assert(adapter.seek_preview(float(sample.frame)/30.0)==OK)
				actor.transform=placement*adapter.root_motion_transform if extract and not request.get("omit_root_control",false) else placement
				var arrays: Array=[];arrays.resize(Mesh.ARRAY_MAX)
				var vertices := PackedVector3Array()
				for p in sample.vertices: vertices.append(vector(p))
				arrays[Mesh.ARRAY_VERTEX]=vertices
				arrays[Mesh.ARRAY_INDEX]=PackedInt32Array(points_data.indices)
				var reference := MeshInstance3D.new();reference.mesh=ArrayMesh.new()
				reference.mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays)
				reference.material_override=material;world.add_child(reference)
				camera.size=float(sample.camera_size)
				var center := vector(sample.center)
				for view in range(request.views.size()):
					camera.position=center+vector(request.views[view])*5.0
					camera.look_at(center)
					var prefix: String=item.id+"-"+("extracted" if extract else "skeleton")+"-"+str(sample.index)+"-"+str(view)
					for kind in ["gpu","reference"]:
						actor.visible=kind=="gpu";reference.visible=kind=="reference"
						for tick in range(3):
							await process_frame
							RenderingServer.force_draw(false)
						var image := viewport.get_texture().get_image()
						assert(image != null and not image.is_empty())
						assert(image.save_png(args[1]+"/"+prefix+"-"+kind+".png")==OK)
					records.append({"prefix":prefix,"frame":sample.frame,"extracted":extract,"view":view,"imported_meshes":mesh_count})
				reference.queue_free();await process_frame
			actor.queue_free();await process_frame
		output.cases.append({"id":item.id,"records":records})
	var file := FileAccess.open(args[1]+"/engine-output.json",FileAccess.WRITE)
	file.store_string(JSON.stringify(output));file.close()
	viewport.queue_free();await process_frame
	quit(0)
