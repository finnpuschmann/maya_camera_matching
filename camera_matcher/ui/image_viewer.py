"""
Image viewer widget with zoom and point selection capabilities.
"""

from typing import Optional, Tuple, List, Callable, Dict
import os

try:
    from PySide2.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                                  QScrollArea, QPushButton, QSlider, QSpinBox,
                                  QSizePolicy, QFrame)
    from PySide2.QtCore import Qt, Signal, QPoint, QRect, QSize
    from PySide2.QtGui import QPixmap, QPainter, QPen, QBrush, QColor, QFont, QWheelEvent, QMouseEvent
    PYSIDE_AVAILABLE = True
except ImportError:
    try:
        from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                                      QScrollArea, QPushButton, QSlider, QSpinBox,
                                      QSizePolicy, QFrame)
        from PySide6.QtCore import Qt, Signal, QPoint, QRect, QSize
        from PySide6.QtGui import QPixmap, QPainter, QPen, QBrush, QColor, QFont, QWheelEvent, QMouseEvent
        PYSIDE_AVAILABLE = True
    except ImportError:
        PYSIDE_AVAILABLE = False


if PYSIDE_AVAILABLE:
    class ImageLabel(QLabel):
        """Custom QLabel for image display with mouse interaction."""
        
        point_clicked = Signal(float, float)  # Emits pixel coordinates
        
        def __init__(self, parent=None):
            super().__init__(parent)
            self.setMinimumSize(200, 200)
            self.setStyleSheet("border: 1px solid gray;")
            self.setAlignment(Qt.AlignCenter)
            
            # Image and display properties
            self._original_pixmap: Optional[QPixmap] = None
            self._scaled_pixmap: Optional[QPixmap] = None
            self._zoom_factor: float = 1.0
            
            # Point management
            self._points: Dict[int, Tuple[float, float]] = {}  # pair_id -> (x, y)
            self._projected_points: Dict[int, Tuple[float, float]] = {}  # pair_id -> (x, y)
            self._point_colors: Dict[int, QColor] = {}
            self._point_radius: int = 5
            
            # Interaction state
            self._adding_point: bool = False
        
        def set_image(self, image_path: str) -> bool:
            """
            Load and display an image.
            
            Args:
                image_path: Path to the image file
                
            Returns:
                True if image was loaded successfully, False otherwise
            """
            if not os.path.exists(image_path):
                return False
            
            self._original_pixmap = QPixmap(image_path)
            if self._original_pixmap.isNull():
                return False
            
            self._update_display()
            return True
        
        def get_image_size(self) -> Tuple[int, int]:
            """
            Get the original image size.
            
            Returns:
                Tuple of (width, height) or (0, 0) if no image
            """
            if self._original_pixmap:
                return self._original_pixmap.width(), self._original_pixmap.height()
            return (0, 0)
        
        def set_zoom_factor(self, zoom_factor: float) -> None:
            """
            Set the zoom factor for the image.
            
            Args:
                zoom_factor: Zoom factor (1.0 = original size)
            """
            self._zoom_factor = max(0.1, min(10.0, zoom_factor))
            self._update_display()
        
        def get_zoom_factor(self) -> float:
            """Get the current zoom factor."""
            return self._zoom_factor
        
        def add_point(self, pair_id: int, pixel_x: float, pixel_y: float, 
                     color: QColor = QColor(255, 0, 0)) -> None:
            """
            Add a point to be displayed on the image.
            
            Args:
                pair_id: Unique identifier for the point
                pixel_x: X pixel coordinate
                pixel_y: Y pixel coordinate
                color: Color to draw the point
            """
            self._points[pair_id] = (pixel_x, pixel_y)
            self._point_colors[pair_id] = color
            self._update_display()
        
        def add_projected_point(self, pair_id: int, pixel_x: float, pixel_y: float,
                               color: QColor = QColor(0, 255, 0)) -> None:
            """
            Add a projected point to be displayed on the image.
            
            Args:
                pair_id: Unique identifier for the point
                pixel_x: X pixel coordinate  
                pixel_y: Y pixel coordinate
                color: Color to draw the projected point
            """
            self._projected_points[pair_id] = (pixel_x, pixel_y)
            self._update_display()
        
        def remove_point(self, pair_id: int) -> None:
            """
            Remove a point from display.
            
            Args:
                pair_id: ID of the point to remove
            """
            self._points.pop(pair_id, None)
            self._projected_points.pop(pair_id, None)
            self._point_colors.pop(pair_id, None)
            self._update_display()
        
        def clear_points(self) -> None:
            """Clear all points."""
            self._points.clear()
            self._projected_points.clear()
            self._point_colors.clear()
            self._update_display()
        
        def clear_projected_points(self) -> None:
            """Clear only projected points."""
            self._projected_points.clear()
            self._update_display()
        
        def set_adding_point_mode(self, enabled: bool) -> None:
            """
            Enable or disable point adding mode.
            
            Args:
                enabled: Whether to enable point adding mode
            """
            self._adding_point = enabled
            if enabled:
                self.setCursor(Qt.CrossCursor)
            else:
                self.setCursor(Qt.ArrowCursor)
        
        def _update_display(self) -> None:
            """Update the displayed image with current zoom and points."""
            if not self._original_pixmap:
                return
            
            # Scale the image
            scaled_size = self._original_pixmap.size() * self._zoom_factor
            self._scaled_pixmap = self._original_pixmap.scaled(
                scaled_size, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            
            # Draw points on the scaled image
            if self._points or self._projected_points:
                painter = QPainter(self._scaled_pixmap)
                painter.setRenderHint(QPainter.Antialiasing)
                
                # Draw actual points (red by default)
                for pair_id, (x, y) in self._points.items():
                    color = self._point_colors.get(pair_id, QColor(255, 0, 0))
                    self._draw_point(painter, x, y, color, filled=True)
                
                # Draw projected points (green, hollow)
                for pair_id, (x, y) in self._projected_points.items():
                    self._draw_point(painter, x, y, QColor(0, 255, 0), filled=False)
                    
                    # Draw line connecting actual and projected points if both exist
                    if pair_id in self._points:
                        actual_x, actual_y = self._points[pair_id]
                        painter.setPen(QPen(QColor(255, 255, 0), 1, Qt.DashLine))
                        painter.drawLine(
                            QPoint(int(actual_x * self._zoom_factor), int(actual_y * self._zoom_factor)),
                            QPoint(int(x * self._zoom_factor), int(y * self._zoom_factor))
                        )
                
                painter.end()
            
            # Set the pixmap
            self.setPixmap(self._scaled_pixmap)
            self.resize(self._scaled_pixmap.size())
        
        def _draw_point(self, painter: QPainter, x: float, y: float, 
                       color: QColor, filled: bool = True) -> None:
            """
            Draw a point on the painter.
            
            Args:
                painter: QPainter object
                x: X pixel coordinate
                y: Y pixel coordinate
                color: Color to draw the point
                filled: Whether to fill the point or draw outline only
            """
            # Scale coordinates
            scaled_x = int(x * self._zoom_factor)
            scaled_y = int(y * self._zoom_factor)
            scaled_radius = max(3, int(self._point_radius * self._zoom_factor))
            
            painter.setPen(QPen(color, 2))
            
            if filled:
                painter.setBrush(QBrush(color))
            else:
                painter.setBrush(QBrush(Qt.NoBrush))
            
            painter.drawEllipse(scaled_x - scaled_radius, scaled_y - scaled_radius,
                              scaled_radius * 2, scaled_radius * 2)
            
            # Draw cross in the center
            painter.setPen(QPen(QColor(255, 255, 255) if filled else color, 1))
            painter.drawLine(scaled_x - scaled_radius//2, scaled_y,
                           scaled_x + scaled_radius//2, scaled_y)
            painter.drawLine(scaled_x, scaled_y - scaled_radius//2,
                           scaled_x, scaled_y + scaled_radius//2)
        
        def mousePressEvent(self, event: QMouseEvent) -> None:
            """Handle mouse press events."""
            if event.button() == Qt.LeftButton and self._adding_point:
                if self._original_pixmap and self._zoom_factor > 0:
                    # Convert widget coordinates to image coordinates
                    widget_pos = event.pos()
                    image_x = widget_pos.x() / self._zoom_factor
                    image_y = widget_pos.y() / self._zoom_factor
                    
                    # Clamp to image bounds
                    img_width, img_height = self.get_image_size()
                    image_x = max(0, min(img_width - 1, image_x))
                    image_y = max(0, min(img_height - 1, image_y))
                    
                    self.point_clicked.emit(image_x, image_y)
            
            super().mousePressEvent(event)
        
        def wheelEvent(self, event: QWheelEvent) -> None:
            """Handle mouse wheel events for zooming."""
            if self._original_pixmap:
                # Calculate zoom delta
                delta = event.angleDelta().y()
                zoom_in = delta > 0
                
                # Calculate new zoom factor
                zoom_step = 1.2
                if zoom_in:
                    new_zoom = self._zoom_factor * zoom_step
                else:
                    new_zoom = self._zoom_factor / zoom_step
                
                self.set_zoom_factor(new_zoom)
            
            super().wheelEvent(event)


    class ImageViewer(QWidget):
        """
        Image viewer widget with zoom controls and point management.
        """
        
        point_added = Signal(float, float)  # Emits when a point is added
        
        def __init__(self, parent=None):
            super().__init__(parent)
            self._setup_ui()
            self._connect_signals()
            
            # State
            self._image_path: Optional[str] = None
            self._adding_point: bool = False
        
        def _setup_ui(self) -> None:
            """Set up the user interface."""
            layout = QVBoxLayout(self)
            
            # Controls frame
            controls_frame = QFrame()
            controls_layout = QHBoxLayout(controls_frame)
            
            # Zoom controls
            zoom_label = QLabel("Zoom:")
            self.zoom_slider = QSlider(Qt.Horizontal)
            self.zoom_slider.setRange(10, 1000)  # 10% to 1000%
            self.zoom_slider.setValue(100)  # 100%
            self.zoom_slider.setMaximumWidth(200)
            
            self.zoom_spinbox = QSpinBox()
            self.zoom_spinbox.setRange(10, 1000)
            self.zoom_spinbox.setValue(100)
            self.zoom_spinbox.setSuffix("%")
            self.zoom_spinbox.setMaximumWidth(80)
            
            # Zoom buttons
            self.zoom_fit_btn = QPushButton("Fit")
            self.zoom_100_btn = QPushButton("100%")
            
            # Point controls
            self.add_point_btn = QPushButton("Add Point")
            self.add_point_btn.setCheckable(True)
            self.clear_points_btn = QPushButton("Clear Points")
            
            # Add controls to layout
            controls_layout.addWidget(zoom_label)
            controls_layout.addWidget(self.zoom_slider)
            controls_layout.addWidget(self.zoom_spinbox)
            controls_layout.addWidget(self.zoom_fit_btn)
            controls_layout.addWidget(self.zoom_100_btn)
            controls_layout.addStretch()
            controls_layout.addWidget(self.add_point_btn)
            controls_layout.addWidget(self.clear_points_btn)
            
            layout.addWidget(controls_frame)
            
            # Image display area
            self.scroll_area = QScrollArea()
            self.scroll_area.setWidgetResizable(True)
            self.scroll_area.setAlignment(Qt.AlignCenter)
            
            self.image_label = ImageLabel()
            self.scroll_area.setWidget(self.image_label)
            
            layout.addWidget(self.scroll_area)
        
        def _connect_signals(self) -> None:
            """Connect widget signals."""
            self.zoom_slider.valueChanged.connect(self._on_zoom_slider_changed)
            self.zoom_spinbox.valueChanged.connect(self._on_zoom_spinbox_changed)
            self.zoom_fit_btn.clicked.connect(self._on_zoom_fit)
            self.zoom_100_btn.clicked.connect(self._on_zoom_100)
            self.add_point_btn.toggled.connect(self._on_add_point_toggled)
            self.clear_points_btn.clicked.connect(self._on_clear_points)
            self.image_label.point_clicked.connect(self._on_point_clicked)
        
        def load_image(self, image_path: str) -> bool:
            """
            Load an image from file.
            
            Args:
                image_path: Path to the image file
                
            Returns:
                True if image was loaded successfully, False otherwise
            """
            if self.image_label.set_image(image_path):
                self._image_path = image_path
                self._on_zoom_fit()  # Fit to window by default
                return True
            return False
        
        def get_image_size(self) -> Tuple[int, int]:
            """
            Get the size of the loaded image.
            
            Returns:
                Tuple of (width, height) or (0, 0) if no image
            """
            return self.image_label.get_image_size()
        
        def add_point(self, pair_id: int, pixel_x: float, pixel_y: float,
                     color: QColor = QColor(255, 0, 0)) -> None:
            """
            Add a point to be displayed on the image.
            
            Args:
                pair_id: Unique identifier for the point
                pixel_x: X pixel coordinate
                pixel_y: Y pixel coordinate
                color: Color to draw the point
            """
            self.image_label.add_point(pair_id, pixel_x, pixel_y, color)
        
        def add_projected_point(self, pair_id: int, pixel_x: float, pixel_y: float) -> None:
            """
            Add a projected point to be displayed on the image.
            
            Args:
                pair_id: Unique identifier for the point
                pixel_x: X pixel coordinate
                pixel_y: Y pixel coordinate
            """
            self.image_label.add_projected_point(pair_id, pixel_x, pixel_y)
        
        def remove_point(self, pair_id: int) -> None:
            """
            Remove a point from display.
            
            Args:
                pair_id: ID of the point to remove
            """
            self.image_label.remove_point(pair_id)
        
        def clear_points(self) -> None:
            """Clear all points."""
            self.image_label.clear_points()
        
        def clear_projected_points(self) -> None:
            """Clear only projected points."""
            self.image_label.clear_projected_points()
        
        def _on_zoom_slider_changed(self, value: int) -> None:
            """Handle zoom slider changes."""
            self.zoom_spinbox.blockSignals(True)
            self.zoom_spinbox.setValue(value)
            self.zoom_spinbox.blockSignals(False)
            
            zoom_factor = value / 100.0
            self.image_label.set_zoom_factor(zoom_factor)
        
        def _on_zoom_spinbox_changed(self, value: int) -> None:
            """Handle zoom spinbox changes."""
            self.zoom_slider.blockSignals(True)
            self.zoom_slider.setValue(value)
            self.zoom_slider.blockSignals(False)
            
            zoom_factor = value / 100.0
            self.image_label.set_zoom_factor(zoom_factor)
        
        def _on_zoom_fit(self) -> None:
            """Fit image to window."""
            if self._image_path:
                img_width, img_height = self.image_label.get_image_size()
                if img_width > 0 and img_height > 0:
                    # Calculate zoom to fit
                    scroll_size = self.scroll_area.size()
                    zoom_x = (scroll_size.width() - 20) / img_width
                    zoom_y = (scroll_size.height() - 20) / img_height
                    zoom_factor = min(zoom_x, zoom_y, 1.0)  # Don't zoom in beyond 100%
                    
                    zoom_percent = int(zoom_factor * 100)
                    self.zoom_slider.setValue(zoom_percent)
        
        def _on_zoom_100(self) -> None:
            """Set zoom to 100%."""
            self.zoom_slider.setValue(100)
        
        def _on_add_point_toggled(self, checked: bool) -> None:
            """Handle add point button toggle."""
            self._adding_point = checked
            self.image_label.set_adding_point_mode(checked)
            
            if checked:
                self.add_point_btn.setText("Adding Point...")
                self.add_point_btn.setStyleSheet("background-color: #4CAF50;")
            else:
                self.add_point_btn.setText("Add Point")
                self.add_point_btn.setStyleSheet("")
        
        def _on_clear_points(self) -> None:
            """Handle clear points button."""
            self.clear_points()
        
        def _on_point_clicked(self, x: float, y: float) -> None:
            """Handle point clicked in image."""
            if self._adding_point:
                # Turn off adding mode
                self.add_point_btn.setChecked(False)
                # Emit signal
                self.point_added.emit(x, y)

else:
    # Fallback if PySide is not available
    class ImageViewer(QWidget if PYSIDE_AVAILABLE else object):
        """Dummy ImageViewer when PySide is not available."""
        
        def __init__(self, parent=None):
            if PYSIDE_AVAILABLE:
                super().__init__(parent)
            self._show_error()
        
        def _show_error(self):
            print("Error: PySide2 or PySide6 is required for the Image Viewer but is not available.")
        
        def load_image(self, image_path: str) -> bool:
            return False
        
        def get_image_size(self) -> Tuple[int, int]:
            return (0, 0)
        
        def add_point(self, pair_id: int, pixel_x: float, pixel_y: float, color=None) -> None:
            pass
        
        def remove_point(self, pair_id: int) -> None:
            pass
        
        def clear_points(self) -> None:
            pass