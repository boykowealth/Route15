import geopandas as gpd

def mapSave():
    gdf = gpd.read_file("https://data.calgary.ca/resource/3u3x-hrc7.geojson")
    gdf.to_feather("plus15_calgary.feather")

def mapData():
    gdf = gpd.read_file("https://data.calgary.ca/resource/3u3x-hrc7.geojson")
    return gdf

def paths():
    gdf = mapData()
    lines = gdf.geometry.boundary
    lines_gdf = gpd.GeoDataFrame(geometry=lines, crs=gdf.crs)
    return lines_gdf
