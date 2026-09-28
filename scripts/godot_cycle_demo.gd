extends Node3D
const Adapter = preload("godot_cycle_adapter.gd")
var actor: Node3D
var adapter: Node
var initial := Transform3D.IDENTITY

func nodes(n: Node) -> Array:
	var found: Array=[n]
	for child in n.get_children(): found.append_array(nodes(child))
	return found

func _ready() -> void:
	actor=Node3D.new();add_child(actor)
	var document := GLTFDocument.new()
	var state := GLTFState.new()
	assert(document.append_from_file("res://character.glb",state)==OK)
	var model := document.generate_scene(state,30.0,false,false)
	actor.add_child(model)
	var player: AnimationPlayer
	var skeleton: Skeleton3D
	for node in nodes(model):
		if node is AnimationPlayer: player=node
		if node is Skeleton3D: skeleton=node
	assert(player != null and skeleton != null)
	var clip := ""
	for name in player.get_animation_list():
		if name != "RESET": clip=name
	adapter=Adapter.new();actor.add_child(adapter)
	var data = JSON.parse_string(FileAccess.get_file_as_string("res://runtime-cycle.json"))
	assert(adapter.bind_cycle(player,skeleton,actor,clip,data,"res://character.glb",true)==OK)
	adapter.marker.connect(func(event): print("STREP_MARKER ",event.name," ",event.cycle))
	var camera := Camera3D.new();add_child(camera);camera.position=Vector3(3,2,4);camera.look_at(Vector3(0,0.9,0));camera.current=true
	var light := DirectionalLight3D.new();add_child(light);light.rotation_degrees=Vector3(-50,-30,0);light.light_energy=1.5
	var environment := WorldEnvironment.new();environment.environment=Environment.new();environment.environment.background_mode=Environment.BG_COLOR;environment.environment.background_color=Color(0.25,0.28,0.32);environment.environment.ambient_light_source=Environment.AMBIENT_SOURCE_COLOR;environment.environment.ambient_light_color=Color.WHITE;environment.environment.ambient_light_energy=0.6;add_child(environment)
	var floor_mesh := MeshInstance3D.new();floor_mesh.mesh=PlaneMesh.new();floor_mesh.mesh.size=Vector2(20,20);add_child(floor_mesh)
	print("STREP_CYCLE_READY")

func _process(delta: float) -> void:
	if adapter == null: return
	assert(adapter.advance(delta)==OK)
	actor.transform=initial*adapter.root_motion_transform
