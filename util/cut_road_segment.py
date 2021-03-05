import math
from typing import Tuple, Optional

from nicks_line_tools.linestring_cut import linestring_cut
from nicks_line_tools.type_aliases import LineString


def cut_road_segment(linestring: LineString, linestring_start_slk: float, linestring_end_slk: float, slk_at_which_to_cut: float) -> Tuple[Optional[LineString], Optional[LineString]]:
	linestring_length_in_slk_units = linestring_end_slk - linestring_start_slk
	distance_along_linestring_in_slk_units = slk_at_which_to_cut - linestring_start_slk
	percent = distance_along_linestring_in_slk_units / linestring_length_in_slk_units
	return linestring_cut(linestring, percent)


def double_cut_road_segment(linestring: LineString, linestring_slk_start: float, linestring_slk_end: float, slk_cut_first: float, slk_cut_second: float) -> Tuple[Optional[LineString], Optional[LineString], Optional[LineString]]:
	part_a, part_bc = cut_road_segment(linestring, linestring_start_slk=linestring_slk_start, linestring_end_slk=linestring_slk_end, slk_at_which_to_cut=slk_cut_first)
	part_b = None
	part_c = None
	if part_bc is not None:
		part_b, part_c = cut_road_segment(part_bc, linestring_start_slk=max(linestring_slk_start, slk_cut_first), linestring_end_slk=linestring_slk_end, slk_at_which_to_cut=slk_cut_second)
	return part_a, part_b, part_c