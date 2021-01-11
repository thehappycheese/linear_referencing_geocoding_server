import math
from typing import Tuple, Optional

from shapely.geometry import LineString, Point


def cut_linestring(linestring: LineString, linestring_start_slk: float, linestring_end_slk: float, slk_at_which_to_cut: float) -> Tuple[Optional[LineString], Optional[LineString]]:
	# Cuts a line in two at a distance from its starting point
	linestring_length_in_slk_units = linestring_end_slk - linestring_start_slk
	distance_along_linestring_in_slk_units = slk_at_which_to_cut - linestring_start_slk
	percent = distance_along_linestring_in_slk_units / linestring_length_in_slk_units
	length_of_linestring_in_data_units = linestring.length
	distance_along_linestring_in_data_units = length_of_linestring_in_data_units * percent
	
	if distance_along_linestring_in_data_units <= 0.0:
		return None, LineString(linestring)
	if distance_along_linestring_in_data_units >= length_of_linestring_in_data_units:
		return LineString(linestring), None
	else:
		linestring_coordinates = list(linestring.coords)
		for index, vertex in enumerate(linestring_coordinates):
			projected_distance_of_vertex = linestring.project(Point(vertex))
			if math.isclose(projected_distance_of_vertex, distance_along_linestring_in_data_units):
				return (
					LineString(linestring_coordinates[:index + 1]),
					LineString(linestring_coordinates[index:])
				)
			if projected_distance_of_vertex > distance_along_linestring_in_data_units:
				new_vertex_at_cut = linestring.interpolate(distance_along_linestring_in_data_units)
				return (
					LineString(linestring_coordinates[:index] + [(new_vertex_at_cut.x, new_vertex_at_cut.y)]),
					LineString([(new_vertex_at_cut.x, new_vertex_at_cut.y)] + linestring_coordinates[index:])
				)


def double_cut_linestring(linestring: LineString, linestring_slk_start: float, linestring_slk_end: float, slk_cut_first: float, slk_cut_second: float) -> Tuple[Optional[LineString], Optional[LineString], Optional[LineString]]:
	part_a, part_bc = cut_linestring(linestring, linestring_start_slk=linestring_slk_start, linestring_end_slk=linestring_slk_end, slk_at_which_to_cut=slk_cut_first)
	part_b = None
	part_c = None
	if part_bc is not None:
		part_b, part_c = cut_linestring(part_bc, linestring_start_slk=max(linestring_slk_start, slk_cut_first), linestring_end_slk=linestring_slk_end, slk_at_which_to_cut=slk_cut_second)
	return part_a, part_b, part_c