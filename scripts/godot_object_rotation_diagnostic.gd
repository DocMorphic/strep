extends SceneTree

func _initialize() -> void:
	call_deferred("run")

func run() -> void:
	var args := OS.get_cmdline_user_args()
	var document := GLTFDocument.new()
	var state := GLTFState.new()
	assert(document.append_from_file(args[0],state)==OK)
	var model := document.generate_scene(state,30.0,false,false)
	root.add_child(model)
	var player := model.find_child("AnimationPlayer",true,false) as AnimationPlayer
	var report: Array = []
	for name in player.get_animation_list():
		if name=="RESET":
			continue
		var animation := player.get_animation(name)
		for track in range(animation.get_track_count()):
			if not str(animation.track_get_path(track)).contains("Interaction_box") or animation.track_get_type(track)!=Animation.TYPE_ROTATION_3D:
				continue
			var keys: Array = []
			for key in range(animation.track_get_key_count(track)):
				var q: Quaternion = animation.track_get_key_value(track,key)
				keys.append({"time":animation.track_get_key_time(track,key),"q":[q.x,q.y,q.z,q.w]})
			report.append({"path":str(animation.track_get_path(track)),"keys":keys})
	var file := FileAccess.open(args[1],FileAccess.WRITE)
	file.store_string(JSON.stringify(report));file.close()
	quit()
