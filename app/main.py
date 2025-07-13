import sys
import math
from PySide6.QtWidgets import (QApplication, QMainWindow, QGraphicsView, QGraphicsScene, 
                               QGraphicsLineItem, QGraphicsEllipseItem, QWidget, QVBoxLayout, QHBoxLayout, 
                               QPushButton, QSplitter, QLabel, QFrame, QMessageBox, QCheckBox, QScrollArea,
                               QGraphicsTextItem)
from PySide6.QtGui import QPen, QPainter, QIcon, QFont, QBrush, QColor
from PySide6.QtCore import Qt, QEvent, QSize, QRectF, QTimer, QPointF
from PySide6.QtPositioning import QGeoPositionInfoSource, QGeoPositionInfo

from shapely.geometry import LineString, MultiLineString, Point
from data import paths, businessData
from tile_loader import TileLayer

class BusinessPointItem(QGraphicsEllipseItem):
    """Custom graphics item for business points with hover effects"""
    def __init__(self, x, y, business_info, radius=4):
        super().__init__(x - radius, y - radius, radius * 2, radius * 2)
        self.business_info = business_info
        self.radius = radius
        self.center_x = x
        self.center_y = y
        
        # Default appearance
        self.setPen(QPen(Qt.darkBlue, 1))
        self.setBrush(QBrush(Qt.blue))
        
        # Enable hover events
        self.setAcceptHoverEvents(True)
        
        # Text item for business name (initially hidden)
        self.text_item = None
        
    def hoverEnterEvent(self, event):
        """Show business name and highlight on hover"""
        # Enlarge and change color
        self.setPen(QPen(Qt.darkRed, 2))
        self.setBrush(QBrush(Qt.red))
        
        # Create text item if it doesn't exist
        if not self.text_item:
            self.text_item = QGraphicsTextItem(self.business_info.get('tradename', 'Unknown Business'))
            self.text_item.setFont(QFont("Arial", 8))
            self.text_item.setDefaultTextColor(Qt.black)
            
            # Position text above the point
            text_rect = self.text_item.boundingRect()
            self.text_item.setPos(
                self.center_x - text_rect.width() / 2,
                self.center_y - self.radius - text_rect.height() - 5
            )
            
            # Add background rectangle for better readability
            bg_rect = QGraphicsEllipseItem(
                self.text_item.x() - 5,
                self.text_item.y() - 2,
                text_rect.width() + 10,
                text_rect.height() + 4
            )
            bg_rect.setBrush(QBrush(QColor(255, 255, 255, 200)))
            bg_rect.setPen(QPen(Qt.gray, 1))
            
            self.scene().addItem(bg_rect)
            self.scene().addItem(self.text_item)
            
            # Store reference to background for cleanup
            self.bg_rect = bg_rect
        
        super().hoverEnterEvent(event)
    
    def hoverLeaveEvent(self, event):
        """Hide business name and return to normal appearance"""
        # Return to normal appearance
        self.setPen(QPen(Qt.darkBlue, 1))
        self.setBrush(QBrush(Qt.blue))
        
        # Remove text item
        if self.text_item:
            self.scene().removeItem(self.text_item)
            self.scene().removeItem(self.bg_rect)
            self.text_item = None
            self.bg_rect = None
        
        super().hoverLeaveEvent(event)

