import json
from datetime import datetime
import mysql.connector
import os
import requests


def split_by_geom_size(features, num_points):
	offset = 0
	coordinate_count = 0
	for index, item in enumerate(features):
		coordinate_count += len(item["geometry"]["coordinates"])
		if coordinate_count > num_points:
			yield features[offset:index]
			offset = index
			coordinate_count = len(item["geometry"]["coordinates"])


def download_features():
	request = requests.get("http://portal-mainroads.opendata.arcgis.com/datasets/082e88d12c894956945ef5bcee0b39e2_17.geojson")
	print("Data downloaded")
	geojson = request.json()
	print("JSON parsed")
	features = (tuple(feature["properties"][item] for item in ["ROAD", "START_SLK", "END_SLK", "CWY"]) + (json.dumps(feature["geometry"]),) for feature in geojson["features"])
	print("Unused fields stripped")
	return (chunk for chunk in split_by_geom_size(features, 10_000))


def do_update():
	try:
		print("Try connect to database")
		db = mysql.connector.connect(
			host="db",
			user="root",
			passwd=os.environ["MYSQL_ROOT_PASSWORD"],
			database=os.environ["MYSQL_DATABASE"],
			# use_pure=True  # enables pure python backend. the new default is the C lib, has errors though. So use_pure is needed if we need to use the ST_AsWKB()
		)
		cur = db.cursor()
		print("Connected")
		
		# TODO: check timestamp
		# data_up_to_date = True
		# try:
		# 	cur.execute("""
		# 		SELECT Last(*) FROM TABLE Last_Refresh;
		# 	""")
		# 	date_refreshed = next(cur)[0][0]
		# 	if (datetime.now() - date_refreshed).days > 30:
		# 		data_up_to_date = False
		# except:
		# 	print("could not select from table Last_Refresh")
		# 	cur.execute("""CREATE TABLE Last_Refresh(
		# 		REFRESH DATETIME
		# 	);""")
		# try:
		# 	cur.execute("TRUNCATE Last_Refresh;")
		# 	print("Deleted old Last_Refresh.")
		# except:
		# 	print("65")
		# if data_up_to_date:
		# 	db.close()
		# 	return True
		#
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
			for num, chunk in enumerate(download_features()):
				print(f"Inserting chunk {num} consisting of {len(chunk)} records")
				cur.executemany("""
					INSERT INTO Road_Network (ROAD, START_SLK, END_SLK, CWY, geom)
					VALUES (%s, %s, %s ,%s, ST_GeomFromGeoJSON(%s))
				""", chunk)
				db.commit()
		except Exception as e:
			raise Exception("filed to insert data into table") from e
	finally:
		try:
			cursor.close()
		except:
			pass
		try:
			db.close()
		except:
			pass
