extends RefCounted

# Explicit f64 little-endian protocol. Decimal JSON clocks remain descriptive.
static func decode(value: Dictionary, count: int) -> PackedFloat64Array:
	var result := PackedFloat64Array()
	if value.size() != 3 or value.get("schema") != "strep-native-engine-clock-f64le-v1" or value.get("count") != count or count < 2:
		return result
	var encoded = value.get("bytes_hex")
	if not encoded is String or encoded.length() != count * 16:
		return result
	var bytes: PackedByteArray = encoded.hex_decode()
	if bytes.size() != count * 8 or bytes.hex_encode() != encoded:
		return result
	for i in range(count):
		var time := bytes.decode_double(i * 8)
		if not is_finite(time) or time < 0.0 or (i == 0 and time != 0.0) or (i > 0 and time <= result[i - 1]):
			return PackedFloat64Array()
		result.append(time)
	return result
