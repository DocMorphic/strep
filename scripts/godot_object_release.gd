extends SceneTree

class Recorder:
	extends RigidBody3D
	var request: Dictionary
	var observations: Array = []
	var tick: int = 0
	var finished: bool = false

	func vector(values: Array) -> Vector3:
		return Vector3(values[0], values[1], values[2])

	func _integrate_forces(state: PhysicsDirectBodyState3D) -> void:
		if finished:
			return
		if tick == 0:
			var q = request.rotation_xyzw
			state.transform = Transform3D(Basis(Quaternion(q[0],q[1],q[2],q[3])),vector(request.position_m))
			state.linear_velocity = vector(request.linear_velocity_m_s)
			state.angular_velocity = vector(request.angular_velocity_rad_s)
		var p := state.transform.origin
		var q := state.transform.basis.get_rotation_quaternion()
		var v := state.linear_velocity
		var w := state.angular_velocity
		var gravity := state.total_gravity
		var inverse := state.inverse_inertia
		var contacts: Array = []
		for index in range(state.get_contact_count()):
			var collider := state.get_contact_collider_object(index)
			contacts.append(str(collider.get_meta("strep_collider_id","unknown")) if collider != null else "unknown")
		observations.append({"tick":tick,"step_s":state.step,
			"moving_colliders":get_tree().moving_states(),
			"position_m":[p.x,p.y,p.z],"rotation_xyzw":[q.x,q.y,q.z,q.w],
			"linear_velocity_m_s":[v.x,v.y,v.z],"angular_velocity_rad_s":[w.x,w.y,w.z],
			"contact_count":state.get_contact_count(),"contact_colliders":contacts,"gravity_m_s2":[gravity.x,gravity.y,gravity.z],
			"inverse_mass":state.inverse_mass,"inverse_inertia":[inverse.x,inverse.y,inverse.z],
			"linear_damp":state.total_linear_damp,"angular_damp":state.total_angular_damp})
		if tick == int(request.steps):
			finished = true
			get_tree().call_deferred("finish_recording")
		else:
			get_tree().advance_moving(tick+1)
		tick += 1

var recorder: Recorder
var request: Dictionary
var output_path: String
var static_bodies: Array = []
var moving_bodies: Array = []

func vec(v: Vector3) -> Array:
	return [v.x,v.y,v.z]

func quat(q: Quaternion) -> Array:
	return [q.x,q.y,q.z,q.w]

func moving_pose(item: Dictionary, tick: int) -> Transform3D:
	var q = item.rotations_xyzw[tick+1]
	return Transform3D(Basis(Quaternion(q[0],q[1],q[2],q[3])),vector(item.positions_m[tick+1]))

func advance_moving(tick: int) -> void:
	for i in range(moving_bodies.size()):
		moving_bodies[i].transform = moving_pose(request.moving_colliders[i],tick)

func moving_states() -> Array:
	var states: Array = []
	for body in moving_bodies:
		var state := PhysicsServer3D.body_get_direct_state(body.get_rid())
		states.append({"id":str(body.get_meta("strep_collider_id")),"position_m":vec(state.transform.origin),"rotation_xyzw":quat(state.transform.basis.get_rotation_quaternion()),"center_of_mass_local_m":vec(state.center_of_mass_local),"linear_velocity_m_s":vec(state.linear_velocity),"angular_velocity_rad_s":vec(state.angular_velocity)})
	return states

func vector(values: Array) -> Vector3:
	return Vector3(values[0],values[1],values[2])

func primitive_shape(item: Dictionary) -> Shape3D:
	var descriptor: Dictionary = item.get("geometry", {"shape":"box","size_m":item.get("size_m",[])})
	if descriptor.shape == "sphere":
		var sphere := SphereShape3D.new()
		sphere.radius = descriptor.radius_m
		return sphere
	if descriptor.shape == "cylinder":
		var cylinder := CylinderShape3D.new()
		cylinder.radius = descriptor.radius_m
		cylinder.height = descriptor.height_m
		return cylinder
	var box := BoxShape3D.new()
	box.size = vector(descriptor.size_m)
	return box

func geometry_record(shape: Shape3D) -> Dictionary:
	if shape is SphereShape3D:
		return {"schema":"strep-object-geometry-v1","shape":"sphere","radius_m":shape.radius}
	if shape is CylinderShape3D:
		return {"schema":"strep-object-geometry-v1","shape":"cylinder","radius_m":shape.radius,"height_m":shape.height}
	return {"schema":"strep-object-geometry-v1","shape":"box","size_m":vec(shape.size)}

func _initialize() -> void:
	call_deferred("start_recording")

