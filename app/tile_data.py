import os
import requests
import mercantile


LAT = 51.0469
LON = -114.0658
ZOOM = 18 

TILE_PROVIDERS = {
    "openstreetmap": {
        "url": "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
        "attribution": "OpenStreetMap contributors"
    },
    "cartodb_positron": {
        "url": "https://cartodb-basemaps-a.global.ssl.fastly.net/light_all/{z}/{x}/{y}.png",
        "attribution": "CartoDB"
    },
    "cartodb_positron_retina": {
        "url": "https://cartodb-basemaps-a.global.ssl.fastly.net/light_all/{z}/{x}/{y}@2x.png",
        "attribution": "CartoDB"
    },
    "cartodb_dark": {
        "url": "https://cartodb-basemaps-a.global.ssl.fastly.net/dark_all/{z}/{x}/{y}.png",
        "attribution": "CartoDB"
    },
    "cartodb_dark_retina": {
        "url": "https://cartodb-basemaps-a.global.ssl.fastly.net/dark_all/{z}/{x}/{y}@2x.png",
        "attribution": "CartoDB"
    },
    "cartodb_voyager": {
        "url": "https://cartodb-basemaps-a.global.ssl.fastly.net/rastertiles/voyager/{z}/{x}/{y}.png",
        "attribution": "CartoDB"
    },
    "stamen_toner": {
        "url": "https://tiles.stadiamaps.com/tiles/stamen_toner/{z}/{x}/{y}.png",
        "attribution": "Stamen Design, CC BY 3.0"
    },
    "stamen_terrain": {
        "url": "https://tiles.stadiamaps.com/tiles/stamen_terrain/{z}/{x}/{y}.png",
        "attribution": "Stamen Design, CC BY 3.0"
    },
    "stamen_watercolor": {
        "url": "https://tiles.stadiamaps.com/tiles/stamen_watercolor/{z}/{x}/{y}.jpg",
        "attribution": "Stamen Design, CC BY 3.0"
    },
    "esri_world_imagery": {
        "url": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        "attribution": "Esri"
    },
    "esri_world_street": {
        "url": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}",
        "attribution": "Esri"
    },
    "esri_world_topo": {
        "url": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}",
        "attribution": "Esri"
    },
    "carto_light": {
        "url": "https://a.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png",
        "attribution": "CARTO"
    },
    "mapbox_satellite": {
        "url": "https://api.mapbox.com/v4/mapbox.satellite/{z}/{x}/{y}@2x.png?access_token=YOUR_MAPBOX_TOKEN",
        "attribution": "Mapbox",
        "tile_size": 512
    },
    "mapbox_streets": {
        "url": "https://api.mapbox.com/v4/mapbox.streets/{z}/{x}/{y}@2x.png?access_token=YOUR_MAPBOX_TOKEN",
        "attribution": "Mapbox",
        "tile_size": 512
    },
}

SELECTED_PROVIDER = "cartodb_positron" 

TILE_URL = TILE_PROVIDERS[SELECTED_PROVIDER]["url"]
TILES_DIR = f"tiles_{SELECTED_PROVIDER}"

def download_tile(z, x, y):
    url = TILE_URL.format(z=z, x=x, y=y)
    out_dir = os.path.join(TILES_DIR, str(z), str(x))
    os.makedirs(out_dir, exist_ok=True)
    
    extension = ".jpg" if "watercolor" in SELECTED_PROVIDER else ".png"
    out_path = os.path.join(out_dir, f"{y}{extension}")

    if os.path.exists(out_path):
        return 

    headers = {
        "User-Agent": "Plus15Map/1.0 (braydenboyko@boykowealth.com)",
        "Referer": "https://www.openstreetmap.org/"
    }

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        with open(out_path, "wb") as f:
            f.write(resp.content)
        print(f"Downloaded tile {z}/{x}/{y} from {SELECTED_PROVIDER}")
    except Exception as e:
        print(f"Failed to download {url}: {e}")

def main():
    print(f"Using tile provider: {SELECTED_PROVIDER}")
    print(f"Tiles will be saved to: {TILES_DIR}")
    print(f"Attribution: {TILE_PROVIDERS[SELECTED_PROVIDER]['attribution']}")
    
    center_tile = mercantile.tile(LON, LAT, ZOOM)
    print(f"Center tile at zoom {ZOOM}: x={center_tile.x}, y={center_tile.y}")

    radius = 3 

    x_start = center_tile.x - radius
    x_end = center_tile.x + radius
    y_start = center_tile.y - radius
    y_end = center_tile.y + radius

    total_tiles = (x_end - x_start + 1) * (y_end - y_start + 1)
    print(f"Starting download of approx {total_tiles} tiles at zoom {ZOOM}...")

    count = 0
    for x in range(x_start, x_end + 1):
        for y in range(y_start, y_end + 1):
            download_tile(ZOOM, x, y)
            count += 1

    print(f"Completed downloading {count} tiles from {SELECTED_PROVIDER}.")

if __name__ == "__main__":
    main()