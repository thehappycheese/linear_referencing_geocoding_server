# Linear Referencing Geocoding Server

## Purpose
Runs a REST server on localhost:8001 which will slice linear referenced
portions of the Main Roads Western Australia road network based on SLK (Straight Line Kilometer).

Sliced sections can be optionally filtered by carriageway,
and can be optionally offset.
For url parameters see the 'Usage' section below.

The response will be GeoJSON with the following format
```JSON
{
  "type":"Feature",
  "properties":null,
  "geometries":[
    {"type":"LineString",...},
    {"type":"MultiLineString",...},
    ...
  ]
}
``` 
At the moment the response is served without any fancy headers, just whatever the Flask default response headers are.

## Data Source Required:
As is, this script will try to load data from a file geodatabase called `data.gdb` containing a feature collection called `NTWK_IRIS_Road_Network_20201029`. This is not included in the repo due to the size.

However this same data is publicly available from https://catalogue.data.wa.gov.au/dataset/mrwa-road-network as a GeoJSON file.

To get this script up and running you will need to replicate the `data.gdb` or download a copy of the GeoJSON file and somehow modify the following lines of code in **main.py**:
 
```python
path_to_gdb = r"data.gdb"
gdf_all_roads: gpd.GeoDataFrame = gpd.read_file(
    path_to_gdb,
    layer="NTWK_IRIS_Road_Network_20201029"
)
```

## Usage
Start the server
```bat
>python main.py
```
Then go into your browser and paste the following URL into the locaiton bar to confirm everything is working
> http://localhost:8001/?road=H001,H012&slk_from=6.3,16.4&slk_to=7,17.35&offset=-5,5&cway=L,R

Note
 - that each parameter can accept a list of values separated by a comma or just a single value.
  In the example above two values are provided for each parameter. eg. road=H001,H012 (Albany Highway and Leach Highway)
 - All lists must be the same length.
 - Only 1 feature will be returned with multiple geometries.
 
the parameters are
|Name|Description|Example Value|Optional|
|---|---|---|---|
|road|Main Roads Road Number or Local Government Road Number|`road=H001`|No|
|slk_from|Straight Line Kilometer to start the segment|`slk_from=1.55`|No|
|slk_to|Straight Line Kilometer to end the segment|`slk_to=2.3`|No|
|cway|Filter for the carriageway. Must be some combination of the letters `L`, `R` and `S`|`cway=LS` or `cway=RS`|Yes|
|offset|Number of meters to offset the resulting line segments. Large values may not produce any output. Negative values are to the left of the road (in slk direction) and positive values are to the right.|`offset=4` or `offset=-3.5`|Yes|