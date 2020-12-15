import math
from typing import List
import json
import geopandas as gpd

from waitress import serve as waitress_serve
from flask import Flask, request, send_file, Response
from shapely.geometry import Point
from shapely.geometry.linestring import LineString
from shapely.geometry.multilinestring import MultiLineString
import os
import sys

# This next line would disable the warning when the built-in flask server is started on the local machine:
# os.environ["FLASK_ENV"] = "development"

app = Flask(__name__)

EARTH_RADIUS_METERS 	= 6.3781e6
EARTH_METERS_PER_RADIAN	= EARTH_RADIUS_METERS
EARTH_METERS_PER_DEGREE = EARTH_METERS_PER_RADIAN * math.pi / 180


# This data is publicly available as a GeoJSON file from https://catalogue.data.wa.gov.au/dataset/mrwa-road-network
path_to_gdb = r"data.gdb"
gdf_all_roads: gpd.GeoDataFrame = gpd.read_file(
	path_to_gdb,
	layer="NTWK_IRIS_Road_Network_20201029"
)


def cut_linestring(linestring: LineString, slk_at_which_to_cut: float, linestring_start_slk: float, linestring_end_slk: float) -> [LineString, LineString]:
	# Cuts a line in two at a distance from its starting point
	linestring_length_in_slk_units = linestring_end_slk - linestring_start_slk
	distance_along_linestring_in_slk_units = slk_at_which_to_cut - linestring_start_slk
	percent = distance_along_linestring_in_slk_units / linestring_length_in_slk_units
	length_of_linestring_in_data_units = linestring.length
	distance_along_linestring_in_data_units = length_of_linestring_in_data_units * percent
	
	if distance_along_linestring_in_data_units <= 0.0:
		return [None, LineString(linestring)]
	if distance_along_linestring_in_data_units >= length_of_linestring_in_data_units:
		return [LineString(linestring), None]
	else:
		linestring_coordinates = list(linestring.coords)
		for index, vertex in enumerate(linestring_coordinates):
			projected_distance_of_vertex = linestring.project(Point(vertex))
			if math.isclose(projected_distance_of_vertex, distance_along_linestring_in_data_units):
				return [
					LineString(linestring_coordinates[:index+1]),
					LineString(linestring_coordinates[index:])
				]
			if projected_distance_of_vertex > distance_along_linestring_in_data_units:
				new_vertex_at_cut = linestring.interpolate(distance_along_linestring_in_data_units)
				return [
					LineString(linestring_coordinates[:index] + [(new_vertex_at_cut.x, new_vertex_at_cut.y)]),
					LineString([(new_vertex_at_cut.x, new_vertex_at_cut.y)] + linestring_coordinates[index:])
				]


ERROR_SUGGEST_CORRECT = "Try /?road=H001&slk_from=6.3&slk_to=7 or /?road=H001,H012&slk_from=6.3,16.4&slk_to=7,17.35"
ERROR_SUGGEST_CORRECT_ADVANCED = "Try /?road=H001&slk_from=6.3&slk_to=7&offset=-5&cway=L or /?road=H001,H012&slk_from=6.3,16.4&slk_to=7,17.35&offset=-5,5&cway=L,R"


