import math

EARTH_RADIUS_METRES = 6.3781e6
EARTH_METRES_PER_RADIAN = EARTH_RADIUS_METRES
EARTH_METRES_PER_DEGREE = EARTH_METRES_PER_RADIAN * math.pi / 180

# yes I know the earth is an oblate spheroid, but the difference is very small...
# (the difference between equatorial diameter subtract polar diameter) divided by the equatorial diameter = 0.003
# if we assume the equatorial diameter is 6.3781e6 metres then the polar diameter would be 20km less
# in any case, the conversion below is used for offsetting small distances from lines stored in lat / lng degrees format, and is never used to convert to/from absolute coordinates in metres.
# therefore since it is used to perform a relative offset we can expect the error in the resulting geometry to be vanishingly small as long as the offsets are in the order of metres and not kilometres


def convert_metres_to_degrees(metres: float):
	return metres / EARTH_METRES_PER_DEGREE