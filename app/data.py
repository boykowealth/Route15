import geopandas as gpd

def mapSave():
    gdf = gpd.read_file("https://data.calgary.ca/resource/3u3x-hrc7.geojson")
    gdf.to_feather("plus15_calgary.feather")

def mapData():
    gdf = gpd.read_file("https://data.calgary.ca/resource/3u3x-hrc7.geojson")
    return gdf