extends Node
## One finite clock for all placed actors and baked object tracks.
## Marker signals describe authored intent; they do not transfer physics ownership.
signal marker(event: Dictionary)
signal marker_reversed(event: Dictionary)
signal finished
signal sampled(seconds: float)
var bound := false
var updating := false
var time_s := 0.0
var correction := 0.0
var duration_s := 0.0
var last_sample_s := 0.0
var playing := false
var speed := 1.0
var notify_reverse := false
var last_error := ""
var actors: Dictionary = {}
var objects: Dictionary = {}
var players: Array = []
var markers: Array = []
var scene_root: Node3D

func reject(reason: String) -> Error:
	last_error=reason
	return ERR_INVALID_DATA

func nodes(node: Node) -> Array:
	var result: Array=[node]
	for child in node.get_children(): result.append_array(nodes(child))
	return result

func valid_file(folder: String, entry: Dictionary) -> bool:
	var path=entry.get("path")
	if not path is String or path.is_empty() or path.is_absolute_path() or ":" in path or "\\" in path: return false
	for part in path.split("/"):
		if part in ["", ".", ".."]: return false
	return entry.get("sha256") is String and FileAccess.get_sha256(folder.path_join(path))==entry.sha256

func decode_pose(value: Dictionary) -> Variant:
	var p=value.get("translation_m");var q=value.get("rotation_xyzw")
	if not p is Array or p.size()!=3 or not q is Array or q.size()!=4: return null
	for x in p+q:
		if not (x is float or x is int) or not is_finite(float(x)): return null
	var rotation:=Quaternion(q[0],q[1],q[2],q[3])
	if abs(rotation.length()-1.0)>0.00001: return null
	return Transform3D(Basis(rotation),Vector3(p[0],p[1],p[2]))

func restore_curves(path: String, source_hash: String, animation: Animation) -> bool:
	var data=JSON.parse_string(FileAccess.get_file_as_string(path))
	if not data is Dictionary or data.get("schema")!="strep-animation-curves-v1" or data.get("source_sha256")!=source_hash or not data.get("channels") is Array: return false
	if abs(float(data.get("duration_s",-1))-animation.length)>0.00001: return false
	var used: Dictionary={}
	var types={"translation":Animation.TYPE_POSITION_3D,"rotation":Animation.TYPE_ROTATION_3D,"scale":Animation.TYPE_SCALE_3D}
	for channel in data.channels:
		if not channel is Dictionary or not types.has(channel.get("path")) or channel.get("interpolation") not in ["LINEAR","STEP"] or channel.get("target_kind") not in ["bone","node"]: return false
		var found: Array=[]
		for i in range(animation.get_track_count()):
			if animation.track_get_type(i)!=types[channel.path]: continue
			var target:=animation.track_get_path(i)
			var name=""
			if channel.target_kind=="bone" and target.get_subname_count()>0: name=str(target.get_subname(target.get_subname_count()-1))
			elif channel.target_kind=="node" and target.get_subname_count()==0 and target.get_name_count()>0: name=str(target.get_name(target.get_name_count()-1))
			if name==channel.get("node_name"): found.append(i)
		if found.size()!=1 or used.has(found[0]): return false
		var track: int=found[0];used[track]=true
		var times=channel.get("times_s");var values=channel.get("values")
		if not times is Array or not values is Array or times.size()!=values.size() or times.size()<2: return false
		var previous:=-1.0;var decoded: Array=[]
		for i in range(times.size()):
			if not (times[i] is int or times[i] is float) or not is_finite(float(times[i])) or times[i]<0 or times[i]<=previous or times[i]>animation.length+0.00001: return false
			previous=float(times[i]);var value=values[i]
			if not value is Array or value.size()!=(4 if channel.path=="rotation" else 3): return false
			for component in value:
				if not (component is int or component is float) or not is_finite(float(component)): return false
			if channel.path=="rotation":
				var q:=Quaternion(value[0],value[1],value[2],value[3])
				if abs(q.length()-1)>0.00001:return false
				decoded.append(q)
			else:decoded.append(Vector3(value[0],value[1],value[2]))
		for i in range(animation.track_get_key_count(track)-1,-1,-1):animation.track_remove_key(track,i)
		animation.track_set_interpolation_type(track,Animation.INTERPOLATION_NEAREST if channel.interpolation=="STEP" else Animation.INTERPOLATION_LINEAR)
		animation.track_set_interpolation_loop_wrap(track,false)
		for i in range(times.size()):
			if channel.path=="rotation":animation.rotation_track_insert_key(track,times[i],decoded[i])
			elif channel.path=="translation":animation.position_track_insert_key(track,times[i],decoded[i])
			else:animation.scale_track_insert_key(track,times[i],decoded[i])
		# Godot may merge extremely close keys; reject instead of changing a jump.
		if animation.track_get_key_count(track)!=times.size(): return false
		for i in range(times.size()):
			if abs(animation.track_get_key_time(track,i)-float(times[i]))>1e-12: return false
	return used.size()==animation.get_track_count()

