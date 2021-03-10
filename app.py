from __future__ import annotations

import os
import sys
import json

try:
	# makes it work with pyinstaller bundled files
	os.chdir(sys._MEIPASS)
except:
	pass

# This next line would disable the warning when the built-in flask server is started on the local machine:

from util.parse_request_parameters import parse_request_parameters, URL_Parameter_Parse_Exception
from util.sample_linestring import sample_linestring

from urllib.parse import urlparse, parse_qs

from http import HTTPStatus
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import refresh_data
import time

reg = refresh_data.load_registry()




class Slice_Network_Exception(Exception):
	def __init__(self, message):
		super().__init__(message)
		self.message = message


class handle_get(BaseHTTPRequestHandler):
	def do_GET(self):
		u = urlparse(self.path)
		q = parse_qs(u.query, keep_blank_values=True)
		if u.path == "/secrets":
			try:
				with open("./static_show/secrets.json", "rb") as f:
					dat = f.read()
			except:
				self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR, f"error: unable to load secrets.json")
				self.end_headers()
				return
			self.send_response(HTTPStatus.OK)
			self.send_header("Content-Type", "application/json; charset=UTF-8;")
			self.send_header("Content-Length", str(len(dat)))
			self.end_headers()
			self.wfile.write(dat)
			return
		elif "show" in q:
			try:
				with open("./static_show/map.html", "rb") as f:
					dat = f.read()
			except:
				self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR, f"error: unable to load map.html")
				self.end_headers()
				return
			self.send_response(HTTPStatus.OK)
			self.send_header("Content-Type", "text/html; charset=UTF-8;")
			self.send_header("Content-Length", str(len(dat)))
			self.end_headers()
			self.wfile.write(dat)
			return
		elif u.path == "/" and not q.keys():
			try:
				with open("./static_show/form.html", "rb") as f:
					dat = f.read()
			except:
				self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR, f"error: unable to load form.html")
				self.end_headers()
				return
			self.send_response(HTTPStatus.OK)
			self.send_header("Content-Type", "text/html; charset=UTF-8;")
			self.send_header("Content-Length", str(len(dat)))
			self.end_headers()
			self.wfile.write(dat)
		elif not u.path == "/":
			self.send_error(HTTPStatus.NOT_FOUND, "File not found")
			self.end_headers()
			return
		request_output_type = "GEOJSON"
		if "WKT" in q or "wkt" in q:
			request_output_type = "WKT"
		try:
			params = parse_request_parameters(q)
		except URL_Parameter_Parse_Exception as e:
			self.send_error(HTTPStatus.BAD_REQUEST, e.message)
			self.end_headers()
			return
		print(params)
		time_start_slice = time.time()
		try:
			slice_results = []
			for slice_request in params:
				road_segment_rows = refresh_data.fetch_filter(reg, slice_request.road, slice_request.slk_from, slice_request.slk_to, slice_request.cway)
				# road_segment_rows.sort(key=lambda item: (item["properties"]["START_SLK"]))
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
			feature_collection_to_send = {
				"type":     "Feature",
				"geometry": {
					"type":     "GeometryCollection",
					"geometries": slice_results
				}
			}
			# print(feature_collection_to_send)
			dat_to_send = json.dumps(feature_collection_to_send).encode("utf-8")
			# dat_to_send = serialise_output_geometry(slice_results, request_output_type).encode("utf-8")
			time_end_slice = time.time()
			print(f"time to slice {time_end_slice-time_start_slice}")
			self.send_response(HTTPStatus.OK)
			self.send_header("Content-Type", "text/plain; charset=UTF-8")
			self.send_header("Content-Length", str(len(dat_to_send)))
			self.end_headers()
			self.wfile.write(dat_to_send)
		
		except Slice_Network_Exception as slice_network_exception:
			self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR, f"error: unable to slice network with the provided parameters: {slice_network_exception.message}")
			self.end_headers()
			return
		# except Serialise_Results_Exception as serialise_results_exception:
		# self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR, f"error: unable to serialise results with the provided parameters: {serialise_results_exception.message}")
		# self.end_headers()
		# return
		except Exception as e:
			exc_type, exc_obj, exc_tb = sys.exc_info()
			file_name = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
			print(exc_type, file_name, exc_tb.tb_lineno)
			print(f"Encountered unknown error on request {self.path}")
			print(e)
			self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR, "unknown error")
			self.end_headers()
			return


address = ('', 8010)
print(f"sering on {address}")
server = ThreadingHTTPServer(address, handle_get)
server.serve_forever()