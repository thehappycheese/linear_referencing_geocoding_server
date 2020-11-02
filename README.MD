# Linear Referencing Geocoding Server

## Purpose
Runs a REST server on localhost:8001 which will slice linear referenced
portions of the Main Roads Western Australia road network based on SLK (Straight Line Kilometer).

Sliced sections can be optionally filtered by carriageway,
and can be optionally offset.
See the 'Usage' section below for more detail.

The response will be GeoJSON with the following format
```json5
{
  "type":"Feature",
  "properties":null,
  "geometry":{"type":"LineString", /*...*/}, //OR
  "geometry":{"type":"MultiLineString", /*...*/}, // OR
  "geometry":{"type":"GeometryCollection", "geometries":[/*...*/]}, // OR
}
``` 
At the moment the response is served without any fancy headers, just whatever the Flask default response headers are.

## Installation

### Python
To run this server python 3.7+ is required, and the packages `geopandas`, `flask` and `waitress` must be installed.

In a non-admin environment this can be slightly challenging to set up.
There are two ways to set up python that might work:

1. Install python through the 'microsoft store' then install required packages using `pip install <package name>`
   (I have not tested this option) OR
2. **Recommended:** Download and install Miniconda/Conda
   - Conda is the preferred option rater than the microsoft store since packages installed via `conda install <package name>`
     are more likely to come with precompiled binaries and 'just work'
   - If the conda installer doesnt work,
     - Obtain a zip file download.
     - Extract the zip into `%USERPROFILE%\Miniconda\...` 
       (ie `C:\Users\e12345\Miniconda\`)
     - search for the windows "Edit environment variables for your account" from the start menu.
     - Edit the PATH variable and append the following three entries:
       - `%USERPROFILE%\Miniconda\`
       - `%USERPROFILE%\Miniconda\Library\bin`
       - `%USERPROFILE%\Miniconda\Scripts`
3. once you have installed conda, you may need to restart your machine.
   To verify it all worked, open command prompt and try
   ```bat
   C:\Users\e12345>conda activate
   (base) C:\Users\e12345>python --version
   [some python version 3.7+ will be displayed]
   ```     

4. Once your python environment is set up, install the three dependencies as follows
   ```bat
   C:\Users\e12345>conda activate
   (base) C:\Users\e12345>conda install geopandas
   (base) C:\Users\e12345>conda install flask
   (base) C:\Users\e12345>conda install waitress
   ```

### Data Source Required:
As is, this script will try to load data from a file geodatabase called `data.gdb` (from the same folder as main.py) containing a feature collection called `NTWK_IRIS_Road_Network_20201029`. This is not included in the repo due to the size.

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
(base) C:\Users\e12345\some\path\to\folder\containing\main_py>python main.py
```
Then go into your browser and paste the following URL into the locaiton bar to confirm everything is working
> http://localhost:8001/?road=H001,H012&slk_from=6.3,16.4&slk_to=7,17.35&offset=-5,5&cway=L,R

Note
 - that each parameter can accept a list of values separated by a comma or just a single value.
  In the example above two values are provided for each parameter. eg. road=H001,H012 (Albany Highway and Leach Highway)
 - All lists must be the same length.
 - Only one GeoJSON "Feature" will be returned with either
   - a single "LineString" or "MultiLineString" geometry or
   - a "GeometryGroup"
 
the parameters are
|Name|Description|Example Value|Optional|
|---|---|---|---|
|road|Main Roads Road Number or Local Government Road Number|`road=H001`|No|
|slk_from|Straight Line Kilometer to start the segment|`slk_from=1.55`|No|
|slk_to|Straight Line Kilometer to end the segment|`slk_to=2.3`|No|
|cway|Filter for the carriageway. Must be some combination of the letters `L`, `R` and `S`|`cway=LS` or `cway=RS`|Yes|
|offset|Number of meters to offset the resulting line segments. Large values may not produce any output. Negative values are to the left of the road (in slk direction) and positive values are to the right.|`offset=4` or `offset=-3.5`|Yes|

## Ideas for Improvement
Show the 'usage' section above if the URL is called with no parameters

Add an optional `show=true` parameter which will display the resulting GeoJSON in a statically served page with an openlayers map for debugging purposes.

Permit the injection of arbitrary "properties" into the returned feature by accepting arbitrary url parameters
(maybe not. seems like it would generally be easier to add them afterwards than deal with this complexity and sending the data in both directions.)

Optionally populate the feature "properties" with a summary of segment length or any other useful data (the query that generated it perhaps).
Perhaps the surface width database could also be loaded and a surface "area" property could be returned.

Maybe elevation data could be sliced and attached as well?
That's probably pushing it a bit too complicated...
the returned GeoJSON would be difficult to interpret due to the potentially many geometries returned per feature.
But GeoJSON can encode a third coordinate per point... so maybe not that hard really. 