class ZoomableGraphicsView(QGraphicsView):
    def __init__(self):
        super().__init__()
        self.scale(1, -1)
        
        self.bounds = QRectF(
            -12700087.099057846,
            6620354.958742279,
            -12684934.17119011 - (-12700087.099057846),
            6635328.924629 - 6620354.958742279
        )
        
        self.min_zoom_level = 1.0
        self.current_zoom = 1.0
        
        self.user_location_item = None
        self.user_accuracy_item = None
        
        # Store business items for toggling visibility
        self.business_items = []

    def wheelEvent(self, event):
        zoom_in_factor = 1.25
        zoom_out_factor = 1 / zoom_in_factor

        old_pos = self.mapToScene(event.position().toPoint())
        
        if event.angleDelta().y() > 0:
            new_zoom = self.current_zoom * zoom_in_factor
            zoom_factor = zoom_in_factor
        else:
            new_zoom = self.current_zoom * zoom_out_factor
            zoom_factor = zoom_out_factor
        
        if new_zoom < self.min_zoom_level:
            return
        
        self.current_zoom = new_zoom
        self.scale(zoom_factor, zoom_factor)

        new_pos = self.mapToScene(event.position().toPoint())
        delta = new_pos - old_pos
        self.translate(delta.x(), delta.y())
        
        self.constrain_to_bounds()

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.last_pan_point = event.pos()

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        if self.dragMode() == QGraphicsView.ScrollHandDrag:
            self.constrain_to_bounds()

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        self.constrain_to_bounds()

    def constrain_to_bounds(self):
        """Constrain the view to stay within the defined bounds"""
        visible_rect = self.mapToScene(self.viewport().rect()).boundingRect()
        
        dx = 0
        dy = 0
        
        if visible_rect.left() < self.bounds.left():
            dx = self.bounds.left() - visible_rect.left()
        elif visible_rect.right() > self.bounds.right():
            dx = self.bounds.right() - visible_rect.right()
        
        if visible_rect.top() < self.bounds.top():
            dy = self.bounds.top() - visible_rect.top()
        elif visible_rect.bottom() > self.bounds.bottom():
            dy = self.bounds.bottom() - visible_rect.bottom()

        if dx != 0 or dy != 0:
            self.translate(dx, dy)

    def set_initial_view(self):
        """Set the initial view to show the full bounds"""
        padding = 100
        padded_bounds = QRectF(
            self.bounds.left() - padding,
            self.bounds.top() - padding,
            self.bounds.width() + 2 * padding,
            self.bounds.height() + 2 * padding
        )

        self.fitInView(padded_bounds, Qt.KeepAspectRatio)
        
        self.min_zoom_level = self.current_zoom = 1.0

    def update_user_location(self, x, y, accuracy=None):
        """Update user location on the map"""
        if self.user_location_item:
            self.scene().removeItem(self.user_location_item)
        if self.user_accuracy_item:
            self.scene().removeItem(self.user_accuracy_item)
        
        if accuracy is not None:
            radius = accuracy
            accuracy_pen = QPen(Qt.blue)
            accuracy_pen.setWidth(1)
            accuracy_pen.setStyle(Qt.DashLine)
            accuracy_brush = QBrush(Qt.blue)
            accuracy_brush.setStyle(Qt.NoBrush)
            
            self.user_accuracy_item = QGraphicsEllipseItem(
                x - radius, y - radius, radius * 2, radius * 2
            )
            self.user_accuracy_item.setPen(accuracy_pen)
            self.user_accuracy_item.setBrush(accuracy_brush)
            self.scene().addItem(self.user_accuracy_item)
        
        location_pen = QPen(Qt.white)
        location_pen.setWidth(2)
        location_brush = QBrush(Qt.blue)
        
        self.user_location_item = QGraphicsEllipseItem(x - 5, y - 5, 10, 10)
        self.user_location_item.setPen(location_pen)
        self.user_location_item.setBrush(location_brush)
        self.scene().addItem(self.user_location_item)

    def lat_lon_to_web_mercator(self, lat, lon):
        """Convert latitude/longitude to Web Mercator (EPSG:3857)"""
        x = lon * 20037508.34 / 180
        y = math.log(math.tan((90 + lat) * math.pi / 360)) / (math.pi / 180)
        y = y * 20037508.34 / 180
        return x, y

    def toggle_business_visibility(self, visible):
        """Toggle visibility of business points"""
        for item in self.business_items:
            item.setVisible(visible)

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
        
        # Add business toggle checkbox
        self.business_checkbox = QCheckBox("Show Business Locations")
        self.business_checkbox.setChecked(True)
        self.business_checkbox.stateChanged.connect(self.toggle_business_points)
        
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
        content_layout.addWidget(self.business_checkbox)
        
        placeholder_label = QLabel("Additional planning tools will go here...")
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

    def toggle_business_points(self, state):
        """Toggle business points visibility from planning panel"""
        self.parent_window.business_visible = (state == Qt.Checked)
        if self.parent_window:
            self.parent_window.view.toggle_business_visibility(state == Qt.Checked)
            # Update the floating button appearance
            self.parent_window.toggle_business_visibility()

    def close_planning_mode(self):
        if self.parent_window:
            self.parent_window.toggle_planning_mode()

