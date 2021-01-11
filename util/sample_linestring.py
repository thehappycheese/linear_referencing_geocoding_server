import math
from typing import List, Union

from geopandas import GeoDataFrame
from shapely.geometry import LineString, Point, MultiLineString

from util.cut_linestring import double_cut_linestring
from util.get_point_along_linestring_with_offset import get_point_along_linestring_with_offset
from util.convert_metres_to_degrees import convert_metres_to_degrees


def sample_linestring(road_segments: GeoDataFrame, slk_cut_first: float, slk_cut_second: float = None, offset_metres: float = 0) -> List[Union[Point, LineString]]:
	"""
	:param road_segments: from a single road number
	:param slk_cut_first:
	:param slk_cut_second:
	:param offset_metres:
	:return: Return a list of shapely geometries; either points or line_strings cut from the road segments.
	"""
	output: List[Union[Point, LineString]] = []
	
	OUTPUT_POINT = math.isclose(slk_cut_first, slk_cut_second) or slk_cut_second is None
	OUTPUT_LINESTRING = not OUTPUT_POINT
	
	for index, row in road_segments.iterrows():
		row_slk_from = float(row["START_SLK"])
		row_slk_to = float(row["END_SLK"])
		
		multilinestring = row.geometry
		if multilinestring.geom_type != "MultiLineString":
			raise Exception("Encountered unexpected geometry in the road network data. The shape of a record was not a MultiLineString.")
		if len(multilinestring.geoms) != 1:
			raise Exception("Encountered unexpected geometry in the road network data. The record's geometry was a MultiLineString (as expected), but it did not contain exactly one LineString.")
		linestring = multilinestring.geoms[0]
		
		if OUTPUT_POINT:
			if row_slk_from <= slk_cut_first <= row_slk_to:
				output.append(
					get_point_along_linestring_with_offset(
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