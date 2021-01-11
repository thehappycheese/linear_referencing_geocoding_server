from __future__ import annotations

import math
import os
import sys
from typing import List, Literal

import geopandas as gpd
from flask import Flask, request, send_file, Response
from shapely.geometry.base import BaseGeometry
from waitress import serve as waitress_serve

# This next line would disable the warning when the built-in flask server is started on the local machine:
# os.environ["FLASK_ENV"] = "development"
from util.parse_request_parameters import parse_request_parameters, URL_Parameter_Parse_Exception
from util.slice_network import return_points_on_network, cut_segments_from_network, Slice_Network_Exception

app = Flask(__name__)


# This data is publicly available as a GeoJSON file from https://catalogue.data.wa.gov.au/dataset/mrwa-road-network
path_to_gdb = r"data.gdb"
gdf_all_roads: gpd.GeoDataFrame = gpd.read_file(
	path_to_gdb,
	layer="NTWK_IRIS_Road_Network_20201029"
)


@app.route('/')
def route_handle_get():
	if not request.args:
		return send_file('static_show/form.html')
	
	if request.args.get("show", default=None) is not None:
		return send_file('static_show/map.html')
	
	request_output_type: Literal["WKT", "GEOJSON"] = "WKT" if request.args.get("wkt", default=None) is not None else "GEOJSON"
	
	try:
		slice_requests = parse_request_parameters(request)
	except URL_Parameter_Parse_Exception as e:
		return Response(e.message, status=400)
	except Exception as e:
		return Response("error: Unknown server error while trying to parse URL parameters.", status=500)
	
	try:
		slice_results: List[BaseGeometry] = []
		for slice_request in slice_requests:
			if math.isclose(slice_request.slk_from, slice_request.slk_to):
				slice_results.extend(
					return_points_on_network(
						gdf_all_roads,
						slice_request.road,
						slice_request.slk_from,
						slice_request.offset,
						slice_request.cway,
						request_output_type
					)
				)
			else:
				slice_results.extend(
					cut_segments_from_network(
						gdf_all_roads,
						slice_request.road,
						slice_request.slk_from,
						slice_request.slk_to,
						slice_request.offset,
						slice_request.cway,
						request_output_type
					)
				)
		
		if len(slice_results) == 0:
			raise Slice_Network_Exception("Valid user parameters produced no resulting geometry. Are the SLK bounds within the extent of the road?")
		
		if request_output_type:
			
			result = slice_results[0]
			for item in slice_results[1:]:
				result = result.union(item)
			result = result.wkt
			
			
		else:
			if len(slice_results) == 1:
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
		return Response(f"error: Unknown error. ", status=500)





if __name__ == '__main__':
	# app.run(host='0.0.0.0', port=8001)
	waitress_serve(app, host='0.0.0.0', port=8001)
