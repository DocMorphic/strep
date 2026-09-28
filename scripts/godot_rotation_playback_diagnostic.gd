extends SceneTree

func matrix(b: Basis) -> Array:
	return [[b.x.x,b.x.y,b.x.z],[b.y.x,b.y.y,b.y.z],[b.z.x,b.z.y,b.z.z]]

func quat(q: Quaternion) -> Array:
	return [q.x,q.y,q.z,q.w]

func _initialize() -> void:
	call_deferred("run")

func run() -> void:
	var args := OS.get_cmdline_user_args()
	var document := GLTFDocument.new()
	var state := GLTFState.new()
	assert(document.append_from_file(args[0],state)==OK)
	var model := document.generate_scene(state,30.0,false,false)
	root.add_child(model)
	await process_frame
	var player := model.find_child("AnimationPlayer",true,false) as AnimationPlayer
	var target := model.find_child(args[2],true,false) as Node3D
	var report: Array = []
	for name in player.get_animation_list():
		if name=="RESET":
			continue
		var animation := player.get_animation(name)
		player.callback_mode_process = AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_MANUAL
		player.play(name)
		for track in range(animation.get_track_count()):
			if not str(animation.track_get_path(track)).contains(args[2]) or animation.track_get_type(track)!=Animation.TYPE_ROTATION_3D:
				continue
			var keys: Array = []
			for key in range(animation.track_get_key_count(track)):
				var q: Quaternion = animation.track_get_key_value(track,key)
				keys.append({"time":animation.track_get_key_time(track,key),"q":quat(q)})
			var samples: Array = []
			for frame in range(keys.size()):
				var time := float(frame)/30.0
				var q := animation.rotation_track_interpolate(track,time)
				player.seek(time,true,true)
				samples.append({"frame":frame,"interpolated":quat(q),"interpolated_basis":matrix(Basis(q)),"actual_q":quat(target.quaternion),"actual_basis":matrix(target.basis),"rotation_edit_mode":target.rotation_edit_mode})
			report.append({"path":str(animation.track_get_path(track)),"keys":keys,"samples":samples})
	var file := FileAccess.open(args[1],FileAccess.WRITE)
	file.store_string(JSON.stringify(report));file.close()
	quit()
