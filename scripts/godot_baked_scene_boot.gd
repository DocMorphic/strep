extends Node3D
## Game embedding: supply camera/rendering and consumers for confirmed intent.
signal gameplay(event: Dictionary)
const Loader = preload("godot_baked_scene_loader.gd")
var loaded := {}
var motion
var start_us := 0

func _ready() -> void:
	var config = JSON.parse_string(FileAccess.get_file_as_string("res://baked-runtime-v1/runtime.json"))
	if not config is Dictionary: set_process(false); return
	loaded=Loader.load_scene(self,"res://",config)
	if loaded.is_empty(): push_error("Baked scene validation failed"); set_process(false); return
	motion=loaded.player; motion.gameplay.connect(func(event): gameplay.emit(event)); start_us=Time.get_ticks_usec()

func _process(_delta: float) -> void:
	if motion==null: return
	var time: float = min(float(Time.get_ticks_usec()-start_us)/1000000.0,motion.duration_s)
	if not motion.advance_to(time).valid or time==motion.duration_s: set_process(false)

func _exit_tree() -> void:
	motion=null; loaded.clear()
