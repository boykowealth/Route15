import geopandas as gpd
import pandas as pd

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

def businessSave():
    url = "https://data.calgary.ca/resource/vdjc-pybd.csv"
    df = pd.read_csv(url)

    df.to_feather("calgary_businesses.feather")

def businessData():
    url = "https://data.calgary.ca/resource/vdjc-pybd.csv"
    df = pd.read_csv(url)

    return df