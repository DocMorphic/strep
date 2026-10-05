extends RigidBody3D
## Only the shared owner advances actors/props; each body integrates once.
var strep_manager: RefCounted
var strep_prop_id := ""

func _integrate_forces(state: PhysicsDirectBodyState3D) -> void:
	if strep_manager != null: strep_manager.integrate_body(self,state)