@app.route('/')
def hello_world():
	if not request.args:
		return send_file('static_show/form.html')
	if request.args.get("show", default=None) is not None:
		return send_file('static_show/map.html')
	
	request_road = request.args.get("road", default=None)
	try:
		assert request_road is not None
		request_road = request_road.split(',')
		for item in request_road:
			assert len(item) > 2
	except:
		return Response("error: missing or malformed url parameter 'road'. " + ERROR_SUGGEST_CORRECT, status=400)
	
	request_slk_from = request.args.get("slk_from", default=None)
	request_slk_to = request.args.get("slk_to", default=None)
	
	try:
		assert request_slk_from is not None
		assert request_slk_to is not None
	except:
		return Response("error: missing url parameters 'slk_from' and/or 'slk_to'. " + ERROR_SUGGEST_CORRECT, status=400)
	
	try:
		request_slk_from = request_slk_from.split(',')
		request_slk_to = request_slk_to.split(',')
		assert len(request_slk_from) == len(request_road)
		assert len(request_slk_to) == len(request_road)
	except:
		return Response("error: parameters 'slk_from' and 'slk_to' could not be split into lists the same length as the 'road' parameter list. " + ERROR_SUGGEST_CORRECT, status=400)
	
	try:
		request_slk_from = tuple(float(item) for item in request_slk_from)
		request_slk_to = tuple(float(item) for item in request_slk_to)
	except:
		return Response("error: parameters 'slk_from' and 'slk_to' could not be converted to numbers. " + ERROR_SUGGEST_CORRECT, status=400)
	
	request_slk_from_copy = request_slk_from
	request_slk_to_copy = request_slk_to
	request_slk_from = []
	request_slk_to = []
	for iter_slk_from, iter_slk_to in zip(request_slk_from_copy, request_slk_to_copy):
		request_slk_from.append(min(iter_slk_from, iter_slk_to))
		request_slk_to.append(max(iter_slk_from, iter_slk_to))
	
	# obtain offset
	request_offset = request.args.get("offset", default=None)
	if request_offset is None or request_offset == "":
		request_offset = [0]*len(request_road)
	else:
		request_offset = request_offset.split(',')
	if len(request_offset) != len(request_road):
		return Response("error: optional parameter 'offset' list must be the same length as the 'road' parameter. " + ERROR_SUGGEST_CORRECT_ADVANCED, status=400)
	
	# convert offsets to floats
	try:
		request_offset = [float(item) if item != "" else 0 for item in request_offset]
	except:
		return Response("error: optional parameter 'offset' could not be converted to a number. " + ERROR_SUGGEST_CORRECT_ADVANCED, status=400)
	
	request_carriageway = request.args.get("cway", default=None)
	if request_carriageway is None or request_carriageway == "":
		request_carriageway = ["LRS"] * len(request_road)
	else:
		request_carriageway = request_carriageway.split(',')
	if len(request_carriageway) != len(request_road):
		return Response("error: optional parameter 'cway' list must be the same length as the 'road' parameter. " + ERROR_SUGGEST_CORRECT_ADVANCED, status=400)
	request_carriageway = [''.join(sorted(item.upper())) if item != "" else "LRS" for item in request_carriageway]
	
	try:
		slice_results = []
		for road, slk_from, slk_to, offset, cway in zip(request_road, request_slk_from, request_slk_to, request_offset, request_carriageway):
			if math.isclose(slk_from, slk_to):
				ff = return_points_on_network(road, slk_from, offset, cway)
				slice_results.extend(ff)
			else:
				slice_results.extend(cut_segments_from_network(road, slk_from, slk_to, offset, cway))
		if len(slice_results) == 0:
			raise Slice_Network_Exception("Valid user parameters produced no resulting geometry. Are the SLK bounds within the extent of the road?")
		elif len(slice_results) == 1:
			result = f'{{"type": "Feature", "properties": null, "geometry": {slice_results[0]}}}'
		else:
			result = f'{{"type": "Feature", "properties": null, "geometry": {{"type":"GeometryCollection", "geometries":[{",".join(slice_results)}]}}}}'
		return Response(result)  # , mimetype="application/json")
	except Slice_Network_Exception as slice_network_exception:
		return Response(f"error: unable to slice network with the provided parameters: {slice_network_exception.message}", status=400)
	except Exception as e:
		exc_type, exc_obj, exc_tb = sys.exc_info()
		fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
		print(exc_type, fname, exc_tb.tb_lineno)
		print(f"Encountered unknown error on request {request.full_path}")
		print(e)
		exit()
		return Response(f"error: Unknown error. ", status=500)
		
		
class Slice_Network_Exception(Exception):
	def __init__(self, message):
		super().__init__(message)
		self.message = message


