extends SceneTree
func _initialize() -> void: call_deferred("run")
func run() -> void:
	var args := OS.get_cmdline_user_args()
	var viewport := SubViewport.new()
	viewport.size=Vector2i(256,256)
	viewport.own_world_3d=true
	viewport.render_target_update_mode=SubViewport.UPDATE_ALWAYS
	root.add_child(viewport)
	var environment := WorldEnvironment.new()
	environment.environment=Environment.new()
	environment.environment.background_mode=Environment.BG_COLOR
	environment.environment.background_color=Color.BLACK
	viewport.add_child(environment)
	var mesh := MeshInstance3D.new()
	mesh.mesh=SphereMesh.new()
	var material := StandardMaterial3D.new()
	material.shading_mode=BaseMaterial3D.SHADING_MODE_UNSHADED
	material.albedo_color=Color.WHITE
	mesh.material_override=material
	viewport.add_child(mesh)
	var camera := Camera3D.new()
	viewport.add_child(camera)
	camera.position=Vector3(0,0,3)
	camera.look_at(Vector3.ZERO)
	camera.current=true
	for i in range(4):
		await process_frame
		RenderingServer.force_draw(false)
	var image := viewport.get_texture().get_image()
	assert(image != null and not image.is_empty())
	assert(image.save_png(args[0]+"/probe.png")==OK)
	var info := {"adapter":RenderingServer.get_video_adapter_name(),"vendor":RenderingServer.get_video_adapter_vendor(),"api":RenderingServer.get_video_adapter_api_version(),"driver":RenderingServer.get_current_rendering_driver_name(),"renderer":RenderingServer.get_current_rendering_method(),"display":DisplayServer.get_name(),"engine":Engine.get_version_info()}
	var file := FileAccess.open(args[0]+"/render-info.json",FileAccess.WRITE)
	file.store_string(JSON.stringify(info));file.close()
	viewport.queue_free()
	await process_frame
	quit(0)
