import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QGraphicsView, QGraphicsScene, 
                               QGraphicsLineItem, QWidget, QVBoxLayout, QHBoxLayout, 
                               QPushButton, QSplitter, QLabel, QFrame)
from PySide6.QtGui import QPen, QPainter, QIcon, QFont
from PySide6.QtCore import Qt, QEvent, QSize

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

class PlanningPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        
        header_layout = QHBoxLayout()
        
        title_label = QLabel("Route Planning")
        title_label.setFont(QFont("Arial", 14, QFont.Bold))
        
        close_button = QPushButton("×")
        close_button.setFixedSize(30, 30)
        close_button.setStyleSheet("""
            QPushButton {
                background-color: #ff4444;
                color: white;
                border: none;
                border-radius: 15px;
                font-size: 18px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #cc3333;
            }
        """)
        close_button.clicked.connect(self.close_planning_mode)
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(close_button)
        
        content_frame = QFrame()
        content_frame.setFrameStyle(QFrame.Box)
        content_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        
        content_layout = QVBoxLayout()
        placeholder_label = QLabel("Planning tools will go here...")
        placeholder_label.setAlignment(Qt.AlignCenter)
        placeholder_label.setStyleSheet("color: #6c757d; font-size: 14px;")
        content_layout.addWidget(placeholder_label)
        content_frame.setLayout(content_layout)
        
        layout.addLayout(header_layout)
        layout.addWidget(content_frame)
        layout.addStretch()
        
        self.setLayout(layout)
        self.setStyleSheet("""
            QWidget {
                background-color: white;
                border-top: 2px solid #007bff;
            }
        """)

    def close_planning_mode(self):
        if self.parent_window:
            self.parent_window.toggle_planning_mode()

class Plus15Map(QMainWindow):
    def __init__(self, gdf):
        super().__init__()
        self.setWindowTitle("Calgary +15 Map")
        self.resize(400, 750)
        
        self.planning_mode = False
        self.gdf = gdf
        
        self.init_ui()
        self.setup_map()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        self.main_layout = QVBoxLayout(central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        self.view = ZoomableGraphicsView()
        self.scene = QGraphicsScene()
        self.view.setScene(self.scene)
        
        self.splitter = QSplitter(Qt.Vertical)
        self.splitter.addWidget(self.view)
        
        self.planning_panel = PlanningPanel(self)
        self.splitter.addWidget(self.planning_panel)
        self.planning_panel.hide()
        
        self.splitter.setSizes([600, 200])
        
        self.main_layout.addWidget(self.splitter)
        
        self.create_floating_button()

    def create_floating_button(self):
        self.plus_button = QPushButton("+")
        self.plus_button.setParent(self)
        self.plus_button.setFixedSize(50, 50)
        self.plus_button.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                border-radius: 25px;
                font-size: 24px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
            QPushButton:pressed {
                background-color: #004085;
            }
        """)
        self.plus_button.clicked.connect(self.toggle_planning_mode)
        
        self.position_floating_button()

    def position_floating_button(self):
        margin = 20
        button_x = self.width() - self.plus_button.width() - margin
        button_y = self.height() - self.plus_button.height() - margin
        self.plus_button.move(button_x, button_y)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.position_floating_button()

    def toggle_planning_mode(self):
        self.planning_mode = not self.planning_mode
        
        if self.planning_mode:
            # Show planning panel
            self.planning_panel.show()
            self.plus_button.setText("−")
            self.plus_button.setStyleSheet("""
                QPushButton {
                    background-color: #dc3545;
                    color: white;
                    border: none;
                    border-radius: 25px;
                    font-size: 24px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #c82333;
                }
                QPushButton:pressed {
                    background-color: #bd2130;
                }
            """)
        else:
            self.planning_panel.hide()
            self.plus_button.setText("+")
            self.plus_button.setStyleSheet("""
                QPushButton {
                    background-color: #007bff;
                    color: white;
                    border: none;
                    border-radius: 25px;
                    font-size: 24px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #0056b3;
                }
                QPushButton:pressed {
                    background-color: #004085;
                }
            """)

    def setup_map(self):
        self.tile_layer = TileLayer(self.scene, tiles_root="tiles_cartodb_positron")
        
        self.draw_lines(self.gdf)
        self.update_tiles()

        self.view.setRenderHint(QPainter.Antialiasing)
        self.view.setDragMode(QGraphicsView.ScrollHandDrag)
        self.view.viewport().installEventFilter(self)

    def draw_lines(self, gdf):
        pen = QPen(Qt.red)
        pen.setWidth(3)
        pen.setCapStyle(Qt.RoundCap)

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