import json
from collections import OrderedDict
from typing import Dict, List

import requests
import re
import lz4.frame
import time

import geopandas

# {
# "type": "FeatureCollection",
# "name": "Road_Network",
# "crs": { "type": "name", "properties": { "name": "urn:ogc:def:crs:OGC:1.3:CRS84" } },
# "features": [
# { "type": "Feature", "properties": { "OBJECTID": 128965992, "ROAD": "X001", "ROAD_NAME": "High Wide Load Oversize Cross Over (Restricted Access) (H018 to Military Rd)", "COMMON_USAGE_NAME": "High Wide Load Oversize Cross Over (Restricted Access) (H018 N of Bushmead Rd)", "START_SLK": 0.0, "END_SLK": 0.03, "CWY": "Single", "START_TRUE_DIST": 0.0, "END_TRUE_DIST": 0.03, "NETWORK_TYPE": "Crossover", "RA_NO": "07", "RA_NAME": "Metropolitan", "LG_NO": "106", "LG_NAME": "Mundaring", "START_NODE_NO": "159483", "START_NODE_NAME": "Roe Hwy", "END_NODE_NO": "159484", "END_NODE_NAME": "Roe Hwy", "DATUM_NE_ID": 268144340, "NM_BEGIN_MP": 0, "NM_END_MP": 30, "NETWORK_ELEMENT": "X001\/1-S", "ROUTE_NE_ID": 268144339, "GEOLOCSTLength": 0.00029295128658892664 }, "geometry": { "type": "LineString", "coordinates": [ [ 116.016386821440108, -31.908495094549608 ], [ 116.016275005352838, -31.90857095014394 ], [ 116.016133725452107, -31.908641315586749 ] ] } },
import shapely

from data_management.delete_folder_content import delete_folder_content

re_preamble = re.compile(r"^({\s*\"type\"\s*:\s*\"FeatureCollection\".*?features\"\s*:\s*\[\s*)(.*?)$", flags=re.DOTALL)
re_feature = re.compile(r"^(\s*{\s*\"type\"\s*:\s*\"Feature\".*?}\s*}\s*),(.*?)$", flags=re.DOTALL)


def parse(text, pattern: re.Pattern):
	result = pattern.search(text)
	if result:
		return result.groups()
	else:
		return None, text


def strip_feature(feature):
	return {
		**feature,
		"properties": {
			item: feature["properties"][item] for item in ["ROAD", "START_SLK", "END_SLK", "CWY"]
		}
	}


def split_by_geom_size(l, num_points):
	sub_list = []
	count = 0
	current_road = None
	for item in l:
		count += len(item["geometry"]["coordinates"])
		if count > num_points and item["properties"]["ROAD"] != last_road:
			yield sub_list
			sub_list = []
			count = 0
		sub_list.append(item)
		
		last_road = item["properties"]["ROAD"]


