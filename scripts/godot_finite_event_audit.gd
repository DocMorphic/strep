extends "godot_event_object_audit.gd"

func world_bones() -> Array:
	grip()
	var values: Array=[]
	for index in range(skeleton.get_bone_count()): values.append(serial(skeleton.global_transform*skeleton.get_bone_global_pose(index)))
	return values

func start_case() -> void:
	super.start_case()
	var forward: Array=[];var reverse: Array=[];var ended: Array=[]
	var on_forward := func(event): forward.append(event.duplicate(true))
	var on_reverse := func(event): reverse.append(event.duplicate(true))
	var on_end := func(): ended.append(clock.time_s)
	clock.marker.connect(on_forward);clock.marker_reversed.connect(on_reverse);clock.clip_finished.connect(on_end)
	assert(clock.restart(true)==OK)
	assert(clock.advance(clock.last_sample_s)==OK)
	var terminal := world_bones()
	assert(clock.advance(clock.duration_s*3)==OK)
	assert(clock.advance(clock.duration_s)==OK)
	var after := world_bones()
	var before_count := forward.size()
	assert(clock.seek_preview(clock.last_sample_s)==OK)
	assert(clock.seek_preview(clock.duration_s*5)==OK)
	var silent := forward.size()==before_count and ended.size()==1
	assert(clock.rewind(clock.time_s,true)==OK)
	var errors: Array=[clock.advance(-1.0),clock.seek_preview(-1.0),clock.rewind(1.0,true)]
	var unchanged: bool=clock.time_s==0.0
	assert(clock.restart(false)==OK)
	clock.marker.disconnect(on_forward);clock.marker_reversed.disconnect(on_reverse);clock.clip_finished.disconnect(on_end)
	result.clock_contract={"forward":forward,"reverse":reverse,"finished":ended,"terminal_bones":terminal,"held_bones":after,"silent_seek":silent,"invalid_errors":errors,"invalid_unchanged":unchanged}
