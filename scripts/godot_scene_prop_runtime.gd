extends RefCounted
## Source meshes remain hidden authored references; physical copies own visibility.
const Loader = preload("godot_native_scene_loader.gd")
const Owner = preload("godot_scene_prop_owner.gd")
const Body = preload("godot_scene_prop_body.gd")
var loaded: Dictionary = {}
var owner
var config: Dictionary = {}
var bones: Dictionary = {}
var bodies: Dictionary = {}
var last_error := ""
var collision_settings: Dictionary = {}

static func profile_settings(name: String,rate: int) -> Dictionary:
	if name not in ["engine-default","ccd-threshold","strict-ccd"]: return {}
	var p := "physics/jolt_physics_3d/"
	return {
		p+"simulation/continuous_cd_movement_threshold":0.75 if name=="engine-default" else 0.05,
		p+"simulation/continuous_cd_max_penetration":0.01 if name=="strict-ccd" else 0.25,
		p+"simulation/penetration_slop":0.001,p+"simulation/baumgarte_stabilization_factor":0.2,
		p+"simulation/position_steps":2,p+"simulation/velocity_steps":10,
		p+"collisions/collision_margin_fraction":0.0,p+"simulation/speculative_contact_distance":0.02,
		"physics/common/physics_ticks_per_second":rate,"physics/3d/default_gravity":9.81}

func check_collision_profile(document: Dictionary) -> bool:
	collision_settings.clear()
	if not document.has("collision_profile"): return true
	var profile = document.collision_profile
	if not profile is Dictionary or profile.size()!=3 or profile.get("backend")!="Jolt Physics" or not profile.get("name") is String or not profile.get("settings") is Dictionary: return false
	var expected := profile_settings(profile.name,int(document.physics_fps))
	if expected.is_empty() or expected.size()!=profile.settings.size() or ProjectSettings.get_setting("physics/3d/physics_engine")!="Jolt Physics": return false
	for key in expected:
		var declared = profile.settings.get(key)
		var actual = ProjectSettings.get_setting(key)
		if typeof(declared) not in [TYPE_INT,TYPE_FLOAT] or not is_finite(declared) or declared!=expected[key]: return false
		if typeof(actual) not in [TYPE_INT,TYPE_FLOAT] or not is_finite(actual) or abs(actual-expected[key])>1e-7: return false
		collision_settings[key]=actual
	return true

static func integer(value: Variant,low: int,high: int) -> bool:
	return typeof(value) in [TYPE_INT,TYPE_FLOAT] and is_finite(value) and value==floor(value) and value>=low and value<=high

static func transform(rows: Variant) -> Variant:
	if not rows is Array or rows.size()!=4: return null
	for row in rows:
		if not row is Array or row.size()!=4: return null
		for value in row:
			if typeof(value) not in [TYPE_INT,TYPE_FLOAT] or not is_finite(value): return null
	if rows[3][0]!=0.0 or rows[3][1]!=0.0 or rows[3][2]!=0.0 or rows[3][3]!=1.0: return null
	var result := Loader.matrix(rows)
	return result if Owner.rigid(result) else null

static func geometry(value: Variant) -> Shape3D:
	if not value is Dictionary or value.get("schema")!="strep-object-geometry-v1": return null
	var shape: Shape3D
	if value.get("shape")=="box":
		if value.size()!=3 or not value.get("size_m") is Array or value.size_m.size()!=3: return null
		for v in value.size_m:
			if typeof(v) not in [TYPE_INT,TYPE_FLOAT] or not is_finite(v) or v<=0: return null
		shape=BoxShape3D.new(); shape.size=Vector3(value.size_m[0],value.size_m[1],value.size_m[2])
	elif value.get("shape") in ["sphere","cylinder"]:
		var radius = value.get("radius_m")
		if typeof(radius) not in [TYPE_INT,TYPE_FLOAT] or not is_finite(radius) or radius<=0: return null
		if value.shape=="sphere":
			if value.size()!=3: return null
			shape=SphereShape3D.new(); shape.radius=radius
		else:
			var height = value.get("height_m")
			if value.size()!=4 or typeof(height) not in [TYPE_INT,TYPE_FLOAT] or not is_finite(height) or height<=0: return null
			shape=CylinderShape3D.new(); shape.radius=radius; shape.height=height
	else: return null
	return shape

func discard() -> void:
	# This object owns only its staged container, never existing game nodes.
	if loaded.has("container") and is_instance_valid(loaded.container): loaded.container.free()
	loaded.clear(); bodies.clear(); bones.clear(); owner=null

func grip(key: String,prop: String) -> Transform3D:
	var binding: Dictionary = config.grip_bindings[key]
	var helper = loaded.player.actors[binding.actor]
	return helper.skeleton.global_transform*helper.skeleton.get_bone_global_pose(bones[key])*Loader.matrix(binding.prop_offsets[prop])

