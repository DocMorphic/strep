extends Node3D
## No process clock: the shared owner's body callbacks drive the native scene.
signal gameplay(event: Dictionary)
signal actions_applied(actions: Array)
signal sampled(record: Dictionary)
signal faulted(reason: String)
const Runtime = preload("godot_scene_prop_runtime.gd")
var runtime
var motion

func _ready() -> void:
	var config = JSON.parse_string(FileAccess.get_file_as_string("res://ownership-v1/prop-runtime.json"))
	if not config is Dictionary: faulted.emit("Invalid explicit prop settings"); return
	runtime=Runtime.new()
	if runtime.bind(self,"res://",config)!=OK:
		push_error(runtime.last_error); faulted.emit(runtime.last_error); runtime=null; return
	motion=runtime.loaded.player
	motion.gameplay.connect(func(event): gameplay.emit(event))
	runtime.owner.actions_applied.connect(func(actions): actions_applied.emit(actions))
	runtime.owner.sampled.connect(func(record): sampled.emit(record))
	runtime.owner.faulted.connect(func(reason): faulted.emit(reason))

func pause_playback() -> Error: return ERR_UNCONFIGURED if runtime==null else runtime.owner.pause_playback()
func resume_playback() -> Error: return ERR_UNCONFIGURED if runtime==null else runtime.owner.resume_playback()
func restart_playback() -> Error: return ERR_UNCONFIGURED if runtime==null else runtime.owner.restart_playback()
func preview_tick(tick: int) -> Error: return ERR_UNCONFIGURED if runtime==null else runtime.owner.preview_tick(tick)
