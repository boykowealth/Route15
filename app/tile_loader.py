import os
import mercantile
from PySide6.QtWidgets import QGraphicsPixmapItem
from PySide6.QtGui import QPixmap
from pyproj import Transformer

TILE_SIZE = 256

transformer = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)

class TileLayer:
    def __init__(self, scene, tiles_root="tiles", tile_size=256):
        self.scene = scene
        self.tiles_root = tiles_root
        self.tiles = {}
        self.tile_size = tile_size  # Support different tile sizes

    def update_tiles(self, rect, zoom):
        self.clear_tiles()

        left_m = rect.left()
        right_m = rect.right()
        top_m = rect.top()
        bottom_m = rect.bottom()

        min_y = min(top_m, bottom_m)
        max_y = max(top_m, bottom_m)

        left_lon, south_lat = transformer.transform(left_m, min_y)
        right_lon, north_lat = transformer.transform(right_m, max_y)

        print(f"Request bounds EPSG:3857 -> Lon/Lat:")
        print(f"Left: {left_m}, Right: {right_m}, Top: {top_m}, Bottom: {bottom_m}")
        print(f"Lon/Lat bounds: West={left_lon}, East={right_lon}, North={north_lat}, South={south_lat}")

        tiles = list(mercantile.tiles(left_lon, south_lat, right_lon, north_lat, zoom))
        print(f"Tiles requested: {len(tiles)}")

        for tile in tiles:
            key = (tile.z, tile.x, tile.y)
            if key in self.tiles:
                continue

            pixmap = self.load_tile_from_disk(tile)
            if pixmap is None:
                continue

            bounds = mercantile.xy_bounds(tile)
            x = bounds.left
            y = bounds.top 
            width = bounds.right - bounds.left
            height = bounds.top - bounds.bottom

            item = QGraphicsPixmapItem(pixmap)
            item.setScale(width / self.tile_size) 
            item.setTransform(item.transform().scale(1, -1))
            item.setPos(x, y)
            item.setZValue(-10)
            self.scene.addItem(item)
            self.tiles[key] = item

        print(f"Loaded {len(self.tiles)} tiles")

    def get_tile_path(self, tile):
        png_path = os.path.join(self.tiles_root, str(tile.z), str(tile.x), f"{tile.y}.png")
        jpg_path = os.path.join(self.tiles_root, str(tile.z), str(tile.x), f"{tile.y}.jpg")
        
        if os.path.exists(png_path):
            return png_path
        elif os.path.exists(jpg_path):
            return jpg_path
        else:
            return png_path 

    def load_tile_from_disk(self, tile):
        path = self.get_tile_path(tile)
        if not os.path.exists(path):
            return None
        pixmap = QPixmap(path)
        if pixmap.isNull():
            return None
        return pixmap

    def clear_tiles(self):
        for item in self.tiles.values():
            self.scene.removeItem(item)
        self.tiles.clear()