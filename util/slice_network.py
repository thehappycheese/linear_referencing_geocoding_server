import json
import math
from typing import List, Union

import geopandas as gpd
from shapely.geometry import LineString, MultiLineString, MultiPoint, Point
from shapely.geometry.base import BaseGeometry

from util.cut_linestring import cut_linestring, double_cut_linestring
from util.unit_conversion import convert_metres_to_degrees


class Slice_Network_Exception(Exception):
	def __init__(self, message):
		super().__init__(message)
		self.message = message


def filter_dataframe(gdf_all_roads: gpd.GeoDataFrame, road: str, request_slk_from: float, request_slk_to: float, cway: str) -> gpd.GeoDataFrame:
	result = gdf_all_roads[
		(gdf_all_roads["ROAD"] == road.strip().upper()) & (gdf_all_roads["START_SLK"] <= request_slk_to) & (gdf_all_roads["END_SLK"] >= request_slk_from)
	]
	
	if cway == "LS":
		result = result[(result["CWY"] == "Left") | (result["CWY"] == "Single")]
	elif cway == "RS":
		result = result[(result["CWY"] == "Right") | (result["CWY"] == "Single")]
	elif cway == "LR":
		result = result[(result["CWY"] == "Right") | (result["CWY"] == "Left")]
	elif cway == "R":
		result = result[result["CWY"] == "Right"]
	elif cway == "L":
		result = result[result["CWY"] == "Left"]
	elif cway == "S":
		result = result[result["CWY"] == "Single"]
	elif cway == "LRS":
		pass
	else:
		raise Slice_Network_Exception(f"Invalid carriageway parameter: {cway}. Must be any combination of the three letters 'L', 'R' and 'S'. eg &cwy=LR or &cwy=RL or &cwy=S. omit the parameter to query all.")
	
	return result

# def slice_network(gdf_all_roads: gpd.GeoDataFrame, road: str, request_slk_from: float, request_slk_to: float, offset_metres: float, cway: str, request_wkt: bool) -> Union[List[BaseGeometry], List[str]]:
# 	road_segment_rows = filter_dataframe(gdf_all_roads, road, request_slk_from, request_slk_to, cway)
#
# 	output_points: List[Union[MultiPoint, Point]] = []
# 	output_linestrings: List[Union[MultiPoint, Point]] = []
#
# 	for index, road_segment_row in road_segment_rows.iterrows():
# 		row_slk_from = float(road_segment_row["START_SLK"])
# 		row_slk_to = float(road_segment_row["END_SLK"])
#
# 		multilinestring = road_segment_row.geometry
# 		if multilinestring.geom_type != "MultiLineString":
# 			raise Exception("Encountered unexpected geometry in the road network data. The geometry of a record was not a MultiLineString.")
# 		if len(multilinestring.geoms) != 1:
# 			raise Exception("Encountered unexpected geometry in the road network data. The record's geometry was a MultiLineString (as expected), but it did not contain exactly one LineString.")
#
# 		row_linestring: LineString = multilinestring.geoms[0]
# 		if row_linestring.is_empty:
# 			return []


