import math
from typing import Optional, Tuple, List, Union

from geopandas import GeoSeries, GeoDataFrame
from shapely.geometry import LineString, Point, MultiPoint, MultiLineString

from util.direction_of_linestring import direction_of_linestring
from util.unit_conversion import convert_metres_to_degrees


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


def cut_point_linestring(line_string: LineString, linestring_slk_start: float, linestring_slk_end: float, slk_cut: float, offset_metres: float = 0) -> Point:
	OFFSET_BY_INSTANTANEOUS_DIRECTION = True
	distance_along_linestring_normalised = (slk_cut - linestring_slk_start) / (linestring_slk_end - linestring_slk_start)
	
	if offset_metres == 0:
		point = line_string.interpolate(
			distance_along_linestring_normalised,
			normalized=True
		)
	else:
		if OFFSET_BY_INSTANTANEOUS_DIRECTION:
			# with this method error is introduced by sharp corners
			direction = direction_of_linestring(line_string, distance_along_linestring_normalised)
			x_offset = math.cos(direction) * convert_metres_to_degrees(offset_metres)
			y_offset = math.sin(direction) * convert_metres_to_degrees(offset_metres)
			point = line_string.interpolate(
				distance_along_linestring_normalised,
				normalized=True
			)
			point = Point(point.coords[0] + x_offset, point.coords[1] + y_offset)
		else:
			# with this method error is introduced by uneven introduction of extra length in offset linestring at curved corners, plus there is extra effort to offset the entire linestring
			# TODO: there is an error waiting to happen here; sometimes offset will result in a multi-linestring for which 'project()' does not make sense.
			offset_linestring = line_string.parallel_offset(
				abs(convert_metres_to_degrees(offset_metres)),
				side=('left' if offset_metres < 0 else 'right')
			)
			point = offset_linestring.project(
				distance_along_linestring_normalised,
				normalized=True
			)
	return point


def get_row_linestring(row: GeoSeries) -> LineString:
	multilinestring = row.geometry
	if multilinestring.geom_type != "MultiLineString":
		raise Exception("Encountered unexpected geometry in the road network data. The shape of a record was not a MultiLineString.")
	if len(multilinestring.geoms) != 1:
		raise Exception("Encountered unexpected geometry in the road network data. The record's geometry was a MultiLineString (as expected), but it did not contain exactly one LineString.")
	return multilinestring.geoms[0]


def sample_linestring(road_segments: GeoDataFrame, slk_cut_first: float, slk_cut_second: float = None, offset_metres: float = 0) -> List[Union[Point, LineString]]:
	"""
	:param road_segments: from a single road number
	:param slk_cut_first:
	:param slk_cut_second:
	:param offset_metres:
	:return:
	"""
	output: List[Union[Point, LineString]] = []
	
	OUTPUT_POINT = math.isclose(slk_cut_first, slk_cut_second) or slk_cut_second is None
	OUTPUT_LINESTRING = not OUTPUT_POINT
	
	for index, row in road_segments.iterrows():
		row_slk_from = float(row["START_SLK"])
		row_slk_to = float(row["END_SLK"])
		linestring = get_row_linestring(row)
		
		if OUTPUT_POINT:
			if row_slk_from <= slk_cut_first <= row_slk_to:
				output.append(
					cut_point_linestring(
						linestring,
						linestring_slk_start=row_slk_from,
						linestring_slk_end=row_slk_to,
						slk_cut=slk_cut_first,
						offset_metres=offset_metres
						)
					)
				
		elif OUTPUT_LINESTRING:
			_, segment, _ = double_cut_linestring(linestring, row_slk_from, row_slk_to, slk_cut_first, slk_cut_second)
			if segment is None or segment.is_empty:
				continue
			if offset_metres == 0:
				output.append(segment)
			else:
				offset_linestring_maybe_multi = segment.parallel_offset(
					distance=abs(convert_metres_to_degrees(offset_metres)),
					side=('left' if offset_metres < 0 else 'right')
				)
				# print(offset_linestring_maybe_multi)
				if offset_linestring_maybe_multi.is_empty:
					continue
				if isinstance(offset_linestring_maybe_multi, MultiLineString):
					# convert any multilinestring back to linestring. Example situations that require this branch:
					# /?road=H015&slk_from=30.97&slk_to=31&offset=-35&cway=LS
					# /?road=H015&slk_from=30.97&slk_to=31&offset=-35&cway=LS
					# /?road=H015&slk_from=30.97&slk_to=31&offset=-35&cway=LS
					# /?road=H015&slk_from=30.97&slk_to=31&offset=-35&cway=LS
					for linestring in offset_linestring_maybe_multi:
						if not linestring.is_empty:
							output.append(linestring)
				elif isinstance(offset_linestring_maybe_multi, LineString):
					output.append(offset_linestring_maybe_multi)
				else:
					raise Exception("unknown result from offset operation")
			
	return output