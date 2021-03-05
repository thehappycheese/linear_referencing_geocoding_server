import math
from typing import List, Union, Dict, Any

from geopandas import GeoDataFrame
from shapely.geometry import LineString, Point, MultiLineString

from nicks_line_tools import linestring_offset
from nicks_line_tools.Vector2 import Vector2
from nicks_line_tools.linestring_merge_sequential import linestring_merge_sequential
from util.cut_road_segment import double_cut_road_segment
from util.get_point_along_linestring_with_offset import get_point_along_linestring_with_offset
from util.convert_metres_to_degrees import convert_metres_to_degrees


def sample_linestring(road_segments: List[Dict[str, Any]], slk_cut_first: float, slk_cut_second: float = None, offset_metres: float = 0) -> List[Dict[str, Any]]:
	"""
	:param road_segments: from a single road number
	:param slk_cut_first:
	:param slk_cut_second:
	:param offset_metres:
	:return: Return a list of shapely geometries; either points or line_strings cut from the road segments.
	"""
	output: List[Dict[str, Any]] = []
	
	OUTPUT_POINT = math.isclose(slk_cut_first, slk_cut_second) or slk_cut_second is None
	OUTPUT_LINESTRING = not OUTPUT_POINT
	output_segments = []
	for item in road_segments:
		row_slk_from = float(item["properties"]["START_SLK"])
		row_slk_to = float(item["properties"]["END_SLK"])
		
		if not item["geometry"]["type"] == "LineString":
			raise Exception("Encountered unexpected geometry in the road network data. The record's geometry was a not a LineString")
		
		linestring = [Vector2(*coord) for coord in item["geometry"]["coordinates"]]
		
		if OUTPUT_POINT:
			if row_slk_from <= slk_cut_first <= row_slk_to:
				output_point_temp: Vector2 = get_point_along_linestring_with_offset(
					linestring,
					linestring_slk_start=row_slk_from,
					linestring_slk_end=row_slk_to,
					slk_cut=slk_cut_first,
					offset_metres=offset_metres
				)
				output.append(
					{"type": "Point", "coordinates": [*output_point_temp]}
				)
		
		elif OUTPUT_LINESTRING:
			_, segment, _ = double_cut_road_segment(linestring, row_slk_from, row_slk_to, slk_cut_first, slk_cut_second)
			if not segment:
				continue
			output_segments.append(segment)
	if OUTPUT_LINESTRING:
		if offset_metres == 0:
			output = [{"type": "LineString", "coordinates": [[x, y] for x, y in segment]} for segment in output_segments]
		else:
			linestring_merge_sequential(output_segments)
			for segment in output_segments:
				offset_linestrings = linestring_offset(
					segment,
					convert_metres_to_degrees(offset_metres)
				)
				# print(offset_linestrings)
				if not offset_linestrings:
					continue
				else:
					for linestring in offset_linestrings:
						if linestring:
							output.append({"type": "LineString", "coordinates": [[x, y] for x, y in linestring]})
	
	return output
