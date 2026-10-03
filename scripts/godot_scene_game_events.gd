extends RefCounted

const Clock = preload("native_engine_clock.gd")
var times := PackedFloat64Array()
var events: Array = []
var cursor: Variant = null

func configure(document: Dictionary) -> bool:
	if document.get("schema") != "strep-native-scene-game-events-v1" or not document.get("clock") is Dictionary or not document.get("events") is Array:
		return false
	var decoded := Clock.decode(document.clock, int(document.clock.get("count", 0)))
	if decoded.is_empty():
		return false
	var seen := {}
	var last_index := -1
	var checked: Array = []
	for entry in document.events:
		if not entry is Dictionary or not entry.get("id") is String or not entry.get("name") is String or not entry.get("actor") is String:
			return false
		var index_value = entry.get("sample_index")
		if typeof(index_value) not in [TYPE_INT, TYPE_FLOAT] or not is_finite(index_value) or index_value != int(index_value):
			return false
		var index := int(index_value)
		if index < last_index or index < 0 or index >= decoded.size() or seen.has(entry.id):
			return false
		if typeof(entry.get("timing_confirmed")) != TYPE_BOOL or typeof(entry.get("runtime_dispatch_allowed")) != TYPE_BOOL:
			return false
		if entry.get("kind") not in ["gameplay_intent", "contact_intent"]:
			return false
		if entry.runtime_dispatch_allowed != (entry.kind == "gameplay_intent" and entry.timing_confirmed):
			return false
		seen[entry.id] = true
		last_index = index
		var copy: Dictionary = entry.duplicate(true)
		copy.time_s = decoded[index] # Decimal JSON is descriptive; binary clock is authoritative.
		checked.append(copy)
	times = decoded
	events = checked
	cursor = null
	return true

func advance(time_s: float) -> Dictionary:
	if times.is_empty() or not is_finite(time_s) or time_s < 0.0 or time_s > times[-1] or (cursor != null and time_s < cursor):
		return {"valid": false, "events": []}
	var fired: Array = []
	for entry in events:
		if entry.runtime_dispatch_allowed and (cursor == null or entry.time_s > cursor) and entry.time_s <= time_s:
			fired.append(entry.duplicate(true))
	cursor = time_s
	return {"valid": true, "events": fired}

func reset() -> void:
	cursor = null
