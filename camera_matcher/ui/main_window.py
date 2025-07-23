"""
Main window for the Camera Matcher plugin.
"""

from typing import Optional, List, Dict, Any
import os
import traceback

try:
    from PySide2.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                                  QSplitter, QGroupBox, QLabel, QPushButton, 
                                  QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox,
                                  QTableWidget, QTableWidgetItem, QHeaderView,
                                  QFileDialog, QMessageBox, QProgressBar,
                                  QTextEdit, QTabWidget, QFrame, QFormLayout,
                                  QSlider, QApplication)
    from PySide2.QtCore import Qt, QTimer, Signal, QThread, pyqtSignal
    from PySide2.QtGui import QColor, QFont
    PYSIDE_AVAILABLE = True
except ImportError:
    try:
        from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                                      QSplitter, QGroupBox, QLabel, QPushButton, 
                                      QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox,
                                      QTableWidget, QTableWidgetItem, QHeaderView,
                                      QFileDialog, QMessageBox, QProgressBar,
                                      QTextEdit, QTabWidget, QFrame, QFormLayout,
                                      QSlider, QApplication)
        from PySide6.QtCore import Qt, QTimer, Signal, QThread
        from PySide6.QtGui import QColor, QFont
        # Handle different signal naming in PySide6
        try:
            from PySide6.QtCore import pyqtSignal
        except ImportError:
            pyqtSignal = Signal
        PYSIDE_AVAILABLE = True
    except ImportError:
        PYSIDE_AVAILABLE = False

import maya.cmds as cmds
from ..core.camera_matcher import CameraMatcher
from ..core.camera_parameters import ParameterConstraints
from .image_viewer import ImageViewer


