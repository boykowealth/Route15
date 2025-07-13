# File: tile_data.py
import os
import requests
import mercantile

# Downtown Calgary lat/lon
LAT = 51.0469
LON = -114.0658
ZOOM = 15

TILE_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
TILES_DIR = "tiles"

def download_tile(z, x, y):
    url = TILE_URL.format(z=z, x=x, y=y)
    out_dir = os.path.join(TILES_DIR, str(z), str(x))
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{y}.png")

    if os.path.exists(out_path):
        return  # Skip already downloaded

    headers = {
        "User-Agent": "Route15/1.0 (braydenboyko@boykowealth.com)",
    }

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        with open(out_path, "wb") as f:
            f.write(resp.content)
        print(f"Downloaded tile {z}/{x}/{y}")
    except Exception as e:
        print(f"Failed to download {url}: {e}")

def main():
    # Get center tile
    center_tile = mercantile.tile(LON, LAT, ZOOM)
    print(f"Center tile at zoom {ZOOM}: x={center_tile.x}, y={center_tile.y}")

    # Define how many tiles to download around center
    radius = 3  # downloads a 7x7 tile square

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

    print(f"Completed downloading {count} tiles.")

if __name__ == "__main__":
    main()
