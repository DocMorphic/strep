extends Node3D
## Embed this scene in your game; provide its camera and gameplay consumers.
signal gameplay(event: Dictionary)
const Loader = preload("godot_native_scene_loader.gd")
var motion
var started_us := 0

func _ready() -> void:
	var config = JSON.parse_string(FileAccess.get_file_as_string("res://runtime-v1/scene-runtime.json"))
	if not config is Dictionary:
		push_error("Strep scene settings are invalid"); set_process(false); return
	var loaded := Loader.load_scene(self, "res://", config)
	if loaded.is_empty():
		push_error("Strep scene/config/resource validation failed"); set_process(false); return
	motion = loaded.player
	motion.gameplay.connect(func(event): gameplay.emit(event))
	started_us = Time.get_ticks_usec()
	# Parent _ready() runs after child _ready(). Initial markers dispatch on the
	# first process tick, once the parent can connect its gameplay listener.

func _process(_delta: float) -> void:
	if motion == null: return
	var seconds := minf(float(Time.get_ticks_usec() - started_us) / 1000000.0, motion.times[-1])
	if not motion.advance_to(seconds).valid:
		push_error("Strep scene ownership/clock changed"); set_process(false)