def return_points_on_network(gdf_all_roads: gpd.GeoDataFrame, road: str, request_slk: float, offset_metres: float, cway: str, request_wkt: bool) -> Union[List[BaseGeometry], List[str]]:
	road_segment_rows = filter_dataframe(gdf_all_roads, road, request_slk, request_slk, cway)
	
	output: List[Union[MultiPoint, Point]] = []
	
	for index, road_segment_row in road_segment_rows.iterrows():
		row_slk_from = float(road_segment_row["START_SLK"])
		row_slk_to = float(road_segment_row["END_SLK"])
		
		multilinestring = road_segment_row.geometry
		if multilinestring.geom_type != "MultiLineString":
			raise Exception("Encountered unexpected geometry in the road network data. The geometry of a record was not a MultiLineString.")
		if len(multilinestring.geoms) != 1:
			raise Exception("Encountered unexpected geometry in the road network data. The record's geometry was a MultiLineString (as expected), but it did not contain exactly one LineString.")
		
		row_linestring: LineString = multilinestring.geoms[0]
		if row_linestring.is_empty:
			return []
		
		if offset_metres == 0:
			row_linestring_after_offset = row_linestring
		else:
			offset_linestring_maybe_multi = row_linestring.parallel_offset(
				distance=abs(convert_metres_to_degrees(offset_metres)),
				side=('left' if offset_metres < 0 else 'right')
			)
			if offset_linestring_maybe_multi.is_empty:
				# TODO: No result. Do not emit error explaining that an offset operation removed a point?
				return []
			row_linestring_after_offset = offset_linestring_maybe_multi
		
		point_result = row_linestring.interpolate(
			(request_slk - row_slk_from) / (row_slk_to - row_slk_from),  # Fraction of line length
			normalized=True
		)
		
		if point_result.is_empty:
			# TODO: No result. Do not emit error?
			return []
		
		# TODO: error will be introduced by offset due to the additional line length of the miters. Should not be noticeable most of the time?
		#  The only way to fix this is to determine the instantaneous direction of the linestring, and perform the offset. Add to readme.
		
		point_result = row_linestring_after_offset.interpolate(row_linestring_after_offset.project(point_result))
		
		if point_result.is_empty:
			# TODO: No result. Do not emit error?
			return []
		
		output.append(point_result)

	return output
	


def cut_segments_from_network(gdf_all_roads: gpd.GeoDataFrame, road: str, request_slk_from: float, request_slk_to: float, offset: float, cway: str, request_wkt: bool) -> Union[List[BaseGeometry], List[str]]:
	if request_slk_to < request_slk_from:
		# The user should not see this error, the code in process_request_args is supposed to silently swap the SLKs if they are the wrong way around.
		raise Slice_Network_Exception("Invalid slk interval; either reversed or zero length")
	
	if math.isclose(request_slk_from, request_slk_to):
		raise Slice_Network_Exception("Infinitesimal length slk interval provided.")
	
	road_segment_rows = filter_dataframe(gdf_all_roads, road, request_slk_from, request_slk_to, cway)
	
	output: List[Union[LineString, MultiLineString]] = []
	
	for index, row in road_segment_rows.iterrows():
		row_slk_from = float(row["START_SLK"])
		row_slk_to = float(row["END_SLK"])
		
		multilinestring = row.geometry
		if multilinestring.geom_type != "MultiLineString":
			raise Exception("Encountered unexpected geometry in the road network data. The shape of a record was not a MultiLineString.")
		if len(multilinestring.geoms) != 1:
			raise Exception("Encountered unexpected geometry in the road network data. The record's geometry was a MultiLineString (as expected), but it did not contain exactly one LineString.")
		
		row_linestring: LineString = multilinestring.geoms[0]

		_, segment, _ = double_cut_linestring(row_linestring, row_slk_from, row_slk_to, request_slk_from, request_slk_to)
		if segment:
			output.append(segment)
		
	if len(output) == 0:
		return []
	
	if offset == 0:
		output_after_offset = output
	else:
		output_after_offset = []
		for line_string_to_offset in output:
			if line_string_to_offset.is_empty:
				continue
			
			offset_linestring_maybe_multi = line_string_to_offset.parallel_offset(
				distance=abs(convert_metres_to_degrees(offset)),
				side=('left' if offset < 0 else 'right')
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
						output_after_offset.append(linestring)
			else:
				output_after_offset.append(offset_linestring_maybe_multi)
	
	if len(output_after_offset) == 0:
		raise Slice_Network_Exception(f"Cutting network succeeded producing {len(output)} features, but offsetting the results failed. Try using a smaller offset, or perhaps shorter road segments will work?")
	
	return output_after_offset
