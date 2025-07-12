import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QGraphicsView, QGraphicsScene, QGraphicsLineItem
from PySide6.QtGui import QPen, QPainter
from PySide6.QtCore import Qt

import geopandas as gpd
from shapely.geometry import LineString, MultiLineString

from data import paths  # Your function that returns GeoDataFrame in lat/lon (EPSG:4326)

class ZoomableGraphicsView(QGraphicsView):
    def wheelEvent(self, event):
        zoom_in_factor = 1.25
        zoom_out_factor = 1 / zoom_in_factor

        old_pos = self.mapToScene(event.position().toPoint())

        if event.angleDelta().y() > 0:
            zoom_factor = zoom_in_factor
        else:
            zoom_factor = zoom_out_factor

        self.scale(zoom_factor, zoom_factor)

        new_pos = self.mapToScene(event.position().toPoint())
        delta = new_pos - old_pos
        self.translate(delta.x(), delta.y())

class Plus15Map(QMainWindow):
    def __init__(self, gdf):
        super().__init__()
        self.setWindowTitle("Calgary +15 Map (Projected)")
        self.resize(1000, 800)

        self.view = ZoomableGraphicsView()
        self.scene = QGraphicsScene()
        self.view.setScene(self.scene)
        self.setCentralWidget(self.view)

        self.draw_lines(gdf)

    def draw_lines(self, gdf):
        pen = QPen(Qt.darkRed)
        pen.setWidth(2)

        # No scaling needed, projected coords are in meters
        min_x, min_y = float('inf'), float('inf')
        max_x, max_y = float('-inf'), float('-inf')

        for geom in gdf.geometry:
            if isinstance(geom, LineString):
                lines = [geom]
            elif isinstance(geom, MultiLineString):
                lines = geom.geoms
            else:
                continue

            for line_geom in lines:
                coords = list(line_geom.coords)
                for i in range(len(coords) - 1):
                    x1, y1 = coords[i]
                    x2, y2 = coords[i + 1]

                    # Flip Y if needed (Qt coordinate system has Y down)
                    # If you want north-up, flip Y:
                    y1s = -y1
                    y2s = -y2
                    x1s, x2s = x1, x2

                    min_x = min(min_x, x1s, x2s)
                    min_y = min(min_y, y1s, y2s)
                    max_x = max(max_x, x1s, x2s)
                    max_y = max(max_y, y1s, y2s)

                    line = QGraphicsLineItem(x1s, y1s, x2s, y2s)
                    line.setPen(pen)
                    self.scene.addItem(line)

        padding = 100  # meters padding around shapes
        self.scene.setSceneRect(
            min_x - padding,
            min_y - padding,
            (max_x - min_x) + 2 * padding,
            (max_y - min_y) + 2 * padding,
        )

        self.view.setRenderHint(QPainter.Antialiasing)
        self.view.setDragMode(QGraphicsView.ScrollHandDrag)
        self.view.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)

if __name__ == "__main__":
    app = QApplication(sys.argv)

    gdf = paths()  # Your data in lat/lon (EPSG:4326)
    print("Original CRS:", gdf.crs)

    # Project to UTM Zone 11N (meters, suitable for Calgary area)
    gdf_projected = gdf.to_crs(epsg=32611)
    print("Projected CRS:", gdf_projected.crs)

    window = Plus15Map(gdf_projected)
    window.show()
    sys.exit(app.exec())
