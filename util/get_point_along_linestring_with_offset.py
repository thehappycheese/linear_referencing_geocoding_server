import math
from typing import List, Tuple

from nicks_line_tools.Vector2 import Vector2
from nicks_line_tools.linestring_direction import linestring_direction
from nicks_line_tools.linestring_interpolate import linestring_interpolate_normalised
from nicks_line_tools.type_aliases import LineString

from util.convert_metres_to_degrees import convert_metres_to_degrees


def get_point_along_linestring_with_offset(line_string: LineString, linestring_slk_start: float, linestring_slk_end: float, slk_cut: float, offset_metres: float = 0) -> Vector2:
	distance_along_linestring_normalised = (slk_cut - linestring_slk_start) / (linestring_slk_end - linestring_slk_start)
	if offset_metres == 0:
		point = linestring_interpolate_normalised(
			line_string,
			distance_along_linestring_normalised
		)
	else:
		# With this offset method, error is introduced by sharp corners
		direction = linestring_direction(line_string, distance_along_linestring_normalised).left
		point = linestring_interpolate_normalised(line_string, distance_along_linestring_normalised)
		point = point + direction * convert_metres_to_degrees(offset_metres)
	
	return point
