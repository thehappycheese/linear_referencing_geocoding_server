import math
from typing import NewType, Optional

from shapely.geometry import LineString

Radians = NewType("Radians", float)


def direction_of_linestring(line_string: LineString, normalised_distance_along: float) -> Optional[Radians]:
	linestring_coordinates = list(line_string.coords)
	direction = None
	de_normalised_distance_along = line_string.length * normalised_distance_along
	len_so_far = 0
	for vertex_a, vertex_b in zip(linestring_coordinates, linestring_coordinates[1:]):
		
		delta_x = vertex_b[0]-vertex_a[0]
		delta_y = vertex_b[1]-vertex_a[1]
		
		direction = math.atan2(delta_y, delta_x)
		len_so_far += math.sqrt(delta_x*delta_x + delta_y*delta_y)

		if len_so_far >= de_normalised_distance_along:
			break
	return direction
