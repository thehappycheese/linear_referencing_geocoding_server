from __future__ import annotations

import os
import sys
from typing import List, Union  # , Literal

import geopandas as gpd
from flask import Flask, request, send_file, Response
from geopandas import GeoDataFrame
from shapely.geometry import LineString, Point
from waitress import serve as waitress_serve

# This next line would disable the warning when the built-in flask server is started on the local machine:
# os.environ["FLASK_ENV"] = "development"
from data_management.data_manager import Data_Manager
from util.parse_request_parameters import parse_request_parameters, URL_Parameter_Parse_Exception
from util.sample_linestring import sample_linestring
from util.serialise_output_geometry import serialise_output_geometry, Serialise_Results_Exception

app = Flask(__name__)

# This data is publicly available as a GeoJSON file from https://catalogue.data.wa.gov.au/dataset/mrwa-road-network
#path_to_gdb = r"data.gdb"
##gdf_all_roads: gpd.GeoDataFrame = gpd.read_file(
#	path_to_gdb,
#	layer="NTWK_IRIS_Road_Network_20201029"
#)

@app.route('/secrets/')
def route_handle_get_secrets():
	try:
		return send_file('static_show/secrets.json')
	except:
		return Response("")


@app.route('/')
def route_handle_get():
	if not request.args:
		return send_file('static_show/form.html')
	
	if request.args.get("show", default=None) is not None:
		return send_file('static_show/map.html')
	
	# noinspection PyTypeChecker
	# request_output_type: Literal["WKT", "GEOJSON"] = "WKT" if request.args.get("wkt", default=None) is not None else "GEOJSON"
	request_output_type = "WKT" if request.args.get("wkt", default=None) is not None else "GEOJSON"
	
	try:
		slice_requests = parse_request_parameters(request)
	except URL_Parameter_Parse_Exception as e:
		return Response(e.message, status=400)
	except Exception:
		return Response("error: Unknown server error while trying to parse URL parameters.", status=500)
	
	try:
		dm = Data_Manager()
		dm.load_registry()
	except:
		return Response("Server is still booting please try again.", status=500)

	try:
		slice_results: List[Union[Point, LineString]] = []
		for slice_request in slice_requests:
			road_segment_rows = dm.fetch_filter(slice_request.road, slice_request.slk_from, slice_request.slk_to, slice_request.cway)
			slice_results.extend(
				sample_linestring(
					road_segment_rows,
					slk_cut_first=slice_request.slk_from,
					slk_cut_second=slice_request.slk_to,
					offset_metres=slice_request.offset
				)
			)
		if len(slice_results) == 0:
			raise Slice_Network_Exception("Valid user parameters produced no resulting geometry. Are the SLK bounds within the extent of the road?")
		
		return Response(serialise_output_geometry(slice_results, request_output_type))  # , mimetype="application/json")
	
	except Slice_Network_Exception as slice_network_exception:
		return Response(f"error: unable to slice network with the provided parameters: {slice_network_exception.message}", status=400)
	except Serialise_Results_Exception as serialise_results_exception:
		return Response(f"error: unable to serialise results with the provided parameters: {serialise_results_exception.message}", status=400)
	except Exception as e:
		exc_type, exc_obj, exc_tb = sys.exc_info()
		file_name = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
		print(exc_type, file_name, exc_tb.tb_lineno)
		print(f"Encountered unknown error on request {request.full_path}")
		print(e)
		return Response(f"error: Unknown error. ", status=500)


class Slice_Network_Exception(Exception):
	def __init__(self, message):
		super().__init__(message)
		self.message = message


if __name__ == '__main__':
	# app.run(host='0.0.0.0', port=8002)
	waitress_serve(app, host='0.0.0.0', port=8002)