func start_recording() -> void:
	var args := OS.get_cmdline_user_args()
	if args.size()!=2:
		quit(2)
		return
	request = JSON.parse_string(FileAccess.get_file_as_string(args[0]))
	output_path = args[1]
	Engine.physics_ticks_per_second = int(request.physics_fps)
	Engine.max_physics_steps_per_frame = 16
	var material := PhysicsMaterial.new()
	material.friction = request.friction
	material.bounce = request.restitution
	if request.floor_enabled:
		var floor_body := StaticBody3D.new()
		floor_body.set_meta("strep_collider_id","floor")
		var floor_shape := CollisionShape3D.new()
		var plane := WorldBoundaryShape3D.new()
		plane.plane = Plane(Vector3.UP,request.floor_height_m)
		floor_shape.shape = plane
		floor_body.add_child(floor_shape)
		floor_body.physics_material_override = material
		root.add_child(floor_body)
	for item in request.get("static_colliders",[]):
		var body := StaticBody3D.new()
		body.set_meta("strep_collider_id",item.id)
		var shape := CollisionShape3D.new()
		var geometry := primitive_shape(item)
		shape.shape = geometry
		body.add_child(shape)
		var surface := PhysicsMaterial.new()
		surface.friction = item.friction
		surface.bounce = item.restitution
		body.physics_material_override = surface
		var rotation = item.rotation_xyzw
		body.transform = Transform3D(Basis(Quaternion(rotation[0],rotation[1],rotation[2],rotation[3])),vector(item.position_m))
		root.add_child(body)
		static_bodies.append(body)
	for item in request.get("moving_colliders",[]):
		var body := AnimatableBody3D.new()
		body.set_meta("strep_collider_id",item.id)
		var shape := CollisionShape3D.new()
		var geometry
		if item.get("shape","box") == "convex":
			geometry = ConvexPolygonShape3D.new()
			var points := PackedVector3Array()
			for point in item.points_m:
				points.append(vector(point))
			geometry.points = points
		else:
			geometry = primitive_shape(item)
		shape.shape = geometry
		body.add_child(shape)
		var surface := PhysicsMaterial.new()
		surface.friction = item.friction
		surface.bounce = item.restitution
		body.physics_material_override = surface
		body.transform = moving_pose(item,-1)
		root.add_child(body)
		if item.get("shape","box") == "convex":
			PhysicsServer3D.body_set_param(body.get_rid(),PhysicsServer3D.BODY_PARAM_CENTER_OF_MASS,vector(item.center_of_mass_local_m))
		body.transform = moving_pose(item,0)
		moving_bodies.append(body)
	recorder = Recorder.new()
	recorder.request = request
	recorder.mass = request.mass_kg
	recorder.inertia = vector(request.inertia_diagonal_kg_m2)
	recorder.can_sleep = false
	recorder.continuous_cd = true
	recorder.max_contacts_reported = 16
	recorder.contact_monitor = true
	recorder.linear_damp_mode = RigidBody3D.DAMP_MODE_REPLACE
	recorder.angular_damp_mode = RigidBody3D.DAMP_MODE_REPLACE
	recorder.linear_damp = 0
	recorder.angular_damp = 0
	recorder.physics_material_override = material
	var collision := CollisionShape3D.new()
	collision.shape = primitive_shape(request)
	recorder.add_child(collision)
	# Set the initial placement before activation, then reset it once in the
	# first callback. Subsequent ticks are advanced solely by the engine.
	var q = request.rotation_xyzw
	recorder.transform = Transform3D(Basis(Quaternion(q[0],q[1],q[2],q[3])),vector(request.position_m))
	root.add_child(recorder)

func finish_recording() -> void:
	var moving_geometry: Array = []
	for body in moving_bodies:
		var geometry = body.get_child(0).shape
		var entry := {"id":str(body.get_meta("strep_collider_id")),"friction":body.physics_material_override.friction,"restitution":body.physics_material_override.bounce}
		if geometry is ConvexPolygonShape3D:
			var points: Array = []
			for point in geometry.points:
				points.append(vec(point))
			entry.shape = "convex"
			entry.points_m = points
		else:
			if request.moving_colliders[moving_geometry.size()].has("geometry"):
				entry.geometry = geometry_record(geometry)
			else:
				entry.size_m = vec(geometry.size)
		moving_geometry.append(entry)
	var colliders: Array = []
	for body in static_bodies:
		var p: Vector3 = body.position
		var q: Quaternion = body.quaternion
		var entry := {"id":str(body.get_meta("strep_collider_id")),"position_m":[p.x,p.y,p.z],"rotation_xyzw":[q.x,q.y,q.z,q.w],"friction":body.physics_material_override.friction,"restitution":body.physics_material_override.bounce}
		if request.static_colliders[colliders.size()].has("geometry"):
			entry.geometry = geometry_record(body.get_child(0).shape)
		else:
			entry.size_m = vec(body.get_child(0).shape.size)
		colliders.append(entry)
	var report := {"engine":Engine.get_version_info(),
		"released_geometry":geometry_record(recorder.get_child(0).shape),
		"moving_colliders":moving_geometry,
		"direct_state_class":PhysicsServer3D.body_get_direct_state(recorder.get_rid()).get_class(),
		"collision_margin_fraction":ProjectSettings.get_setting("physics/jolt_physics_3d/collisions/collision_margin_fraction"),
		"static_colliders":colliders,
		"backend":ProjectSettings.get_setting("physics/3d/physics_engine"),
		"contact_max_allowed_penetration_m":ProjectSettings.get_setting("physics/jolt_physics_3d/simulation/penetration_slop") if request.get("backend","GodotPhysics3D") == "Jolt Physics" else PhysicsServer3D.space_get_param(recorder.get_world_3d().space,PhysicsServer3D.SPACE_PARAM_CONTACT_MAX_ALLOWED_PENETRATION),
		"physics_fps":Engine.physics_ticks_per_second,"observations":recorder.observations}
	if request.get("backend","GodotPhysics3D") == "Jolt Physics":
		report.contact_max_allowed_penetration_m = ProjectSettings.get_setting("physics/jolt_physics_3d/simulation/penetration_slop")
	var file := FileAccess.open(output_path,FileAccess.WRITE)
	if file == null:
		quit(3)
		return
	file.store_string(JSON.stringify(report))
	file.close()
	quit(0)
