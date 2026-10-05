extends SceneTree
const Tracks = preload("native_godot_tracks.gd")
const Roots = preload("godot_native_root_adapter.gd")

func fail(message: String) -> void:
	push_error(message); quit(2)

func _initialize() -> void: call_deferred("prepare")

func prepare() -> void:
	var args := OS.get_cmdline_user_args()
	if args.size() != 2: fail("Two prepare paths required"); return
	var request = JSON.parse_string(FileAccess.get_file_as_string(args[0]))
	var document := GLTFDocument.new(); var state := GLTFState.new()
	if document.append_from_file(request.glb, state) != OK: fail("Transferred rig import failed"); return
	var animations := state.get_animations()
	var index := int(request.animation_index)
	if index < 0 or index >= animations.size(): fail("Transferred clip missing"); return
	var selected: Array[GLTFAnimation] = [animations[index]]; state.set_animations(selected)
	var model := document.generate_scene(state, 30.0, false, false)
	if model == null: fail("Transferred model generation failed"); return
	root.add_child(model)
	await process_frame
	var players: Array = []; var skeletons: Array = []
	for node in Roots.nodes(model):
		if node is AnimationPlayer: players.append(node)
		if node is Skeleton3D: skeletons.append(node)
	if players.size() != 1 or skeletons.size() != 1: fail("One transferred skeleton/player required"); return
	var payload = JSON.parse_string(FileAccess.get_file_as_string(request.payload))
	if Tracks.install(players[0], skeletons[0], payload, request.animation_resource) != OK:
		fail("Transferred native resource installation failed"); return
	var file := FileAccess.open(args[1], FileAccess.WRITE)
	file.store_string(JSON.stringify({"status":"complete", "engine":Engine.get_version_info(), "resource_sha256":FileAccess.get_sha256(request.animation_resource), "source_animation_count":animations.size(), "selected_animation_index":index}))
	file.close(); model.free(); quit(0)
