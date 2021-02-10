# this is intended to run in a separate process to the main flask server such that after the refresh the
# memory allocated is released back to the system
import sqlite3

import requests

from data_management.delete_folder_content import delete_folder_content
from data_management.map_cway import MAP_CWAY_TO_INT
from parse_wkb import geojson_to_wkb

import timeit

delete_folder_content("./data/")
conn = sqlite3.connect("./data/database.sqlite")
cur = conn.cursor()
cur.execute("""DROP TABLE IF EXISTS Road_Network""")
cur.execute("""
	CREATE TABLE Road_Network(
		ROAD TEXT,
		START_SLK REAL,
		END_SLK REAL,
		CWY INTEGER,
		GEOM BLOB
	);

""")
cur.execute("""
	CREATE INDEX "Road_Index" ON "Road_Network" ("ROAD"	ASC)
""")

print("trying to download data")
request = requests.get("http://portal-mainroads.opendata.arcgis.com/datasets/082e88d12c894956945ef5bcee0b39e2_17.geojson")
print("download completed")
feature_collection = request.json()
print("data converted to JSON")
features = feature_collection["features"]


def feature_to_record(feature):
	return (
		*(feature["properties"][item] for item in ["ROAD", "START_SLK", "END_SLK"]),
		MAP_CWAY_TO_INT[feature["properties"]["CWY"]],
		geojson_to_wkb(feature["geometry"])
	)


def split_by_geom_size(features, num_points):
	offset = 0
	coordinate_count = 0
	for index, item in enumerate(features):
		coordinate_count += len(item["geometry"]["coordinates"])
		if coordinate_count > num_points:
			yield features[offset:index]
			offset = index
			coordinate_count = len(item["geometry"]["coordinates"])


for num, chunk in enumerate(split_by_geom_size(features, 20_000)):
	print('.', end='')
	cur.executemany("""
			INSERT INTO Road_Network (ROAD, START_SLK, END_SLK, CWY, GEOM)
			VALUES (?, ?, ?, ?, ?)
		""", map(feature_to_record, chunk))
	conn.commit()
print("optimizing")
cur.execute("PRAGMA optimize;")
print("compacting")
cur.execute("PRAGMA vacuume;")

cur.close()
conn.close()

# exit()
# import sqlite3
# import timeit
#
# conn = sqlite3.connect("./data/database.sqlite")
# cur = conn.cursor()
# start = timeit.timeit()
# cur.execute("""SELECT * FROM Road_Network WHERE ROAD="H001" AND START_SLK BETWEEN 10 AND 30""")
# result = [*cur]
# end = timeit.timeit()
# print(result)
# print(f"selected in {end - start}")