func bind(parent: Node3D,folder: String,document: Dictionary) -> Error:
	last_error="Source participant/physics preflight rejected"
	if not loaded.is_empty() or parent==null or not parent.is_inside_tree() or not Owner.rigid(parent.global_transform): return ERR_INVALID_PARAMETER
	if document.get("schema")!="strep-scene-prop-runtime-v1" or not document.get("native_scene") is Dictionary or not document.get("object_modes") is Dictionary or not document.get("grip_bindings") is Dictionary or not document.get("props") is Dictionary or not document.get("ownership") is Dictionary: return ERR_INVALID_DATA
	last_error="Physics step/history configuration differs from the running project"
	if not integer(document.get("physics_fps"),60,240) or int(document.physics_fps) not in [60,120,240] or int(document.physics_fps)!=Engine.physics_ticks_per_second or not integer(document.get("history_capacity"),2,3600): return ERR_INVALID_DATA
	last_error="Declared collision profile differs from the actual running project"
	if not check_collision_profile(document): return ERR_INVALID_DATA
	last_error="Ownership events cannot satisfy the declared physical timing"
	if document.has("physical_timing") and not Owner.checked_timing(document.get("ownership",{}),document.physical_timing,int(document.physics_fps)): return ERR_INVALID_DATA
	var scene_path := Loader.checked_path(folder,document.native_scene.get("scene",{}))
	if scene_path.is_empty(): return ERR_INVALID_DATA
	var intent = JSON.parse_string(FileAccess.get_file_as_string(scene_path))
	last_error="Complete source object/actor/ownership population required"
	if not intent is Dictionary or not intent.get("objects") is Dictionary or not intent.get("actors") is Dictionary or not document.ownership.get("objects") is Array or not document.ownership.get("grips") is Dictionary: return ERR_INVALID_DATA
	if document.object_modes.size()!=intent.objects.size() or document.grip_bindings.size()!=document.ownership.grips.size(): return ERR_INVALID_DATA
	var selected: Array = []; var shapes := {}; var poses := {}; var inertias := {}
	for id in document.object_modes:
		last_error="Invalid authored/physical mode or source geometry: "+id
		if not intent.objects.has(id) or document.object_modes[id] not in ["authored","grip-physics"]: return ERR_INVALID_DATA
		if document.object_modes[id]=="authored": continue
		selected.append(id)
		var prop = document.props.get(id)
		if not prop is Dictionary or not prop.get("physics") is Dictionary or prop.get("geometry")!=intent.objects[id].get("geometry"): return ERR_INVALID_DATA
		var shape := geometry(prop.geometry); var pose = transform(prop.get("initial_pose"))
		var physics: Dictionary = prop.physics; var mass = physics.get("mass_kg")
		last_error="Invalid rigid prop pose/shape/mass: "+id
		if shape==null or pose==null or physics.size()!=7 or typeof(mass) not in [TYPE_INT,TYPE_FLOAT] or not is_finite(mass) or mass<0.001 or mass>10000: return ERR_INVALID_DATA
		for field in ["friction","restitution","linear_damping","angular_damping"]:
			last_error="Invalid prop physics field: "+id+"/"+field
			var value = physics.get(field)
			if typeof(value) not in [TYPE_INT,TYPE_FLOAT] or not is_finite(value) or value<0 or value>(100 if field.ends_with("damping") else 1): return ERR_INVALID_DATA
		for field in ["collision_layer","collision_mask"]:
			last_error="Invalid collision bitfield: "+id+"/"+field
			if not integer(physics.get(field),0,4294967295): return ERR_INVALID_DATA
		var inertia: Vector3
		if shape is BoxShape3D:
			var size: Vector3 = shape.size
			inertia=Vector3(size.y*size.y+size.z*size.z,size.x*size.x+size.z*size.z,size.x*size.x+size.y*size.y)*float(mass)/12.0
		elif shape is SphereShape3D: inertia=Vector3.ONE*(0.4*float(mass)*shape.radius*shape.radius)
		else: inertia=Vector3(float(mass)*(3*shape.radius*shape.radius+shape.height*shape.height)/12.0,float(mass)*shape.radius*shape.radius/2.0,float(mass)*(3*shape.radius*shape.radius+shape.height*shape.height)/12.0)
		var authored_inertia = prop.get("inertia_diagonal")
		last_error="Prop inertia differs from uniform source geometry: "+id
		if not authored_inertia is Array or authored_inertia.size()!=3: return ERR_INVALID_DATA
		for i in range(3):
			if typeof(authored_inertia[i]) not in [TYPE_INT,TYPE_FLOAT] or not is_finite(authored_inertia[i]) or abs(authored_inertia[i]-inertia[i])>max(1e-7,abs(inertia[i])*1e-6): return ERR_INVALID_DATA
		shapes[id]=shape; poses[id]=pose; inertias[id]=inertia
	selected.sort()
	last_error="Physical prop mode/ownership populations differ"
	if selected.is_empty() or selected!=document.ownership.objects or document.props.size()!=selected.size(): return ERR_INVALID_DATA
	for key in document.grip_bindings:
		last_error="Explicit grip/source actor contract differs: "+key
		var binding = document.grip_bindings[key]
		if not binding is Dictionary or binding.size()!=6 or not document.ownership.grips.has(key) or document.ownership.grips[key].get("actor")!=binding.get("actor") or not intent.actors.has(binding.get("actor")): return ERR_INVALID_DATA
		var actor: Dictionary = intent.actors[binding.actor]
		last_error="Grip joint/animation/source metadata differs: "+key
		if binding.get("character_glb_sha256")!=actor.get("sha256") or binding.get("animation_index")!=actor.get("animation_index") or not integer(binding.get("joint_node"),0,2147483647) or not binding.get("bone") is String or not binding.get("prop_offsets") is Dictionary: return ERR_INVALID_DATA
		for id in binding.prop_offsets:
			last_error="Invalid prop-center grip offset: "+key+"/"+id
			if id not in selected or transform(binding.prop_offsets[id])==null: return ERR_INVALID_DATA
		for group in document.ownership.get("groups",[]):
			last_error="Commanded grip lacks an explicit prop offset: "+key
			for transition in group.get("transitions",[]):
				for command in transition.get("changes",[]):
					if command.get("grip")==key and not binding.prop_offsets.has(command.get("object")): return ERR_INVALID_DATA
	# Native importer stages a new container; failed bindings discard it wholly.
	last_error="Native actor/object source import rejected"
	loaded=Loader.load_scene(parent,folder,document.native_scene)
	if loaded.is_empty(): return ERR_INVALID_DATA
	config=document.duplicate(true)
	for key in config.grip_bindings:
		last_error="Exact source joint binding rejected: "+key
		var binding: Dictionary = config.grip_bindings[key]; var helper = loaded.player.actors[binding.actor]
		var bone: int = helper.skeleton.find_bone(binding.bone)
		# Verify the exact GLB node/name mapping, not only an imported string match.
		var asset: Dictionary = {}
		for a in config.native_scene.actors:
			if a.id==binding.actor: asset=a.asset
		var gltf := GLTFDocument.new(); var state := GLTFState.new()
		if bone<0 or gltf.append_from_file(Loader.checked_path(folder,asset),state)!=OK or int(binding.joint_node)>=state.get_nodes().size() or state.get_nodes()[int(binding.joint_node)].original_name!=binding.bone or state.get_nodes()[int(binding.joint_node)].skeleton<0:
			discard(); return ERR_INVALID_DATA
		bones[key]=bone
	for id in selected:
		last_error="Source prop placement/geometry rejected: "+id
		if not loaded.objects.get(id) is MeshInstance3D: discard(); return ERR_INVALID_DATA
		var original: MeshInstance3D = loaded.objects[id]
		var initial: Transform3D = parent.global_transform*poses[id]
		if original.global_transform.origin.distance_to(initial.origin)>0.00003 or not original.global_transform.basis.is_equal_approx(initial.basis): discard(); return ERR_INVALID_DATA
		var prop: Dictionary = config.props[id]; var body = Body.new(); body.name="Physical_"+id; body.mass=prop.physics.mass_kg; body.inertia=inertias[id]
		body.collision_layer=int(prop.physics.collision_layer); body.collision_mask=int(prop.physics.collision_mask); body.continuous_cd=true; body.max_contacts_reported=16; body.contact_monitor=true
		body.linear_damp_mode=RigidBody3D.DAMP_MODE_REPLACE; body.angular_damp_mode=RigidBody3D.DAMP_MODE_REPLACE
		body.linear_damp=prop.physics.linear_damping; body.angular_damp=prop.physics.angular_damping
		var material := PhysicsMaterial.new(); material.friction=prop.physics.friction; material.bounce=prop.physics.restitution; body.physics_material_override=material
		var collision := CollisionShape3D.new(); collision.shape=shapes[id]; body.add_child(collision)
		var mesh := MeshInstance3D.new(); mesh.mesh=original.mesh; mesh.material_override=original.material_override; body.add_child(mesh)
		body.set_meta("strep_collider_id",id); loaded.container.add_child(body); body.global_transform=initial; bodies[id]=body
	var providers := {}
	for key in config.grip_bindings: providers[key]=func(id: String) -> Transform3D: return grip(key,id)
	owner=Owner.new()
	last_error="Shared native scene owner rejected explicit membership/clock binding"
	if owner.bind(loaded.player,config.ownership,bodies,providers,int(config.physics_fps),int(config.history_capacity),config.get("physical_timing"))!=OK: discard(); return ERR_INVALID_DATA
	for id in selected: loaded.objects[id].visible=false
	last_error=""
	return OK
