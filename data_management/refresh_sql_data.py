import json
import re
import datetime
import mysql.connector
import os

import requests

re_preamble = re.compile(r"^({\s*\"type\"\s*:\s*\"FeatureCollection\".*?features\"\s*:\s*\[\s*)(.*?)$", flags=re.DOTALL)
re_feature = re.compile(r"^(\s*{\s*\"type\"\s*:\s*\"Feature\".*?}\s*}\s*),(.*?)$", flags=re.DOTALL)


def parse(text, pattern: re.Pattern):
	result = pattern.search(text)
	if result:
		return result.groups()
	else:
		return None, text


def strip_feature(feature):
	return tuple(feature["properties"][item] for item in ["ROAD", "START_SLK", "END_SLK", "CWY"]) + (json.dumps(feature["geometry"]),)


def stream_down():
	request = requests.get("http://portal-mainroads.opendata.arcgis.com/datasets/082e88d12c894956945ef5bcee0b39e2_17.geojson", stream=True)
	
	buffer = ""
	
	state = "trim_preamble"
	
	current_file_length = 0
	current_road = None
	current_features = []
	
	file_count = 0
	
	for chunk_bytes in request.iter_content(chunk_size=8192):
		buffer += chunk_bytes.decode("utf-8")
		if state == "trim_preamble":
			preamble, buffer = parse(buffer, re_preamble)
			if preamble is not None:
				state = "parse_features"
		
		if state == "parse_features":
			while True:
				feature_string, buffer = parse(buffer, re_feature)
				if feature_string is None:
					if current_features:
						yield current_features
					break
				current_file_length += len(feature_string)
				feature = strip_feature(json.loads(feature_string))
				if feature[0] != current_road:
					if current_road is None:
						current_road = feature[0]
					else:
						if current_file_length > 2_000_000:
							print(f"yield {len(current_features)} features with size of {current_file_length}")
							yield current_features
							
							file_count += 1
							current_road = feature[0]
							current_features = []
							current_file_length = 0
				current_features.append(feature)


def do_update():
	db = mysql.connector.connect(
		host="db",
		user="root",
		passwd=os.environ["MYSQL_ROOT_PASSWORD"],
		database=os.environ["MYSQL_DATABASE"],
		# use_pure=True  # enables pure python backend. the new default is the C lib, has errors though. So use_pure is needed if we need to use the ST_AsWKB()
	)
	cur = db.cursor()
	
	try:
		cur.execute("""
			SELECT Last(*) FROM TABLE Last_Refresh;
		""")
		date_refreshed = next(cur)[0]
		if (datetime.now()-date_refreshed).
	except:
		try:
			cur.execute("TRUNCATE Last_Refresh;")
			print("Deleted old Last_Refresh.")
		except:
			print("65")
		
	
	
	
	# TODO: check timestamp
	try:
		print("Deleting old data.")
		cur.execute("DROP TABLE Road_Network;")
	except:
		pass
	
	print("Creating new table.")
	cur.execute("""
		CREATE TABLE Road_Network  (
			ID INT NOT NULL AUTO_INCREMENT,
			ROAD VARCHAR(20),
			START_SLK FLOAT,
			END_SLK FLOAT,
			CWY ENUM('Single', 'Left', 'Right'),
			geom GEOMETRY,
			PRIMARY KEY (ID)
		);
	""")
	try:
		for chunk in stream_down():
			cur.executemany("""
				INSERT INTO Road_Network (ROAD, START_SLK, END_SLK, CWY, geom)
				VALUES (%s, %s, %s ,%s, ST_GeomFromGeoJSON(%s))
			""", chunk)
			db.commit()
	finally:
		db.close()
