extends SceneTree

class Recorder:
	extends RigidBody3D
	var owner_tree
	var tick := 0
	var observations: Array = []
	var done := false
	func _integrate_forces(state: PhysicsDirectBodyState3D) -> void:
		if done:
			return
		if tick == 0:
			state.transform = owner_tree.body_initial
			state.linear_velocity = Vector3.ZERO
			state.angular_velocity = Vector3.ZERO
		var moving := PhysicsServer3D.body_get_direct_state(owner_tree.moving.get_rid())
		var contacts: Array = []
		for i in range(state.get_contact_count()):
			contacts.append({"point":owner_tree.vec(state.get_contact_collider_position(i)),"velocity":owner_tree.vec(state.get_contact_collider_velocity_at_position(i))})
		observations.append({"tick":tick,"body_position":owner_tree.vec(state.transform.origin),"body_velocity":owner_tree.vec(state.linear_velocity),"collider_position":owner_tree.vec(moving.transform.origin),"collider_rotation":owner_tree.quat(moving.transform.basis.get_rotation_quaternion()),"collider_linear_velocity":owner_tree.vec(moving.linear_velocity),"collider_angular_velocity":owner_tree.vec(moving.angular_velocity),"contacts":contacts})
		if tick == owner_tree.request.steps:
			done = true
			owner_tree.call_deferred("finish")
		else:
			owner_tree.moving.transform = owner_tree.pose(tick+1)
		tick += 1

var request
var output: String
var moving: AnimatableBody3D
var recorder: Recorder
var body_initial := Transform3D(Basis.IDENTITY,Vector3(0,1.2,0))

func vec(v: Vector3) -> Array:
	return [v.x,v.y,v.z]

func quat(q: Quaternion) -> Array:
	return [q.x,q.y,q.z,q.w]

func pose(tick: int) -> Transform3D:
	var p = request.positions[tick+1]
	var q = request.rotations[tick+1]
	return Transform3D(Basis(Quaternion(q[0],q[1],q[2],q[3])),Vector3(p[0],p[1],p[2]))

func _initialize() -> void:
	call_deferred("start")

func start() -> void:
	var args := OS.get_cmdline_user_args()
	request = JSON.parse_string(FileAccess.get_file_as_string(args[0]))
	output = args[1]
	Engine.physics_ticks_per_second = request.fps
	moving = AnimatableBody3D.new()
	var shape := CollisionShape3D.new()
	var geometry := BoxShape3D.new()
	geometry.size = Vector3(2,.2,2)
	shape.shape = geometry
	moving.add_child(shape)
	moving.transform = pose(-1)
	root.add_child(moving)
	moving.transform = pose(0)
	recorder = Recorder.new()
	recorder.owner_tree = self
	recorder.can_sleep = false
	recorder.continuous_cd = true
	recorder.max_contacts_reported = 16
	recorder.contact_monitor = true
	recorder.linear_damp_mode = RigidBody3D.DAMP_MODE_REPLACE
	recorder.angular_damp_mode = RigidBody3D.DAMP_MODE_REPLACE
	recorder.linear_damp = 0
	recorder.angular_damp = 0
	var collider := CollisionShape3D.new()
	var box := BoxShape3D.new()
	box.size = Vector3(.2,.2,.2)
	collider.shape = box
	recorder.add_child(collider)
	recorder.transform = body_initial
	root.add_child(recorder)

func finish() -> void:
	var file := FileAccess.open(output,FileAccess.WRITE)
	file.store_string(JSON.stringify({"backend_setting":ProjectSettings.get_setting("physics/3d/physics_engine"),"direct_state_class":PhysicsServer3D.body_get_direct_state(moving.get_rid()).get_class(),"observations":recorder.observations}))
	file.close()
	quit()
