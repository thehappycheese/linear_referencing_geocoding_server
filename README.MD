# Linear Referencing Geocoding Server

## Purpose
Runs a REST server on localhost:8001 which will slice
portions of the Main Roads Western Australia road network based on pair of SLKs
(Straight Line Kilometer) and return a GeoJSON feature.

Sliced sections can be optionally filtered by carriageway,
and can be optionally offset.
See the 'Usage' section below for more detail.

The original LineString geometry will be cut at the specified endpoints, and properly truncated to reflect the requested SLK interval.
Points will be returned instead of lines if a zero length SLK interval is requested.

## Yes but Why?
It is meant to be used in Excel or PowerBI to add a new text column of consisting of GeoJSON features based on each row of the original data.
(See the 'Useage' section below). This can then be used to visualise the data against a map.

## Yes but don't we already have tools for that?

Yes, but you are going to need an arcmap licence and know how to use it very well.
To slice linestring intervals at arbitrary SLKs is hard to do (or maybe requires additional tools not available in the basic licence).

This way you can do it in Excel or PowerBI or even a web browser. It can be used from a variety of technologies to slice the road network and update dashboards etc without any access to ESRI tools.

## What tool can visualise that kind of data anyway?
See my related PowerBI custom visual project  https://github.com/thehappycheese/powerbi-visual-geojson-map-1

## Response Format
The response will be GeoJSON with the following format
```json5
{
  "type":"Feature",
  "properties":null,
  "geometry":{"type":"LineString", /*...*/}, //OR
  "geometry":{"type":"MultiLineString", /*...*/}, // OR
  "geometry":{"type":"GeometryCollection", "geometries":[/*...LineStrings or MultiLineStrings...*/]}
}
``` 
- The response mime-type will be "application/json".
- HTTP status code 400 will indicate invalid url parameters.
- HTTP status code 500 will indicate unknown server error.

## Installation

### Python
To run this server python 3.7+ is required, and the packages `geopandas` and `flask` must be installed.

In a non-admin environment this can be slightly challenging to set up.
There are two ways to set up python that might work:

1. Install python through the 'microsoft store' then install required packages using `pip install <package name>`
   - The `pip install` method does not typically work on windows because geopandas depends on a heap of binary (.dll / .exe) files which pip does not install properly. There is a lot of fiddling involved to get this to work on windows and I don't think its worth anyone's time.
