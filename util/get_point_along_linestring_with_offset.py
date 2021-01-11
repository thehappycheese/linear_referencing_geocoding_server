import math

from shapely.geometry import LineString, Point

from util.direction_of_linestring import direction_of_linestring
from util.convert_metres_to_degrees import convert_metres_to_degrees

OFFSET_BY_INSTANTANEOUS_DIRECTION = True


def get_point_along_linestring_with_offset(line_string: LineString, linestring_slk_start: float, linestring_slk_end: float, slk_cut: float, offset_metres: float = 0) -> Point:
	distance_along_linestring_normalised = (slk_cut - linestring_slk_start) / (linestring_slk_end - linestring_slk_start)
	
	if offset_metres == 0:
		point = line_string.interpolate(
			distance_along_linestring_normalised,
			normalized=True
		)
	else:
		if OFFSET_BY_INSTANTANEOUS_DIRECTION:
			# With this offset method, error is introduced by sharp corners
			direction = direction_of_linestring(line_string, distance_along_linestring_normalised)
			x_offset = math.sin(direction) * convert_metres_to_degrees(offset_metres)
			y_offset = -math.cos(direction) * convert_metres_to_degrees(offset_metres)
			point = line_string.interpolate(
				distance_along_linestring_normalised,
				normalized=True
			)
			point = Point(point.coords[0][0] + x_offset, point.coords[0][1] + y_offset)
		else:
			# TODO: the alternate method above is safer. consider deleting this branch.
			# With this offset method, error is introduced by uneven introduction of extra length in offset linestring at curved corners, plus there is extra effort to offset the entire linestring
			offset_linestring = line_string.parallel_offset(
				abs(convert_metres_to_degrees(offset_metres)),
				side=('left' if offset_metres < 0 else 'right')
			)
			if isinstance(offset_linestring, LineString):
				point = offset_linestring.interpolate(
					distance_along_linestring_normalised,
					normalized=True
				)
			else:
				# Sometimes offset will result in a multi line string. the above may just work anyway... but behaviour is undocumented. Error is safer.
				raise Exception("could not offset point as offset linestring resulted in a multilinestring.")
	return point