class Data_Manager:
	
	def __init__(self):
		self.loaded_chunks: OrderedDict[str, geopandas.GeoDataFrame] = OrderedDict()
		self.loaded_chunk_size = 0
	
	def refresh_data(self):
		
		delete_folder_content("data/")
		
		request = requests.get("http://portal-mainroads.opendata.arcgis.com/datasets/082e88d12c894956945ef5bcee0b39e2_17.geojson")
		#request = requests.get("http://localhost:8005/Road_Network.geojson")
		print("loaded")
		feature_collection = request.json()
		print("jsoned")
		
		features = sorted(feature_collection["features"], key=lambda item: item["properties"]["ROAD"])
		print("sorted")
		new_registry = {}
		for num, chunk in enumerate(split_by_geom_size(features, 9000)):
			print(f"chunk no {num} from {chunk[0]['properties']['ROAD']} to {chunk[-1]['properties']['ROAD']}")
			output_filename = f"{num}.json.lz4"
			with lz4.frame.open("data/" + output_filename, mode="wb") as lz4_file:
				lz4_file.write(json.dumps({
					"type":     "FeatureCollection",
					"crs":      {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
					"features": chunk
				}).encode("utf-8"))
			
			new_registry[output_filename] = (chunk[0]['properties']['ROAD'], chunk[-1]['properties']['ROAD'])
		print(new_registry)
		
		with lz4.frame.open("data/reg.json.lz4", mode="wb") as lz4_file:
			lz4_file.write(json.dumps(new_registry).encode("utf-8"))
		self.registry = new_registry
	
	# return
	# iter_count = 0
	# buffer = ""
	#
	# state = "trim_preamble"
	#
	# current_roads_in_file = []
	# current_file_length = 0
	# current_road = None
	# current_features = []
	#
	# new_registry = {}
	#
	# file_count = 0
	#
	# for chunk_bytes in request.iter_content(chunk_size=8192):
	# 	buffer += chunk_bytes.decode("utf-8")
	# 	if state == "trim_preamble":
	# 		preamble, buffer = parse(buffer, re_preamble)
	# 		if preamble is not None:
	# 			state = "parse_features"
	#
	# 	if state == "parse_features":
	# 		while True:
	# 			feature_string, buffer = parse(buffer, re_feature)
	# 			if feature_string is None:
	# 				break
	# 			current_file_length += len(feature_string)
	# 			feature = strip_feature(json.loads(feature_string))
	# 			if feature["properties"]["ROAD"] != current_road:
	# 				if current_road is None:
	# 					current_road = feature["properties"]["ROAD"]
	# 				else:
	# 					if current_file_length > 5_000_000:
	# 						print(f"write out {len(current_features)} features with size of {current_file_length} and roads {', '.join(current_roads_in_file)}")
	# 						output_filename = f"{file_count}.json.lz4"
	# 						with lz4.frame.open("data/" + output_filename, mode="wb") as lz4_file:
	# 							lz4_file.write(json.dumps({
	# 								"type":     "FeatureCollection",
	# 								"crs":      {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
	# 								"features": current_features
	# 							}).encode("utf-8"))
	#
	# 						new_registry[output_filename] = current_roads_in_file
	#
	# 						file_count += 1
	# 						current_road = feature["properties"]["ROAD"]
	# 						current_roads_in_file = []
	# 						current_features = []
	# 						current_file_length = 0
	#
	# 				current_roads_in_file.append(feature["properties"]["ROAD"])
	#
	# 			current_features.append(feature)
	#
	# 		iter_count += 1
	# request.close()
	#
	# with lz4.frame.open("data/reg.json.lz4", mode="wb") as lz4_file:
	# 	lz4_file.write(json.dumps(new_registry).encode("utf-8"))
	# self.registry = new_registry
	
	def load_registry(self):
		try:
			with lz4.frame.open("data/reg.json.lz4", mode="rb") as lz4_file:
				f = lz4_file.read()
				self.registry = json.loads(f.decode("utf-8"))
		except:
			raise Exception("Registry could not be loaded. try .refresh_data() ?")
	
	def lookup_road_file(self, road):
		try:
			file = next(k for k, v in self.registry.items() if v[0] <= road <= v[1])
			return file
		except:
			raise Exception("road number not found in registry")
	
	def fetch(self, road):
		file = self.lookup_road_file(road)
		with lz4.frame.open(f"data/{file}", "rb") as lz4_file:
			f = lz4_file.read()
			feature_collection = json.loads(f.decode("utf-8"))
			df = geopandas.GeoDataFrame.from_features(feature_collection)
		return df[df["ROAD"] == road]
	
	def fetch_filter(self, road: str, request_slk_from: float, request_slk_to: float, carriageway: str) -> geopandas.GeoDataFrame:
		road_segments = self.fetch(road)
		mask = (road_segments["ROAD"] == road) & (road_segments["START_SLK"] <= request_slk_to) & (road_segments["END_SLK"] >= request_slk_from)
		if carriageway == "LS":
			mask = mask & ((road_segments["CWY"] == "Left") | (road_segments["CWY"] == "Single"))
		elif carriageway == "RS":
			mask = mask & ((road_segments["CWY"] == "Right") | (road_segments["CWY"] == "Single"))
		elif carriageway == "LR":
			mask = mask & ((road_segments["CWY"] == "Right") | (road_segments["CWY"] == "Left"))
		elif carriageway == "R":
			mask = mask & (road_segments["CWY"] == "Right")
		elif carriageway == "L":
			mask = mask & (road_segments["CWY"] == "Left")
		elif carriageway == "S":
			mask = mask & (road_segments["CWY"] == "Single")
		elif carriageway == "LRS":
			pass
		# else:
		# 	raise Slice_Network_Exception(f"Invalid carriageway parameter: {carriageway}. Must be any combination of the three letters 'L', 'R' and 'S'. eg &cwy=LR or &cwy=RL or &cwy=S. omit the parameter to query all.")
		
		return road_segments[mask]
	
	def check_mem_use(self):
		print(f"loaded chunk size {len(self.loaded_chunks)} {self.loaded_chunk_size} b {self.loaded_chunks.keys()}")
		while self.loaded_chunk_size > 5_000_000:
			k, v = self.loaded_chunks.popitem()
			self.loaded_chunk_size -= v.memory_usage(deep=True).sum()


def test():
	dm = Data_Manager()
	dm.load_registry()
	t0 = time.time()
	# dm.refresh_data()
	t1 = time.time()
	print(f"time to refresh data {t1 - t0}")
	
	t0 = time.time()
	fetched = dm.fetch("H001")
	t1 = time.time()
	print(f"time to fetch H001 {t1 - t0}")
	print(f"found {len(fetched.index)} features")
	print(f"used {dm.loaded_chunk_size} bytes of space")
	print(fetched)
	t0 = time.time()
	fetched = dm.fetch("H002")
	t1 = time.time()
	print(f"time to fetch H002 {t1 - t0}")
	print(f"found {len(fetched.index)} features")
	print(f"used {dm.loaded_chunk_size} bytes of space")
	print(fetched)
	t0 = time.time()
	fetched = dm.fetch("H027")
	t1 = time.time()
	print(f"time to fetch H027 {t1 - t0}")
	print(f"found {len(fetched.index)} features")
	print(f"used {dm.loaded_chunk_size} bytes of space")
	print(fetched)
	
	print(dm.loaded_chunks.keys())

test()