def return_points_on_network(road: str, request_slk: float, offset: float, cway: str) -> List[str]:
	road_segment_rows = gdf_all_roads[
		(gdf_all_roads["ROAD"] == road.strip().upper()) & (gdf_all_roads["START_SLK"] <= request_slk) & (gdf_all_roads["END_SLK"] >= request_slk)
	]
	
	if cway == "LS":
		road_segment_rows = road_segment_rows[(road_segment_rows["CWY"] == "Left") | (road_segment_rows["CWY"] == "Single")]
	elif cway == "RS":
		road_segment_rows = road_segment_rows[(road_segment_rows["CWY"] == "Right") | (road_segment_rows["CWY"] == "Single")]
	elif cway == "LR":
		road_segment_rows = road_segment_rows[(road_segment_rows["CWY"] == "Right") | (road_segment_rows["CWY"] == "Left")]
	elif cway == "R":
		road_segment_rows = road_segment_rows[road_segment_rows["CWY"] == "Right"]
	elif cway == "L":
		road_segment_rows = road_segment_rows[road_segment_rows["CWY"] == "Left"]
	elif cway == "S":
		road_segment_rows = road_segment_rows[road_segment_rows["CWY"] == "Single"]
	elif cway == "LRS":
		pass
	else:
		raise Slice_Network_Exception(f"Invalid carriageway parameter: {cway}. Must be any combination of the three letters 'L', 'R' and 'S'. eg &cwy=LR or &cwy=RL or &cwy=S. omit the parameter to query all.")
	
	output: List[LineString] = []
	
	for index, road_segment_row in road_segment_rows.iterrows():
		row_slk_from = float(road_segment_row["START_SLK"])
		row_slk_to = float(road_segment_row["END_SLK"])
		
		multilinestring = road_segment_row.geometry
		if multilinestring.geom_type != "MultiLineString":
			raise Exception("Encountered unexpected geometry in the road network geometry data. The shape of a row was not a MultiLineString as expected.")
		if len(multilinestring.geoms) != 1:
			raise Exception("Encountered unexpected geometry in the road network geometry data. The row's geometry was a MultiLineString (as expected), but it did not contain exactly one LineString as expected.")
		
		row_linestring: LineString = multilinestring.geoms[0]
		if row_linestring.is_empty:
			return []
		
		if offset == 0:
			row_linestring_after_offset = row_linestring
		else:
			offset_linestring_maybe_multi = row_linestring.parallel_offset(
				distance=abs(offset / EARTH_METERS_PER_DEGREE),
				side=('left' if offset < 0 else 'right')
			)
			if offset_linestring_maybe_multi.is_empty:
				# TODO: No result. Do not emit error explaining that an offset operation removed a point?
				return []
			row_linestring_after_offset = offset_linestring_maybe_multi
		
		point_result = row_linestring.interpolate(
			(request_slk-row_slk_from)/(row_slk_to-row_slk_from),  # Fraction of line length
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
	if len(output) == 0:
		return []
	if len(output) > 1:
		return [f'{{"type":"MultiPoint","coordinates":[{",".join(json.dumps([item.coords[0][0],item.coords[0][1]]) for item in output)}]}}']
	else:
		return [f'{{"type":"Point","coordinates":{json.dumps([output[0].coords[0][0], output[0].coords[0][1]])}}}']


def cut_segments_from_network(road: str, request_slk_from: float, request_slk_to: float, offset: float, cway: str) -> List[str]:
	
	if request_slk_to < request_slk_from:
		# The user should not see this error, the code above is supposed to silently swap the SLKs if they are the wrong way around.
		raise Slice_Network_Exception("Invalid slk interval; either reversed or zero length")
	
	if math.isclose(request_slk_from, request_slk_to):
		raise Slice_Network_Exception("Infinitesimal length slk interval provided.")
	
	m = gdf_all_roads[
		(gdf_all_roads["ROAD"] == road.strip().upper()) & (gdf_all_roads["START_SLK"] <= request_slk_to) & (gdf_all_roads["END_SLK"] >= request_slk_from)
	]
	
	if cway == "LS":
		m = m[(m["CWY"] == "Left") | (m["CWY"] == "Single")]
	elif cway == "RS":
		m = m[(m["CWY"] == "Right") | (m["CWY"] == "Single")]
	elif cway == "LR":
		m = m[(m["CWY"] == "Right") | (m["CWY"] == "Left")]
	elif cway == "R":
		m = m[m["CWY"] == "Right"]
	elif cway == "L":
		m = m[m["CWY"] == "Left"]
	elif cway == "S":
		m = m[m["CWY"] == "Single"]
	elif cway == "LRS":
		pass
	else:
		raise Slice_Network_Exception(f"Invalid carriageway parameter: {cway}. Must be any combination of the three letters 'L', 'R' and 'S'. eg &cwy=LR or &cwy=RL or &cwy=S. omit the parameter to query all.")
	
	output: List[LineString] = []
	
	for index, row in m.iterrows():
		row_slk_from = float(row["START_SLK"])
		row_slk_to = float(row["END_SLK"])
		
		multilinestring = row.geometry
		if multilinestring.geom_type != "MultiLineString":
			raise Exception("Encountered unexpected geometry in the road network geometry data. The shape of a row was not a MultiLineString as expected.")
		if len(multilinestring.geoms) != 1:
			raise Exception("Encountered unexpected geometry in the road network geometry data. The row's geometry was a MultiLineString, but it did not contain exactly one LineString as expected.")
		
		row_linestring: LineString = multilinestring.geoms[0]
		
		if (request_slk_from < row_slk_from or math.isclose(request_slk_from, row_slk_from)) and (row_slk_to < request_slk_to or math.isclose(row_slk_to, request_slk_to)):
			# request contains row linestring entirely therefore return the entire linestring
			output.append(row_linestring)
		else:
			part_a, part_bc = cut_linestring(
				row_linestring,
				slk_at_which_to_cut=request_slk_from,
				linestring_start_slk=row_slk_from,
				linestring_end_slk=row_slk_to
			)
			part_b = None
			if part_bc is not None:
				
				part_b, _ = cut_linestring(
					part_bc,
					slk_at_which_to_cut=request_slk_to,
					linestring_start_slk=max(row_slk_from, request_slk_from),
					linestring_end_slk=row_slk_to
				)
			else:
				pass  # there is no intersect
			
			if part_b is not None:
				output.append(part_b)
			else:
				pass  # no output
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
				distance=abs(offset / EARTH_METERS_PER_DEGREE),
				side=('left' if offset < 0 else 'right')
			)
			# print(offset_linestring_maybe_multi)
			if offset_linestring_maybe_multi.is_empty:
				continue
			if isinstance(offset_linestring_maybe_multi, MultiLineString):
				# convert any multilinestring back to linestring.
				# /?road=H015&slk_from=30.97&slk_to=31&offset=-35&cway=LS
				# /?road=H015&slk_from=30.97&slk_to=31&offset=-35&cway=LS
				# /?road=H015&slk_from=30.97&slk_to=31&offset=-35&cway=LS
				# /?road=H015&slk_from=30.97&slk_to=31&offset=-35&cway=LS
				for linestring in offset_linestring_maybe_multi:
					if not linestring.is_empty:
						output_after_offset.append(linestring)
			else:
				output_after_offset.append(offset_linestring_maybe_multi)
		# print("o after offset")
		# print(output_after_offset)
		
	if len(output_after_offset) == 1:
		return [json.dumps(output_after_offset[0].__geo_interface__)]
	elif len(output_after_offset) > 1:
		return [json.dumps(MultiLineString(output_after_offset).__geo_interface__)]
	else:
		raise Slice_Network_Exception(f"Cutting network succeeded producing {len(output)} features, but offsetting the results failed. Try using a smaller offset, or perhaps shorter road segments will work?")


if __name__ == '__main__':
	# app.run(host='0.0.0.0', port=8001)
	waitress_serve(app, host='0.0.0.0', port=8001)