class Plus15Map(QMainWindow):
    def __init__(self, gdf, business_df):
        super().__init__()
        self.setWindowTitle("Calgary +15 Map")
        self.resize(400, 750)
        
        self.planning_mode = False
        self.gdf = gdf
        self.business_df = business_df
        
        # Location services
        self.location_source = None
        self.location_enabled = False
        
        self.init_ui()
        self.setup_map()
        self.setup_location_services()

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
        
        self.location_button = QPushButton("📍")
        self.location_button.setParent(self)
        self.location_button.setFixedSize(50, 50)
        self.location_button.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 25px;
                font-size: 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:pressed {
                background-color: #1e7e34;
            }
        """)
        self.location_button.clicked.connect(self.toggle_location_tracking)
        
        # Add business toggle button
        self.business_button = QPushButton("🏢")
        self.business_button.setParent(self)
        self.business_button.setFixedSize(50, 50)
        self.business_visible = True  # Track business visibility state
        self.business_button.setStyleSheet("""
            QPushButton {
                background-color: #6f42c1;
                color: white;
                border: none;
                border-radius: 25px;
                font-size: 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5a2d91;
            }
            QPushButton:pressed {
                background-color: #4c1d7a;
            }
        """)
        self.business_button.clicked.connect(self.toggle_business_visibility)
        
        self.position_floating_buttons()

    def position_floating_buttons(self):
        """Position the floating buttons in the bottom right corner"""
        margin = 20
        button_spacing = 60
        
        plus_x = self.width() - self.plus_button.width() - margin
        plus_y = self.height() - self.plus_button.height() - margin
        self.plus_button.move(plus_x, plus_y)
        
        location_x = self.width() - self.location_button.width() - margin
        location_y = plus_y - button_spacing
        self.location_button.move(location_x, location_y)
        
        business_x = self.width() - self.business_button.width() - margin
        business_y = location_y - button_spacing
        self.business_button.move(business_x, business_y)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.position_floating_buttons()

    def toggle_business_visibility(self):
        """Toggle business points visibility from the floating button"""
        self.business_visible = not self.business_visible
        self.view.toggle_business_visibility(self.business_visible)
        
        # Update button appearance based on state
        if self.business_visible:
            self.business_button.setStyleSheet("""
                QPushButton {
                    background-color: #6f42c1;
                    color: white;
                    border: none;
                    border-radius: 25px;
                    font-size: 20px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #5a2d91;
                }
                QPushButton:pressed {
                    background-color: #4c1d7a;
                }
            """)
        else:
            self.business_button.setStyleSheet("""
                QPushButton {
                    background-color: #6c757d;
                    color: white;
                    border: none;
                    border-radius: 25px;
                    font-size: 20px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #5a6268;
                }
                QPushButton:pressed {
                    background-color: #4e555b;
                }
            """)
        
    def toggle_planning_mode(self):
        self.planning_mode = not self.planning_mode
        
        if self.planning_mode:
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
        self.planning_mode = not self.planning_mode
        
        if self.planning_mode:
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
        
        self.setup_scene_bounds()
        self.draw_lines(self.gdf)
        self.draw_business_points(self.business_df)

        self.view.set_initial_view()
        
        self.update_tiles()

        self.view.setRenderHint(QPainter.Antialiasing)
        self.view.setDragMode(QGraphicsView.ScrollHandDrag)
        self.view.viewport().installEventFilter(self)

    def setup_scene_bounds(self):
        """Set up the scene rectangle to match Calgary bounds"""
        bounds = self.view.bounds
        padding = 500
        
        self.scene.setSceneRect(
            bounds.left() - padding,
            bounds.top() - padding,
            bounds.width() + 2 * padding,
            bounds.height() + 2 * padding
        )
        
        print(f"Scene Rect (EPSG:3857 meters): {self.scene.sceneRect()}")
        print(f"Calgary bounds: Left={bounds.left()}, Right={bounds.right()}, Top={bounds.top()}, Bottom={bounds.bottom()}")

    def draw_lines(self, gdf):
        pen = QPen(Qt.red)
        pen.setWidth(3)
        pen.setCapStyle(Qt.RoundCap)

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

                    line_item = QGraphicsLineItem(x1, y1, x2, y2)
                    line_item.setPen(pen)
                    self.scene.addItem(line_item)

    def draw_business_points(self, business_df):
        """Draw business points on the map"""
        print(f"Drawing {len(business_df)} business points...")
        
        for idx, row in business_df.iterrows():
            try:
                # Extract geometry from the point column
                point_geom = row['point']
                
                if isinstance(point_geom, Point):
                    # Get coordinates
                    lon, lat = point_geom.x, point_geom.y
                    
                    # Convert to Web Mercator
                    x, y = self.view.lat_lon_to_web_mercator(lat, lon)
                    
                    # Create business info dictionary
                    business_info = {
                        'busid': row.get('busid', 'N/A'),
                        'tradename': row.get('tradename', 'Unknown Business'),
                        'homeoccind': row.get('homeoccind', 'N/A'),
                        'jobstatusdesc': row.get('jobstatusdesc', 'N/A'),
                        'lat': lat,
                        'lon': lon
                    }
                    
                    # Create business point item
                    business_item = BusinessPointItem(x, y, business_info)
                    
                    # Add to scene and store reference
                    self.scene.addItem(business_item)
                    self.view.business_items.append(business_item)
                    
            except Exception as e:
                print(f"Error processing business point {idx}: {e}")
                continue
        
        print(f"Successfully added {len(self.view.business_items)} business points to map")

    def update_tiles(self):
        zoom_level = 15
        self.tile_layer.update_tiles(self.scene.sceneRect(), zoom_level)

    def eventFilter(self, obj, event):
        if event.type() in (QEvent.Wheel, QEvent.MouseMove):
            self.update_tiles()
        return super().eventFilter(obj, event)

    def setup_location_services(self):
        """Set up location services"""
        self.location_source = QGeoPositionInfoSource.createDefaultSource(self)
        
        if self.location_source is None:
            print("Location services not available")
            self.location_button.setEnabled(False)
            self.location_button.setStyleSheet("""
                QPushButton {
                    background-color: #6c757d;
                    color: white;
                    border: none;
                    border-radius: 25px;
                    font-size: 20px;
                    font-weight: bold;
                }
            """)
            return
        
        self.location_source.setUpdateInterval(5000)
        self.location_source.positionUpdated.connect(self.on_position_updated)
        self.location_source.errorOccurred.connect(self.on_location_error)
        
        print("Location services initialized")

    def toggle_location_tracking(self):
        """Toggle location tracking on/off"""
        if self.location_source is None:
            QMessageBox.warning(self, "Location Services", 
                              "Location services are not available on this device.")
            return
        
        if not self.location_enabled:
            self.location_source.startUpdates()
            self.location_enabled = True
            self.location_button.setStyleSheet("""
                QPushButton {
                    background-color: #dc3545;
                    color: white;
                    border: none;
                    border-radius: 25px;
                    font-size: 20px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #c82333;
                }
                QPushButton:pressed {
                    background-color: #bd2130;
                }
            """)
            print("Location tracking started")
        else:
            self.location_source.stopUpdates()
            self.location_enabled = False
            
            if self.view.user_location_item:
                self.scene.removeItem(self.view.user_location_item)
                self.view.user_location_item = None
            if self.view.user_accuracy_item:
                self.scene.removeItem(self.view.user_accuracy_item)
                self.view.user_accuracy_item = None
            
            self.location_button.setStyleSheet("""
                QPushButton {
                    background-color: #28a745;
                    color: white;
                    border: none;
                    border-radius: 25px;
                    font-size: 20px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #218838;
                }
                QPushButton:pressed {
                    background-color: #1e7e34;
                }
            """)
            print("Location tracking stopped")

    def on_position_updated(self, position_info):
        """Handle location updates"""
        if position_info.isValid():
            coordinate = position_info.coordinate()
            lat = coordinate.latitude()
            lon = coordinate.longitude()
            
            x, y = self.view.lat_lon_to_web_mercator(lat, lon)
            
            accuracy = None
            if position_info.hasAttribute(QGeoPositionInfo.HorizontalAccuracy):
                accuracy = position_info.attribute(QGeoPositionInfo.HorizontalAccuracy)
            
            self.view.update_user_location(x, y, accuracy)
            
            print(f"Location updated: {lat:.6f}, {lon:.6f} (accuracy: {accuracy}m)")
        else:
            print("Invalid position received")

    def on_location_error(self, error):
        """Handle location errors"""
        error_messages = {
            QGeoPositionInfoSource.AccessError: "Access to location services denied",
            QGeoPositionInfoSource.ClosedError: "Location services connection closed",
            QGeoPositionInfoSource.NoError: "No error",
            QGeoPositionInfoSource.UnknownSourceError: "Unknown location source error"
        }
        
        message = error_messages.get(error, f"Location error: {error}")
        print(f"Location error: {message}")
        
        QMessageBox.warning(self, "Location Error", message)

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Load both datasets
    gdf = paths()
    gdf_projected = gdf.to_crs(epsg=3857)
    
    business_df = businessData()
    
    window = Plus15Map(gdf_projected, business_df)
    window.show()
    sys.exit(app.exec())