2. **Recommended:** Download and install Miniconda
   - Miniconda is the preferred option because it will install
     precompiled binaries and 'just work'
   - Miniconda is the same as 'Anaconda' but without the hundreds of pre-installed packages.
     For a quicker download an install I recommend this option.
   - If the conda installer doesnt work,
     - Obtain a zip file download.
     - Extract the zip into `%USERPROFILE%\Miniconda\...` 
       (ie `C:\Users\e12345\Miniconda\`)
     - Search for the windows "Edit environment variables for your account" from the start menu.
     - Edit the PATH variable and append the following three entries:
       - `%USERPROFILE%\Miniconda\`
       - `%USERPROFILE%\Miniconda\Library\bin`
       - `%USERPROFILE%\Miniconda\Scripts`
3. Once conda is installed, you may need to restart your machine.
   Open command prompt or powershell and try the following:
   ```bat
   C:\Users\e12345>conda activate
   (base) C:\Users\e12345>python --version
   [some python version 3.7+ will be displayed]
   ```
   Depending how it was installed conda may also prompt you to type `conda init` which will configure powershell to always activate conda on startup.

4. Once your python environment is set up, install the two dependencies as follows
   ```bat
   C:\Users\e12345>conda activate
   (base) C:\Users\e12345>conda install geopandas
   (base) C:\Users\e12345>conda install flask
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

### Starting the server
Open a terminal and change the working directory to the same folder containing `app.py`.
Run the command
```bat
>python app.py
```
> Note that flask may emit a warning on startup something like the following:
>
> `WARNING: This is a development server. Do not use it in a production deployment.
Use a production WSGI server instead`
>
> This is fine if you are running the server on your local machine (See 'local machine vs cloud' section below )

Then go into your browser and paste the following URL into the location bar to confirm everything is working
> http://localhost:8001/?road=H001,H012&slk_from=6.3,16.4&slk_to=7,17.35&offset=-5,5&cway=L,R

Note
 - Each parameter can accept a list of values separated by a comma or just a single value.
   - In the example above two values are provided for each parameter. eg. road=H001,H012 (Albany Highway and Leach Highway).
   - The **n**<sup>th</sup> item in the `road=` list corresponds with the **n**<sup>th</sup> item in the `slk_from=` list and so on.
   - All lists must be the same length.
 - Only one GeoJSON "Feature" will be returned per request. The Feature `"geometry"` may be any valid GeoJSON geometry object including: 
   - a "Point"
   - a "MultiPoint"
   - a "LineString"
   - a "MultiLineString" or
   - a "GeometryCollection"
 
the parameters are
|Name|Description|Example Value|Optional|
|---|---|---|---|
|road|Main Roads Road Number or Local Government Road Number|`road=H001`|No|
|slk_from|Straight Line Kilometer to start the segment|`slk_from=1.55`|No|
|slk_to|Straight Line Kilometer to end the segment|`slk_to=2.3`|No|
|cway|Filter for the carriageway. Must be some combination of the letters `L`, `R` and `S`|`cway=LS` or `cway=RS`|Yes|
|offset|Number of meters to offset the resulting line segments. Large values may not produce any output. Negative values are to the left of the road (in slk direction) and positive values are to the right.|`offset=4` or `offset=-3.5`|Yes|
|show|If the parameter show is present the results will be displayed in a map. The value of show is not important. Simply append `&show` to the end of the url|`show`|Yes|

### Usage in Excel
The WebService formula can be used as follows in excel to extract information from this service:
```excel
=WEBSERVICE("http://localhost:8001/?road=H001,H012&slk_from=6.3,16.4&slk_to=7,17.35&offset=-5,5&cway=L,R")
```
Concatenation of other cell values can be used to build the request based on each row of the spreadsheet.


### local machine vs cloud
This repo contains a Flask 'app'. To make it a 'webservice' the 'app' must be paired with a suitable 'server'.

While this app was intended to be run in the cloud, it can be executed on a local machine as described above.
Running it locally will use Flask's built in test server which is not intended for deployment to the wide web
(and therefore the warning message described above may appear)
However when it is deployed to the cloud the cloud provider will run a suitable
[WSGI](https://en.wikipedia.org/wiki/Web_Server_Gateway_Interface)
'server' which will safely run this 'app' an pass requests and responses. 


This app should work as-is in any WSGI cloud service (not tested) provided that 
the required dependencies (flask and geopandas) are installed.

Obviously no authentication is implemented in this app. It may be that some
flask middleware can do the job for the specific cloud service?

**Note:** Any kind of authentication will prevent the excel `=WEBSERVICE()` function from working.
Excel is only able to anonymously access webservices and there is no option or workaround to change this.
PowerBI or some other software which can handle (and hopefully automate) this authentication step
would be needed to join the GeoJSON results with your data.

## Ideas for Improvement

Permit the upload of a CSV file with some preset columns which will download a single `{"type":"FeatureCollection",... }` .geojson file as a result.
 - Possibly geopandas may be able to emit a shapefile or other common GIS exchange format.

Permit the injection of arbitrary "properties" into the returned feature by accepting arbitrary url parameters
 - Maybe not a good idea. seems like it would generally be easier to add them afterwards than deal with this complexity and sending the data in both directions.

Optionally populate the feature "properties" with a summary of segment length or any other useful data
 - the query string that generated it perhaps?
 - Perhaps the surface width database could also be loaded and a surface "area" property could be returned.
 - Maybe elevation data could be sliced and attached as well? That's probably pushing it a bit too complicated...

Optionally return a feature for each subquery rather than a single feature with many geometries.
 - I cant think of a use-case for this It would possibly give more flexibility when applying line styles in OpenLayers or Leaflet 

Allow slicing of a road "from the start" or "to the end" possibly by providing an empty value to the `slk_from` or `slk_to` parameters. Or maybe the string `"ALL"` should be used instead. This could potentially break the server if say the whole of Albany Hwy was requested at once.

LineStrings are offset using shapely's default 'round' option for the `.parallelOffset()` function. This produces a lot of extra coordinates in the output to smooth the corners. Most of the time a mitre is probably ok but in some cases will be much worse. Need to do some experiments to find out.

Optionally return a complete GeoJSON document or EsriJSON document, or create a new project which can deal with bulk requests
