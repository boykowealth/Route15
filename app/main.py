# File: main.py
import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QGraphicsView, QGraphicsScene, QGraphicsLineItem
from PySide6.QtGui import QPen, QPainter
from PySide6.QtCore import Qt, QEvent

from shapely.geometry import LineString, MultiLineString
from data import paths
from tile_loader import TileLayer

class ZoomableGraphicsView(QGraphicsView):
    def __init__(self):
        super().__init__()
        self.scale(1, -1)

    def wheelEvent(self, event):
        zoom_in_factor = 1.25
        zoom_out_factor = 1 / zoom_in_factor

        old_pos = self.mapToScene(event.position().toPoint())
        zoom_factor = zoom_in_factor if event.angleDelta().y() > 0 else zoom_out_factor
        self.scale(zoom_factor, zoom_factor)

        new_pos = self.mapToScene(event.position().toPoint())
        delta = new_pos - old_pos
        self.translate(delta.x(), delta.y())

class Plus15Map(QMainWindow):
    def __init__(self, gdf):
        super().__init__()
        self.setWindowTitle("Calgary +15 Map (Local Tiles, Flipped Y)")
        self.resize(400, 750)

        self.view = ZoomableGraphicsView()
        self.scene = QGraphicsScene()
        self.view.setScene(self.scene)
        self.setCentralWidget(self.view)

        self.tile_layer = TileLayer(self.scene, tiles_root="tiles_cartodb_positron")

        self.draw_lines(gdf)
        self.update_tiles()

        self.view.setRenderHint(QPainter.Antialiasing)
        self.view.setDragMode(QGraphicsView.ScrollHandDrag)
        self.view.viewport().installEventFilter(self)

    def draw_lines(self, gdf):
        pen = QPen(Qt.red)
        pen.setWidth(2)

        min_x, min_y = float('inf'), float('inf')
        max_x, max_y = float('-inf'), float('-inf')

        for geom in gdf.geometry:
            if isinstance(geom, LineString):
                lines = [geom]
            elif isinstance(geom, MultiLineString):
                lines = geom.geoms
            else:
                continue

            for line in lines:
                coords = list(line.coords)
                for i in range(len(coords) - 1):
                    x1, y1 = coords[i]
                    x2, y2 = coords[i + 1]

                    x1s, y1s = x1, y1
                    x2s, y2s = x2, y2

                    min_x = min(min_x, x1s, x2s)
                    min_y = min(min_y, y1s, y2s)
                    max_x = max(max_x, x1s, x2s)
                    max_y = max(max_y, y1s, y2s)

                    line_item = QGraphicsLineItem(x1s, y1s, x2s, y2s)
                    line_item.setPen(pen)
                    self.scene.addItem(line_item)

        padding = 500
        self.scene.setSceneRect(
            min_x - padding,
            min_y - padding,
            (max_x - min_x) + 2 * padding,
            (max_y - min_y) + 2 * padding,
        )
        print(f"Scene Rect (EPSG:3857 meters): {self.scene.sceneRect()}")

        self.view.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)

    def update_tiles(self):
        zoom_level = 15
        self.tile_layer.update_tiles(self.scene.sceneRect(), zoom_level)

    def eventFilter(self, obj, event):
        if event.type() in (QEvent.Wheel, QEvent.MouseMove):
            self.update_tiles()
        return super().eventFilter(obj, event)

if __name__ == "__main__":
    app = QApplication(sys.argv)

    gdf = paths()
    gdf_projected = gdf.to_crs(epsg=3857)

    window = Plus15Map(gdf_projected)
    window.show()
    sys.exit(app.exec())
