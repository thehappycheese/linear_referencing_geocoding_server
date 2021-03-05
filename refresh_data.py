# {
# "type": "FeatureCollection",
# "name": "Road_Network",
# "crs": { "type": "name", "properties": { "name": "urn:ogc:def:crs:OGC:1.3:CRS84" } },
# "features": [
# { "type": "Feature", "properties": { "OBJECTID": 128965992, "ROAD": "X001", "ROAD_NAME": "High Wide Load Oversize Cross Over (Restricted Access) (H018 to Military Rd)", "COMMON_USAGE_NAME": "High Wide Load Oversize Cross Over (Restricted Access) (H018 N of Bushmead Rd)", "START_SLK": 0.0, "END_SLK": 0.03, "CWY": "Single", "START_TRUE_DIST": 0.0, "END_TRUE_DIST": 0.03, "NETWORK_TYPE": "Crossover", "RA_NO": "07", "RA_NAME": "Metropolitan", "LG_NO": "106", "LG_NAME": "Mundaring", "START_NODE_NO": "159483", "START_NODE_NAME": "Roe Hwy", "END_NODE_NO": "159484", "END_NODE_NAME": "Roe Hwy", "DATUM_NE_ID": 268144340, "NM_BEGIN_MP": 0, "NM_END_MP": 30, "NETWORK_ELEMENT": "X001\/1-S", "ROUTE_NE_ID": 268144339, "GEOLOCSTLength": 0.00029295128658892664 }, "geometry": { "type": "LineString", "coordinates": [ [ 116.016386821440108, -31.908495094549608 ], [ 116.016275005352838, -31.90857095014394 ], [ 116.016133725452107, -31.908641315586749 ] ] } },
import json
import time

import lz4
import lz4.frame
import requests
import re
from urllib.parse import urlparse
# import bson  # Turns out using bson is 10 times slower because it is not implemented in native libraries like json is. Sad. Should be 10 times faster.

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


def split_by_geom_size(features, num_points):
	offset = 0
	coordinate_count = 0
	first_road = features[0]["properties"]["ROAD"]
	current_road = None
	for index, item in enumerate(features):
		coordinate_count += len(item["geometry"]["coordinates"])
		if coordinate_count > num_points and item["properties"]["ROAD"] != current_road:
			last_road = current_road
			yield features[offset:index], first_road, current_road
			offset = index
			coordinate_count = len(item["geometry"]["coordinates"])
			first_road = item["properties"]["ROAD"]
		current_road = item["properties"]["ROAD"]