if PYSIDE_AVAILABLE:
    
    class OptimizationWorker(QThread):
        """Worker thread for camera optimization."""
        
        progress_updated = pyqtSignal(int, float)
        optimization_finished = pyqtSignal(bool, float, int)
        
        def __init__(self, camera_matcher: CameraMatcher, method: str = 'lm'):
            super().__init__()
            self.camera_matcher = camera_matcher
            self.method = method
        
        def run(self):
            """Run the optimization."""
            try:
                # Set up progress callback
                if self.camera_matcher.optimizer:
                    self.camera_matcher.optimizer.set_progress_callback(self._progress_callback)
                
                # Run optimization
                success, final_error, iterations = self.camera_matcher.optimize_camera(self.method)
                self.optimization_finished.emit(success, final_error, iterations)
                
            except Exception as e:
                print(f"Optimization error: {str(e)}")
                self.optimization_finished.emit(False, float('inf'), 0)
        
        def _progress_callback(self, iteration: int, error: float):
            """Progress callback for optimization."""
            self.progress_updated.emit(iteration, error)


    class CameraMatcherUI(QMainWindow):
        """
        Main window for the Camera Matcher plugin.
        """
        
        def __init__(self, parent=None):
            super().__init__(parent)
            
            # Core components
            self.camera_matcher = CameraMatcher()
            self.optimization_worker: Optional[OptimizationWorker] = None
            
            # UI setup
            self.setWindowTitle("Camera Matcher")
            self.setMinimumSize(1200, 800)
            self.resize(1400, 900)
            
            self._setup_ui()
            self._connect_signals()
            self._update_ui_state()
            
            # Timers for updates
            self.update_timer = QTimer()
            self.update_timer.timeout.connect(self._update_camera_info)
            self.update_timer.start(1000)  # Update every second
        
        def _setup_ui(self) -> None:
            """Set up the user interface."""
            central_widget = QWidget()
            self.setCentralWidget(central_widget)
            
            # Main layout
            main_layout = QHBoxLayout(central_widget)
            
            # Create splitter
            splitter = QSplitter(Qt.Horizontal)
            main_layout.addWidget(splitter)
            
            # Left panel (controls)
            left_panel = self._create_left_panel()
            splitter.addWidget(left_panel)
            
            # Right panel (image viewer)
            right_panel = self._create_right_panel()
            splitter.addWidget(right_panel)
            
            # Set splitter proportions
            splitter.setSizes([400, 800])
        
        def _create_left_panel(self) -> QWidget:
            """Create the left control panel."""
            panel = QWidget()
            layout = QVBoxLayout(panel)
            
            # Image controls
            image_group = QGroupBox("Image")
            image_layout = QVBoxLayout(image_group)
            
            # Load image button
            self.load_image_btn = QPushButton("Load Image")
            image_layout.addWidget(self.load_image_btn)
            
            # Image info
            self.image_info_label = QLabel("No image loaded")
            self.image_info_label.setWordWrap(True)
            image_layout.addWidget(self.image_info_label)
            
            layout.addWidget(image_group)
            
            # Camera controls
            camera_group = QGroupBox("Camera")
            camera_layout = QVBoxLayout(camera_group)
            
            # Camera selection
            camera_select_layout = QHBoxLayout()
            camera_select_layout.addWidget(QLabel("Camera:"))
            self.camera_combo = QComboBox()
            self.camera_combo.setEditable(True)
            camera_select_layout.addWidget(self.camera_combo)
            self.refresh_cameras_btn = QPushButton("Refresh")
            self.refresh_cameras_btn.setMaximumWidth(80)
            camera_select_layout.addWidget(self.refresh_cameras_btn)
            camera_layout.addLayout(camera_select_layout)
            
            # Set camera button
            self.set_camera_btn = QPushButton("Set Camera")
            camera_layout.addWidget(self.set_camera_btn)
            
            # Camera info
            self.camera_info_label = QLabel("No camera set")
            self.camera_info_label.setWordWrap(True)
            camera_layout.addWidget(self.camera_info_label)
            
            layout.addWidget(camera_group)
            
            # Parameter controls
            param_group = QGroupBox("Camera Parameters")
            param_layout = QVBoxLayout(param_group)
            
            # Create tabs for parameter categories
            param_tabs = QTabWidget()
            
            # Transform tab
            transform_tab = self._create_transform_tab()
            param_tabs.addTab(transform_tab, "Transform")
            
            # Camera tab
            camera_tab = self._create_camera_tab()
            param_tabs.addTab(camera_tab, "Camera")
            
            param_layout.addWidget(param_tabs)
            layout.addWidget(param_group)
            
            # Locator pairs
            pairs_group = QGroupBox("Locator Pairs")
            pairs_layout = QVBoxLayout(pairs_group)
            
            # Pairs table
            self.pairs_table = QTableWidget()
            self.pairs_table.setColumnCount(4)
            self.pairs_table.setHorizontalHeaderLabels(["ID", "Pixel X", "Pixel Y", "Error"])
            self.pairs_table.horizontalHeader().setStretchLastSection(True)
            pairs_layout.addWidget(self.pairs_table)
            
            # Pairs controls
            pairs_controls_layout = QHBoxLayout()
            self.delete_pair_btn = QPushButton("Delete Selected")
            self.clear_pairs_btn = QPushButton("Clear All")
            pairs_controls_layout.addWidget(self.delete_pair_btn)
            pairs_controls_layout.addWidget(self.clear_pairs_btn)
            pairs_layout.addLayout(pairs_controls_layout)
            
            layout.addWidget(pairs_group)
            
            # Optimization controls
            opt_group = QGroupBox("Optimization")
            opt_layout = QVBoxLayout(opt_group)
            
            # Method selection
            method_layout = QHBoxLayout()
            method_layout.addWidget(QLabel("Method:"))
            self.method_combo = QComboBox()
            self.method_combo.addItems(["lm", "trf", "dogbox", "L-BFGS-B"])
            method_layout.addWidget(self.method_combo)
            opt_layout.addLayout(method_layout)
            
            # Optimize button
            self.optimize_btn = QPushButton("Optimize Camera")
            opt_layout.addWidget(self.optimize_btn)
            
            # Progress bar
            self.progress_bar = QProgressBar()
            self.progress_bar.setVisible(False)
            opt_layout.addWidget(self.progress_bar)
            
            # Error display
            self.error_label = QLabel("RMS Error: N/A")
            opt_layout.addWidget(self.error_label)
            
            layout.addWidget(opt_group)
            
            # File operations
            file_group = QGroupBox("File Operations")
            file_layout = QVBoxLayout(file_group)
            
            self.save_btn = QPushButton("Save Session")
            self.load_btn = QPushButton("Load Session")
            file_layout.addWidget(self.save_btn)
            file_layout.addWidget(self.load_btn)
            
            layout.addWidget(file_group)
            
            layout.addStretch()
            
            return panel
        
        def _create_transform_tab(self) -> QWidget:
            """Create the transform parameters tab."""
            tab = QWidget()
            layout = QFormLayout(tab)
            
            self.transform_controls = {}
            
            # Translation parameters
            for axis in ['x', 'y', 'z']:
                param_name = f'translate_{axis}'
                controls = self._create_parameter_controls(param_name, f"Translate {axis.upper()}")
                layout.addRow(f"Translate {axis.upper()}:", controls)
                self.transform_controls[param_name] = controls
            
            # Rotation parameters  
            for axis in ['x', 'y', 'z']:
                param_name = f'rotate_{axis}'
                controls = self._create_parameter_controls(param_name, f"Rotate {axis.upper()}")
                layout.addRow(f"Rotate {axis.upper()}:", controls)
                self.transform_controls[param_name] = controls
            
            return tab
        
        def _create_camera_tab(self) -> QWidget:
            """Create the camera parameters tab."""
            tab = QWidget()
            layout = QFormLayout(tab)
            
            self.camera_controls = {}
            
            # Focal length
            controls = self._create_parameter_controls('focal_length', "Focal Length")
            layout.addRow("Focal Length:", controls)
            self.camera_controls['focal_length'] = controls
            
            # Film offset
            for axis in ['x', 'y']:
                param_name = f'film_offset_{axis}'
                controls = self._create_parameter_controls(param_name, f"Film Offset {axis.upper()}")
                layout.addRow(f"Film Offset {axis.upper()}:", controls)
                self.camera_controls[param_name] = controls
            
            return tab
        
        def _create_parameter_controls(self, param_name: str, label: str) -> QWidget:
            """Create controls for a parameter."""
            widget = QWidget()
            layout = QHBoxLayout(widget)
            layout.setContentsMargins(0, 0, 0, 0)
            
            # Lock checkbox
            lock_cb = QCheckBox()
            lock_cb.setToolTip(f"Lock {label} for optimization")
            layout.addWidget(lock_cb)
            
            # Value spinbox
            value_spin = QDoubleSpinBox()
            value_spin.setRange(-999999, 999999)
            value_spin.setDecimals(3)
            value_spin.setToolTip(f"Current {label} value")
            layout.addWidget(value_spin)
            
            # Min value spinbox
            min_spin = QDoubleSpinBox()
            min_spin.setRange(-999999, 999999)
            min_spin.setDecimals(3)
            min_spin.setValue(-1000)
            min_spin.setToolTip(f"Minimum {label} value")
            layout.addWidget(min_spin)
            
            # Max value spinbox
            max_spin = QDoubleSpinBox()
            max_spin.setRange(-999999, 999999)
            max_spin.setDecimals(3)
            max_spin.setValue(1000)
            max_spin.setToolTip(f"Maximum {label} value")
            layout.addWidget(max_spin)
            
            # Store references
            controls = {
                'lock': lock_cb,
                'value': value_spin,
                'min': min_spin,
                'max': max_spin,
                'param_name': param_name
            }
            
            # Connect signals
            lock_cb.toggled.connect(lambda checked, p=param_name: self._on_parameter_lock_changed(p, checked))
            value_spin.valueChanged.connect(lambda value, p=param_name: self._on_parameter_value_changed(p, value))
            min_spin.valueChanged.connect(lambda value, p=param_name: self._on_parameter_min_changed(p, value))
            max_spin.valueChanged.connect(lambda value, p=param_name: self._on_parameter_max_changed(p, value))
            
            return widget
        
        def _create_right_panel(self) -> QWidget:
            """Create the right panel with image viewer."""
            self.image_viewer = ImageViewer()
            return self.image_viewer
        
        def _connect_signals(self) -> None:
            """Connect widget signals."""
            # Image controls
            self.load_image_btn.clicked.connect(self._on_load_image)
            
            # Camera controls
            self.refresh_cameras_btn.clicked.connect(self._refresh_camera_list)
            self.set_camera_btn.clicked.connect(self._on_set_camera)
            
            # Pairs controls
            self.delete_pair_btn.clicked.connect(self._on_delete_pair)
            self.clear_pairs_btn.clicked.connect(self._on_clear_pairs)
            
            # Optimization
            self.optimize_btn.clicked.connect(self._on_optimize)
            
            # File operations
            self.save_btn.clicked.connect(self._on_save_session)
            self.load_btn.clicked.connect(self._on_load_session)
            
            # Image viewer
            self.image_viewer.point_added.connect(self._on_point_added)
            
            # Refresh camera list initially
            self._refresh_camera_list()
        
        def _refresh_camera_list(self) -> None:
            """Refresh the camera list."""
            self.camera_combo.clear()
            
            # Get all cameras in scene
            cameras = cmds.ls(type='camera')
            camera_transforms = []
            
            for camera in cameras:
                # Get the transform node
                transforms = cmds.listRelatives(camera, parent=True, type='transform')
                if transforms:
                    camera_transforms.extend(transforms)
            
            # Remove duplicates and add to combo
            unique_cameras = list(set(camera_transforms))
            self.camera_combo.addItems(unique_cameras)
        
        def _update_ui_state(self) -> None:
            """Update UI state based on current setup."""
            has_image = self.camera_matcher.image_path is not None
            has_camera = self.camera_matcher.camera_params is not None
            has_pairs = self.camera_matcher.get_pair_count() > 0
            
            # Enable/disable controls
            self.optimize_btn.setEnabled(has_image and has_camera and has_pairs)
            self.delete_pair_btn.setEnabled(has_pairs)
            self.clear_pairs_btn.setEnabled(has_pairs)
            
            # Update info labels
            if has_image:
                self.image_info_label.setText(
                    f"Image: {os.path.basename(self.camera_matcher.image_path)}\n"
                    f"Size: {self.camera_matcher.image_width}x{self.camera_matcher.image_height}"
                )
            else:
                self.image_info_label.setText("No image loaded")
            
            if has_camera:
                self.camera_info_label.setText(
                    f"Camera: {self.camera_matcher.camera_params.camera_name}\n"
                    f"Valid pairs: {self.camera_matcher.get_valid_pair_count()}"
                )
            else:
                self.camera_info_label.setText("No camera set")
            
            # Update parameter controls
            self._update_parameter_controls()
            
            # Update pairs table
            self._update_pairs_table()
            
            # Update error display
            error = self.camera_matcher.calculate_current_error()
            if error == float('inf'):
                self.error_label.setText("RMS Error: N/A")
            else:
                self.error_label.setText(f"RMS Error: {error:.3f} px")
        
        def _update_parameter_controls(self) -> None:
            """Update parameter controls with current values."""
            if not self.camera_matcher.camera_params:
                return
            
            # Block signals during update
            all_controls = {}
            all_controls.update(self.transform_controls)
            all_controls.update(self.camera_controls)
            
            for param_name, controls in all_controls.items():
                # Block signals
                for control in controls.values():
                    if hasattr(control, 'blockSignals'):
                        control.blockSignals(True)
                
                try:
                    # Update values
                    value = self.camera_matcher.camera_params.get_parameter_value(param_name)
                    controls['value'].setValue(value)
                    
                    # Update constraints
                    constraints = self.camera_matcher.camera_params.get_constraints(param_name)
                    controls['lock'].setChecked(constraints.is_locked)
                    
                    if constraints.min_value is not None:
                        controls['min'].setValue(constraints.min_value)
                    if constraints.max_value is not None:
                        controls['max'].setValue(constraints.max_value)
                        
                except Exception:
                    pass
                
                # Unblock signals
                for control in controls.values():
                    if hasattr(control, 'blockSignals'):
                        control.blockSignals(False)
        
        def _update_pairs_table(self) -> None:
            """Update the pairs table."""
            pairs = self.camera_matcher.locator_pairs
            self.pairs_table.setRowCount(len(pairs))
            
            # Get individual errors
            errors = {}
            if self.camera_matcher.optimizer:
                error_list = self.camera_matcher.get_individual_errors()
                errors = {pair_id: error for pair_id, error in error_list}
            
            for row, pair in enumerate(pairs):
                # ID
                self.pairs_table.setItem(row, 0, QTableWidgetItem(str(pair.pair_id)))
                
                # Pixel coordinates
                self.pairs_table.setItem(row, 1, QTableWidgetItem(f"{pair.pixel_coords[0]:.1f}"))
                self.pairs_table.setItem(row, 2, QTableWidgetItem(f"{pair.pixel_coords[1]:.1f}"))
                
                # Error
                error = errors.get(pair.pair_id, float('inf'))
                if error == float('inf'):
                    error_text = "N/A"
                else:
                    error_text = f"{error:.2f}"
                self.pairs_table.setItem(row, 3, QTableWidgetItem(error_text))
        
        def _update_camera_info(self) -> None:
            """Update camera info periodically."""
            if self.camera_matcher.camera_params:
                try:
                    # Update parameter values from Maya
                    self.camera_matcher.camera_params._update_from_maya()
                    self._update_parameter_controls()
                except Exception:
                    pass
        
        def _on_load_image(self) -> None:
            """Handle load image button."""
            file_dialog = QFileDialog()
            image_path, _ = file_dialog.getOpenFileName(
                self, "Load Image", "", 
                "Image Files (*.png *.jpg *.jpeg *.tiff *.tga *.exr *.bmp)"
            )
            
            if image_path:
                try:
                    # Load image in viewer
                    if self.image_viewer.load_image(image_path):
                        # Get image size
                        width, height = self.image_viewer.get_image_size()
                        
                        # Set in camera matcher
                        self.camera_matcher.set_image(image_path, width, height)
                        
                        # Update UI
                        self._update_ui_state()
                        self._update_image_points()
                        
                    else:
                        QMessageBox.warning(self, "Error", "Failed to load image")
                        
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to load image: {str(e)}")
        
        def _on_set_camera(self) -> None:
            """Handle set camera button."""
            camera_name = self.camera_combo.currentText()
            if not camera_name:
                QMessageBox.warning(self, "Error", "Please select a camera")
                return
            
            try:
                self.camera_matcher.set_camera(camera_name)
                self._update_ui_state()
                self._update_image_points()
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to set camera: {str(e)}")
        
        def _on_point_added(self, x: float, y: float) -> None:
            """Handle point added in image viewer."""
            try:
                # Create locator pair
                pair = self.camera_matcher.create_locator_pair(x, y)
                
                # Add to image viewer
                self.image_viewer.add_point(pair.pair_id, x, y)
                
                # Update UI
                self._update_ui_state()
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to create locator pair: {str(e)}")
        
        def _on_delete_pair(self) -> None:
            """Handle delete pair button."""
            current_row = self.pairs_table.currentRow()
            if current_row >= 0:
                # Get pair ID
                pair_id_item = self.pairs_table.item(current_row, 0)
                if pair_id_item:
                    pair_id = int(pair_id_item.text())
                    
                    # Remove pair
                    if self.camera_matcher.remove_locator_pair(pair_id):
                        self.image_viewer.remove_point(pair_id)
                        self._update_ui_state()
        
        def _on_clear_pairs(self) -> None:
            """Handle clear pairs button."""
            reply = QMessageBox.question(
                self, "Clear All Pairs", 
                "Are you sure you want to clear all locator pairs?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.camera_matcher.clear_all_pairs()
                self.image_viewer.clear_points()
                self._update_ui_state()
        
        def _on_optimize(self) -> None:
            """Handle optimize button."""
            if self.optimization_worker and self.optimization_worker.isRunning():
                return
            
            method = self.method_combo.currentText()
            
            # Validate setup
            try:
                if not self.camera_matcher.optimizer:
                    raise RuntimeError("Optimizer not initialized")
                
                is_valid, error_msg = self.camera_matcher.optimizer.validate_setup()
                if not is_valid:
                    QMessageBox.warning(self, "Optimization Error", error_msg)
                    return
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Optimization setup failed: {str(e)}")
                return
            
            # Start optimization in worker thread
            self.optimization_worker = OptimizationWorker(self.camera_matcher, method)
            self.optimization_worker.progress_updated.connect(self._on_optimization_progress)
            self.optimization_worker.optimization_finished.connect(self._on_optimization_finished)
            
            # Update UI for optimization
            self.optimize_btn.setEnabled(False)
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 100)
            
            self.optimization_worker.start()
        
        def _on_optimization_progress(self, iteration: int, error: float) -> None:
            """Handle optimization progress."""
            # Update progress bar (roughly)
            max_iterations = 1000  # Rough estimate
            progress = min(100, int((iteration / max_iterations) * 100))
            self.progress_bar.setValue(progress)
            
            # Update error display
            self.error_label.setText(f"Optimizing... Error: {error:.3f}")
        
        def _on_optimization_finished(self, success: bool, final_error: float, iterations: int) -> None:
            """Handle optimization completion."""
            # Update UI
            self.optimize_btn.setEnabled(True)
            self.progress_bar.setVisible(False)
            
            if success:
                QMessageBox.information(
                    self, "Optimization Complete",
                    f"Optimization completed successfully!\n"
                    f"Final RMS error: {final_error:.3f} pixels\n"
                    f"Iterations: {iterations}"
                )
            else:
                QMessageBox.warning(
                    self, "Optimization Failed",
                    "Optimization failed to converge. Please check your setup."
                )
            
            # Update UI state
            self._update_ui_state()
            self._update_image_points()
        
        def _on_save_session(self) -> None:
            """Handle save session button."""
            file_dialog = QFileDialog()
            file_path, _ = file_dialog.getSaveFileName(
                self, "Save Session", "", "JSON Files (*.json)"
            )
            
            if file_path:
                try:
                    self.camera_matcher.export_data(file_path)
                    QMessageBox.information(self, "Success", "Session saved successfully")
                    
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to save session: {str(e)}")
        
        def _on_load_session(self) -> None:
            """Handle load session button."""
            file_dialog = QFileDialog()
            file_path, _ = file_dialog.getOpenFileName(
                self, "Load Session", "", "JSON Files (*.json)"
            )
            
            if file_path:
                try:
                    self.camera_matcher.import_data(file_path)
                    
                    # Update image viewer
                    if self.camera_matcher.image_path:
                        if self.image_viewer.load_image(self.camera_matcher.image_path):
                            self._update_image_points()
                    
                    # Update camera combo
                    if self.camera_matcher.camera_params:
                        camera_name = self.camera_matcher.camera_params.camera_name
                        index = self.camera_combo.findText(camera_name)
                        if index >= 0:
                            self.camera_combo.setCurrentIndex(index)
                    
                    # Update UI
                    self._update_ui_state()
                    
                    QMessageBox.information(self, "Success", "Session loaded successfully")
                    
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to load session: {str(e)}")
        
        def _update_image_points(self) -> None:
            """Update points displayed in image viewer."""
            self.image_viewer.clear_points()
            
            # Add actual points
            for pair in self.camera_matcher.locator_pairs:
                if pair.is_valid:
                    self.image_viewer.add_point(
                        pair.pair_id, 
                        pair.pixel_coords[0], 
                        pair.pixel_coords[1]
                    )
            
            # Add projected points if camera is set
            if self.camera_matcher.camera_params:
                projections = self.camera_matcher.project_locators_to_pixels()
                for pair_id, (pixel_x, pixel_y) in projections.items():
                    self.image_viewer.add_projected_point(pair_id, pixel_x, pixel_y)
        
        def _on_parameter_lock_changed(self, param_name: str, locked: bool) -> None:
            """Handle parameter lock change."""
            if self.camera_matcher.camera_params:
                self.camera_matcher.camera_params.lock_parameter(param_name, locked)
        
        def _on_parameter_value_changed(self, param_name: str, value: float) -> None:
            """Handle parameter value change."""
            if self.camera_matcher.camera_params:
                try:
                    self.camera_matcher.camera_params.set_parameter_value(param_name, value)
                    self.camera_matcher.camera_params.apply_to_maya()
                    self._update_image_points()
                except Exception as e:
                    print(f"Error setting parameter {param_name}: {str(e)}")
        
        def _on_parameter_min_changed(self, param_name: str, value: float) -> None:
            """Handle parameter min value change."""
            if self.camera_matcher.camera_params:
                constraints = self.camera_matcher.camera_params.get_constraints(param_name)
                constraints.min_value = value
                self.camera_matcher.camera_params.set_constraints(param_name, constraints)
        
        def _on_parameter_max_changed(self, param_name: str, value: float) -> None:
            """Handle parameter max value change."""
            if self.camera_matcher.camera_params:
                constraints = self.camera_matcher.camera_params.get_constraints(param_name)
                constraints.max_value = value
                self.camera_matcher.camera_params.set_constraints(param_name, constraints)
        
        def closeEvent(self, event) -> None:
            """Handle window close event."""
            # Stop optimization if running
            if self.optimization_worker and self.optimization_worker.isRunning():
                self.optimization_worker.terminate()
                self.optimization_worker.wait()
            
            # Stop timer
            self.update_timer.stop()
            
            event.accept()

else:
    # Fallback if PySide is not available
    class CameraMatcherUI:
        """Dummy UI class when PySide is not available."""
        
        def __init__(self, parent=None):
            self._show_error()
        
        def _show_error(self):
            print("Error: PySide2 or PySide6 is required for the Camera Matcher UI but is not available.")
            print("Please install PySide2 or PySide6 to use the Camera Matcher plugin.")
        
        def show(self):
            self._show_error()