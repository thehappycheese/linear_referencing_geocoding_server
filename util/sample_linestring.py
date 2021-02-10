from __future__ import annotations
import math
from typing import List, Union, Dict, Tuple

from geopandas import GeoDataFrame
from shapely.geometry import LineString, Point, MultiLineString

from util.cut_linestring import double_cut_linestring
from util.get_point_along_linestring_with_offset import get_point_along_linestring_with_offset
from util.convert_metres_to_degrees import convert_metres_to_degrees


# (START_SLK, END_SLK, CWY, COORDS)
def sample_linestring(road_segments: Tuple[float, float, str, List[List[float]]], slk_cut_first: float, slk_cut_second: float = None, offset_metres: float = 0) -> List[Union[Point, LineString]]:
	output: List[Union[Point, LineString]] = []
	
	OUTPUT_POINT = math.isclose(slk_cut_first, slk_cut_second) or slk_cut_second is None
	OUTPUT_LINESTRING = not OUTPUT_POINT
	
	for START_SLK, END_SLK, CWY, COORDS in road_segments:
		if OUTPUT_POINT:
			if START_SLK <= slk_cut_first <= END_SLK:
				output.append(
					get_point_along_linestring_with_offset(
						COORDS,
						linestring_slk_start=START_SLK,
						linestring_slk_end=END_SLK,
						slk_cut=slk_cut_first,
						offset_metres=offset_metres
					)
				)
		
		elif OUTPUT_LINESTRING:
			_, segment, _ = double_cut_linestring(COORDS, START_SLK, END_SLK, slk_cut_first, slk_cut_second)
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
					for linestring_coordinates in offset_linestring_maybe_multi:
						if not linestring_coordinates.is_empty:
							output.append(linestring_coordinates)
				elif isinstance(offset_linestring_maybe_multi, LineString):
					output.append(offset_linestring_maybe_multi)
				else:
					raise Exception("unknown result from offset operation")
	
	return output