def refresh_data():
	delete_folder_content("data/")
	
	# request = requests.get("http://portal-mainroads.opendata.arcgis.com/datasets/082e88d12c894956945ef5bcee0b39e2_17.geojson")
	request = requests.get("http://localhost:8005/Road_Network.geojson")
	print("file downloaded loaded")
	feature_collection = request.json()
	print("json parsed")
	features = sorted(feature_collection["features"], key=lambda item: item["properties"]["ROAD"])
	print("sorted")
	new_registry = {}
	for num, (chunk, first_road, last_road) in enumerate(split_by_geom_size(features, 5000)):
		print(f"chunk no {num} ({len(chunk)} rows) from {first_road} to {last_road}")
		output_filename = f"{num}.json.lz4"
		with lz4.frame.open("data/" + output_filename, mode="wb") as lz4_file:
			# lz4_file.write(bson.dumps({
			# 	"type":     "FeatureCollection",
			# 	"crs":      {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
			# 	"features": chunk
			# }))
			lz4_file.write(json.dumps({
				"type":     "FeatureCollection",
				"crs":      {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
				"features": chunk
			}).encode("utf-8"))
		
		new_registry[output_filename] = (first_road, last_road)
	print(new_registry)
	
	with lz4.frame.open("data/reg.json.lz4", mode="wb") as lz4_file:
		# lz4_file.write(bson.dumps(new_registry))
		lz4_file.write(json.dumps(new_registry).encode("utf-8"))
	return new_registry


def load_registry():
	try:
		with lz4.frame.open("data/reg.json.lz4", mode="rb") as lz4_file:
			f = lz4_file.read()
			# return bson.loads(f)
			return json.loads(f.decode("utf-8"))
	except:
		raise Exception("Registry could not be loaded. try .refresh_data() ?")


def lookup_road_file(registry, road):
	try:
		file = next(k for k, v in registry.items() if v[0] <= road <= v[1])
		return file
	except:
		raise Exception("road number not found in registry")


def fetch(registry, road):
	file = lookup_road_file(registry, road)
	with lz4.frame.open(f"data/{file}", "rb") as lz4_file:
		f = lz4_file.read()
		# feature_collection = bson.loads(f)
		feature_collection = json.loads(f.decode("utf-8"))
	
	return [feature for feature in feature_collection["features"] if feature["properties"]["ROAD"] == road]


def fetch_filter(registry, road: str, request_slk_from: float, request_slk_to: float, carriageway: str):
	road_segments1 = fetch(registry, road)
	result = []
	for item in road_segments1:
		if not (item["properties"]["START_SLK"] <= request_slk_to and item["properties"]["END_SLK"] >= request_slk_from):
			continue
		
		if carriageway == "LRS":
			result.append(item)
		elif carriageway == "LS" and (item["properties"]["CWY"] == "Left" or item["properties"]["CWY"] == "Single"):
			result.append(item)
		elif carriageway == "RS" and (item["properties"]["CWY"] == "Right" or item["properties"]["CWY"] == "Single"):
			result.append(item)
		elif carriageway == "LR" and (item["properties"]["CWY"] == "Right" or item["properties"]["CWY"] == "Left"):
			result.append(item)
		elif carriageway == "R" and item["properties"]["CWY"] == "Right":
			result.append(item)
		elif carriageway == "L" and item["properties"]["CWY"] == "Left":
			result.append(item)
		elif carriageway == "S" and item["properties"]["CWY"] == "Single":
			result.append(item)
	# else:
	# 	raise Slice_Network_Exception(f"Invalid carriageway parameter: {carriageway}. Must be any combination of the three letters 'L', 'R' and 'S'. eg &cwy=LR or &cwy=RL or &cwy=S. omit the parameter to query all.")
	
	return result


def test():
	try:
		t0 = time.time()
		reg = load_registry()
		t1 = time.time()
		print(f"time to load registry data {t1 - t0}")
		print(reg)
	except:
		print("unable to load registry... attempting to refresh data")
		t0 = time.time()
		reg = refresh_data()
		t1 = time.time()
		print(f"time to refresh data {t1 - t0}")
		
		t0 = time.time()
		reg = load_registry()
		t1 = time.time()
		print(f"time to load registry data {t1 - t0}")
	
	t0 = time.time()
	fetched = fetch(reg, "H001")
	t1 = time.time()
	print(f"time to fetch H001 {t1 - t0}")
	print(f"found {len(fetched)} features")
	print(fetched[0:10])
	
	t0 = time.time()
	fetched = fetch(reg, "H002")
	t1 = time.time()
	print(f"time to fetch H002 {t1 - t0}")
	print(f"found {len(fetched)} features")
	print(fetched[0:10])
	
	t0 = time.time()
	fetched = fetch(reg, "H027")
	t1 = time.time()
	print(f"time to fetch H027 {t1 - t0}")
	print(f"found {len(fetched)} features")
	print(fetched[0:10])
	
	t0 = time.time()
	fetched = fetch_filter(reg, "H001", 5, 10, "LR")
	t1 = time.time()
	print(f"time to fetch H001 from slk 5 to 10 cway LR {t1 - t0}")
	print(f"found {len(fetched)} features")
	print(fetched[0:10])
