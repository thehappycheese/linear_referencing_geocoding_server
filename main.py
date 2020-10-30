import math
from typing import List
import json
import geopandas as gpd

from waitress import serve as waitress_serve
from flask import Flask, request
from shapely.geometry import Point
from shapely.geometry.linestring import LineString
from shapely.geometry.multilinestring import MultiLineString

from NicksIntervals.iInterval import iInterval

app = Flask(__name__)

from flask import Response

EARTH_RADIUS_METERS 	= 6.3781e6
EARTH_METERS_PER_RADIAN	= EARTH_RADIUS_METERS
EARTH_METERS_PER_DEGREE = EARTH_METERS_PER_RADIAN * math.pi / 180


# This data is publicly available as a GeoJSON file from https://catalogue.data.wa.gov.au/dataset/mrwa-road-network
path_to_gdb = r"data.gdb"
gdf_all_roads: gpd.GeoDataFrame = gpd.read_file(path_to_gdb, layer="NTWK_IRIS_Road_Network_20201029")


def cut_linestring(line: LineString, slk_distance: float, row_start_slk: float, row_end_slk: float) -> [LineString, LineString]:
	# Cuts a line in two at a distance from its starting point
	percent = slk_distance / (row_end_slk - row_start_slk)
	distance = line.length*percent
	if distance <= 0.0:
		return [None, LineString(line)]
	if distance >= line.length:
		return [LineString(line), None]
	coords = list(line.coords)
	for i, p in enumerate(coords):
		pd = line.project(Point(p))
		if pd == distance:
			return [
				LineString(coords[:i+1]),
				LineString(coords[i:])]
		if pd > distance:
			cp = line.interpolate(distance)
			return [
				LineString(coords[:i] + [(cp.x, cp.y)]),
				LineString([(cp.x, cp.y)] + coords[i:])]


ERROR_SUGGEST_CORRECT = "Try /?road=H001&slk_from=6.3&slk_to=7 or /?road=H001,H012&slk_from=6.3,16.4&slk_to=7,17.35"
ERROR_SUGGEST_CORRECT_ADVANCED = "Try /?road=H001&slk_from=6.3&slk_to=7&offset=-5&cway=L or /?road=H001,H012&slk_from=6.3,16.4&slk_to=7,17.35&offset=-5,5&cway=L,R"


@app.route('/')
def hello_world():
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
	if request_offset is None:
		request_offset = [0]*len(request_road)
	else:
		request_offset = request_offset.split(',')
	if len(request_offset) != len(request_road):
		return Response("error: optional parameter 'offset' list must be the same length as the 'road' parameter. " + ERROR_SUGGEST_CORRECT_ADVANCED, status=400)
	
	# convert offsets to floats
	try:
		request_offset = [float(item) for item in request_offset]
	except:
		return Response("error: optional parameter 'offset' could not be converted to a number. " + ERROR_SUGGEST_CORRECT_ADVANCED, status=400)
	
	request_carriageway = request.args.get("cway", default=None)
	if request_carriageway is None:
		request_carriageway = ["LRS"] * len(request_road)
	else:
		request_carriageway = request_carriageway.split(',')
	if len(request_carriageway) != len(request_road):
		return Response("error: optional parameter 'cway' list must be the same length as the 'road' parameter. " + ERROR_SUGGEST_CORRECT_ADVANCED, status=400)
	request_carriageway = [''.join(sorted(item.upper())) for item in request_carriageway]
	
	try:
		slice_results = []
		for road, slk_from, slk_to, offset, cway in zip(request_road, request_slk_from, request_slk_to, request_offset, request_carriageway):
			slice_results.extend(slice_network(road, slk_from, slk_to, offset, cway))
		if len(slice_results) == 0:
			raise Slice_Network_Exception("Valid user parameters produced no resulting geometry. Are the SLK bounds within the extent of the road?")
		elif len(slice_results) == 1:
			result = f'{{"type": "Feature", "properties": null, "geometry": {slice_results[0]}}}'
		else:
			result = f'{{"type": "Feature", "properties": null, "geometry": {{"type":"GeometryCollection", "geometries":[{",".join(slice_results)}]}}'
		return result
	except Slice_Network_Exception as slice_network_exception:
		return Response(f"error: unable to slice network with the provided parameters: {slice_network_exception.message}", status=400)
	except Exception as e:
		print("Encountered unknown error:")
		return Response(f"error: Unknown Error", status=500)
		
		
class Slice_Network_Exception(Exception):
	def __init__(self, message):
		super().__init__(message)
		self.message = message


def slice_network(road: str, slk_from: float, slk_to: float, offset: float, cway: str) -> List[str]:
	try:
		request_slk = iInterval.closed(slk_from, slk_to)
	except:
		raise Slice_Network_Exception("Invalid slk interval")
	
	if request_slk.is_degenerate or request_slk.is_infinitesimal:
		# TODO: provide point geometry results
		raise Slice_Network_Exception("Requested slk interval is of zero length. In future we can provide point geometry results. For now, this request is rejected.")
	
	m = gdf_all_roads[
		(gdf_all_roads["ROAD"] == road) & (gdf_all_roads["START_SLK"] <= slk_to) & (gdf_all_roads["END_SLK"] >= slk_from)
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
		row_slk = iInterval.closed(row_slk_from, row_slk_to)
		multilinestring = row.geometry
		if multilinestring.geom_type != "MultiLineString":
			raise Exception("Encountered unexpected geometry in the road network geometry data. The shape of a row was not a MultiLineString as expected.")
		if len(multilinestring.geoms) != 1:
			raise Exception("Encountered unexpected geometry in the road network geometry data. The row's geometry was a MultiLineString, but it did not contain exactly one LineString as expected.")
		linestring: LineString = multilinestring.geoms[0]
		
		if request_slk.contains_interval(row_slk):
			# contained entirely
			output.append(linestring)
		else:
			part_a, part_bc = cut_linestring(
				linestring,
				slk_distance=slk_from - row_slk_from,
				row_start_slk=row_slk_from,
				row_end_slk=row_slk_to
			)
			part_b = None
			part_c = None
			if part_bc is not None:
				part_b, part_c = cut_linestring(
					part_bc,
					slk_distance=request_slk.length,
					row_start_slk=row_slk_from + max(0, slk_from - row_slk_from),
					row_end_slk=row_slk_to
				)
			else:
				pass  # there is no intersect
			
			if part_b is not None:
				output.append(part_b)
			else:
				pass  # no output
	if len(output) == 0:
		return []
	
	if offset != 0:
		output2 = []
		for line_string_to_offset in output:
			offset_linestring_maybe_multi = line_string_to_offset.parallel_offset(
				distance=abs(offset / EARTH_METERS_PER_DEGREE),
				side=('left' if offset < 0 else 'right')
			)
			if isinstance(offset_linestring_maybe_multi, MultiLineString):
				output2.extend(LineString(coords) for coords in offset_linestring_maybe_multi)
			else:
				output2.append(offset_linestring_maybe_multi)
		output = output2
	if len(output) == 1:
		return [json.dumps(output[0].__geo_interface__)]
	return [json.dumps(MultiLineString(output).__geo_interface__)]


if __name__ == '__main__':
	# app.run(host='0.0.0.0', port=8001)
	waitress_serve(app, host='0.0.0.0', port=8001)


