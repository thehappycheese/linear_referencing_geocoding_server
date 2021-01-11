import json
from typing import Union, List, Literal

from shapely.geometry import Point, MultiPoint, MultiLineString, LineString
from shapely.ops import unary_union


def serialise_output_geometry(geometry_list: List[Union[Point, MultiPoint, LineString, MultiLineString]], output_type: Literal["WKT", "GEOJSON"] = "GEOJSON") -> str:
	
	# TODO: make the union operation optional for GeoJSON as it may produce weird results. expose setting to user?
	PERFORM_UNION_ON_GEOMS_FOR_GEOJSON = True
	
	# separate list into points and lines:
	
	point_list = [item for item in geometry_list if isinstance(item, (Point, MultiPoint))]
	# multi_point_list = [item for item in geometry_list if isinstance(item, MultiPoint)]
	line_list = [item for item in geometry_list if isinstance(item, (LineString, MultiLineString))]
	# multi_line_list = [item for item in geometry_list if isinstance(item, MultiLineString)]
	
	if not (line_list or point_list):
		raise Exception("Unable to serialise input; none of the retrieved geometry matched Point, MultiPoint, LineString, or MultiLineString")
		
	if output_type == "WKT":
		if point_list and line_list:
			# TODO: this exception may not be desirable? The code below will work anyway,
			#  but will only keep lines, discarding any points. The aim is to ensures the user doesnt lose data in a way that would be hard to diagnose
			raise Exception("Unable to serialise both points and lines when using the WKT output type. Try GeoJSON output instead.")
		
		result = unary_union(geometry_list).wkt
	
	elif output_type == "GEOJSON":
		result = {
			"type": "Feature",
			"geometry": None
		}
		if len(geometry_list) < 1:
			raise Exception("Empty geometry list")
		elif len(geometry_list) == 1:
			result["geometry"] = geometry_list[0].__geo_interface__
		else:
			if PERFORM_UNION_ON_GEOMS_FOR_GEOJSON:
				geoms = []
				if point_list:
					geoms.append(unary_union(point_list))
				if line_list:
					geoms.append(unary_union(line_list))
				if len(geoms) == 0:
					raise Exception("Something went wrong when computing the union of geometries in the serialise_output_geometry() function")
			else:
				geoms = geometry_list
			
			result["geometry"] = {
				"type": "GeometryCollection",
				"geometries": [
					item.__geo_interface__ for item in geoms
				]
			}
		
		result = json.dumps(result)
	return result