func import_clip(path: String, end: float, precise_mesh: bool = false, bake_fps: float = 30.0, curves_path: String = "", source_hash: String = "") -> Dictionary:
	if not is_finite(bake_fps) or bake_fps<0.01 or bake_fps>30000: return {}
	var document:=GLTFDocument.new();var state:=GLTFState.new()
	var flags := GLTFDocument.IMPORT_FLAG_FORCE_DISABLE_MESH_COMPRESSION if precise_mesh else 0
	if document.append_from_file(path,state,flags)!=OK: return {}
	# Retain constant scale tracks: rigid objects must keep quaternion rotation.
	var model:=document.generate_scene(state,bake_fps,false,false)
	if model==null: return {}
	var found: Array=[];var skeletons: Array=[]
	for node in nodes(model):
		if node is AnimationPlayer: found.append(node)
		if node is Skeleton3D: skeletons.append(node)
	if found.size()!=1: model.free();return {}
	var player: AnimationPlayer=found[0];var clips: Array=[]
	for name in player.get_animation_list():
		if name!="RESET": clips.append(name)
	if clips.size()!=1: model.free();return {}
	var animation:=player.get_animation(clips[0])
	if animation.loop_mode!=Animation.LOOP_NONE or abs(animation.length-end)>0.00001: model.free();return {}
	if not curves_path.is_empty() and not restore_curves(curves_path,source_hash,animation): model.free();return {}
	player.callback_mode_process=AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_MANUAL
	player.play(clips[0])
	return {"model":model,"player":player,"skeletons":skeletons}

func bind_package(folder: String, parent: Node3D) -> Error:
	if bound or parent==null or not parent.is_inside_tree(): return ERR_INVALID_PARAMETER
	var data=JSON.parse_string(FileAccess.get_file_as_string(folder.path_join("scene-runtime.json")))
	if not data is Dictionary or data.get("schema") not in ["strep-runtime-scene-v1","strep-runtime-scene-v2","strep-runtime-scene-v3"] or data.get("fps")!=30: return reject("Invalid scene runtime schema/fps")
	var frames:=float(data.get("frames",0))
	if not is_finite(frames) or frames!=floor(frames) or frames<3 or frames>1800: return reject("Invalid finite scene length")
	if not data.get("actors") is Dictionary or data.actors.size()<1 or data.actors.size()>4 or not data.get("objects") is Dictionary or data.objects.size()>8 or not data.get("markers") is Array: return reject("Invalid scene population")
	for actor in data.actors.values():
		if not actor is Dictionary or not valid_file(folder,actor) or not actor.get("placement") is Dictionary or decode_pose(actor.placement)==null: return reject("Actor hash/path/placement failed")
		if actor.has("curves") and (data.schema!="strep-runtime-scene-v3" or not actor.curves is Dictionary or not valid_file(folder,actor.curves)): return reject("Actor curve hash/path failed")
	if not data.objects.is_empty():
		if not data.get("object_clip") is Dictionary or not valid_file(folder,data.object_clip): return reject("Object clip hash/path failed")
		if data.object_clip.has("curves") and (data.schema!="strep-runtime-scene-v3" or not data.object_clip.curves is Dictionary or not valid_file(folder,data.object_clip.curves)): return reject("Object curve hash/path failed")
		for entry in data.objects.values():
			if not entry is Dictionary or entry.get("ownership")!="baked_track" or not entry.get("node_name") is String: return reject("Object ownership must remain baked_track")
	var previous:=-1.0
	var ids: Dictionary={}
	for event in data.markers:
		if not event is Dictionary or not event.get("id") is String or event.id.is_empty() or ids.has(event.id) or not event.get("payload") is Dictionary: return reject("Invalid marker identity/payload")
		var frame:=float(event.get("frame",-1))
		if not (event.get("frame") is int or event.get("frame") is float) or not is_finite(frame) or (data.schema=="strep-runtime-scene-v1" and frame!=floor(frame)) or frame<0 or frame>frames or frame<previous: return reject("Invalid marker clock/order")
		if event.payload.has("actor") and not data.actors.has(event.payload.actor): return reject("Unknown marker actor")
		if event.payload.has("object") and not data.objects.has(event.payload.object): return reject("Unknown marker object")
		ids[event.id]=true;previous=frame
	# Stage every import before exposing any actor in the user's scene.
	var staged:=Node3D.new();staged.name="StrepScene"
	var actor_nodes: Dictionary={};var object_nodes: Dictionary={};var staged_players: Array=[]
	for id in data.actors:
		var entry: Dictionary=data.actors[id]
		var imported:=import_clip(folder.path_join(entry.path),(frames-1)/30.0,false,float(entry.get("bake_fps",30.0)),folder.path_join(entry.curves.path) if entry.has("curves") else "",entry.sha256)
		if imported.is_empty(): staged.free();return reject("Actor animation import failed: "+id)
		if imported.skeletons.size()!=1: imported.model.free();staged.free();return reject("Actor requires one skeleton: "+id)
		var placement:=Node3D.new();placement.transform=decode_pose(entry.placement)
		staged.add_child(placement);placement.add_child(imported.model)
		actor_nodes[id]={"placement":placement,"model":imported.model,"skeleton":imported.skeletons[0],"player":imported.player}
		staged_players.append(imported.player)
	if not data.objects.is_empty():
		var imported:=import_clip(folder.path_join(data.object_clip.path),(frames-1)/30.0,true,float(data.object_clip.get("bake_fps",30.0)),folder.path_join(data.object_clip.curves.path) if data.object_clip.has("curves") else "",data.object_clip.sha256)
		if imported.is_empty(): staged.free();return reject("Object animation import failed")
		staged.add_child(imported.model);staged_players.append(imported.player)
		for id in data.objects:
			var found: Array=[]
			for node in nodes(imported.model):
				if node is Node3D and str(node.name)==data.objects[id].node_name: found.append(node)
			if found.size()!=1: staged.free();return reject("Object node missing/ambiguous: "+id)
			object_nodes[id]=found[0]
	parent.add_child(staged)
	scene_root=staged;actors=actor_nodes;objects=object_nodes;players=staged_players;markers=data.markers.duplicate(true)
	last_sample_s=(frames-1)/30.0;duration_s=frames/30.0;bound=true
	return seek_preview(0.0)

func sample(seconds: float, notify: bool=true) -> void:
	# Pose every participant before any sampled/marker/completion callback.
	for player in players: player.seek(minf(seconds,last_sample_s),true,true)
	for actor in actors.values(): actor.skeleton.force_update_all_bone_transforms()
	time_s=seconds
	if notify: sampled.emit(seconds)

func seek_preview(seconds: float) -> Error:
	if updating: return ERR_BUSY
	if not bound or not is_finite(seconds) or seconds<0 or seconds>duration_s: return ERR_INVALID_PARAMETER
	updating=true;playing=false;correction=0.0;sample(seconds);updating=false
	return OK

func dispatch(event: Dictionary, direction: int) -> void:
	var value:=event.duplicate(true);value.time_s=float(event.frame)/30.0;value.observed_at_s=time_s
	if direction>0: marker.emit(value)
	else: value.direction=-1;marker_reversed.emit(value)

func restart(dispatch_initial: bool=false) -> Error:
	var error:=seek_preview(0.0)
	if error!=OK: return error
	if dispatch_initial:
		updating=true
		for event in markers:
			if event.frame==0: dispatch(event,1)
		updating=false
	return OK

func advance(seconds: float) -> Error:
	if updating: return ERR_BUSY
	if not bound or not is_finite(seconds) or seconds<0 or seconds>3600: return ERR_INVALID_PARAMETER
	if seconds==0: return OK
	updating=true
	var before:=time_s;var increment:=seconds-correction;var raw:=before+increment
	var after:=duration_s if raw>=duration_s-1e-12 else raw;correction=(raw-before)-increment if after<duration_s else 0.0
	for event in markers:
		var at:=float(event.frame)/30.0
		if at>before and at<=after:
			sample(at,false);dispatch(event,1)
	sample(after)
	if after==duration_s:
		playing=false
		if before<duration_s: finished.emit()
	updating=false
	return OK

func rewind(seconds: float, notifications: bool=false) -> Error:
	if updating: return ERR_BUSY
	if not bound or not is_finite(seconds) or seconds<0 or seconds>3600: return ERR_INVALID_PARAMETER
	if seconds==0: return OK
	updating=true
	var before:=time_s;var increment:=-seconds-correction;var raw:=before+increment
	var after:=0.0 if raw<=1e-12 else raw;correction=(raw-before)-increment if after>0 else 0.0
	if notifications:
		for i in range(markers.size()-1,-1,-1):
			var event: Dictionary=markers[i];var at:=float(event.frame)/30.0
			if (at>=after and at<before) or (before==duration_s and at==duration_s):
				sample(at,false);dispatch(event,-1)
	sample(after)
	if after==0: playing=false
	updating=false
	return OK

func play(rate: float=1.0, reverse_notifications: bool=false) -> Error:
	if updating: return ERR_BUSY
	if not bound or not is_finite(rate) or rate==0 or abs(rate)>4: return ERR_INVALID_PARAMETER
	speed=rate;notify_reverse=reverse_notifications;playing=true
	return OK

func pause() -> void:
	playing=false

func _physics_process(delta: float) -> void:
	if playing:
		if speed>0: advance(delta*speed)
		else: rewind(delta*-speed,notify_reverse)

func unload() -> Error:
	if updating: return ERR_BUSY
	playing=false;bound=false;players.clear();actors.clear();objects.clear();markers.clear()
	if is_instance_valid(scene_root): scene_root.queue_free()
	scene_root=null;time_s=0.0;correction=0.0
	return OK

func _exit_tree() -> void:
	if is_instance_valid(scene_root) and not scene_root.is_queued_for_deletion(): scene_root.queue_free()
