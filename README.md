# Maya Camera Matcher Plugin

A Maya plugin for matching cameras to images using 3D-2D locator correspondences. This tool allows you to match camera parameters (translation, rotation, focal length, and film offset) by minimizing the difference between where the camera projection places 3D locators and their corresponding 2D pixel coordinates in an image.

## Features

- **Image Viewer**: Load and display reference images with zoom and pan capabilities
- **Point Selection**: Click on images to create 2D pixel coordinate points
- **3D Locator Integration**: Automatically creates Maya locators for each 2D point
- **Visual Feedback**: See both actual pixel coordinates (red) and projected coordinates (green) with error lines
- **Camera Parameter Control**: Lock/unlock and set min/max bounds for optimization parameters:
  - Translation (X, Y, Z)
  - Rotation (X, Y, Z) 
  - Focal Length
  - Film Offset (X, Y) - crucial for off-center cropped images
- **Multiple Optimization Methods**: Choose from various scipy optimization algorithms
- **Session Management**: Save and load camera matching sessions
- **Real-time Updates**: See projections update as you modify camera parameters

## Installation

### Prerequisites

- Maya 2020+ (with Python 3.7+)
- NumPy >= 1.18.0
- SciPy >= 1.5.0  
- PySide2 or PySide6 (usually included with Maya)

### Install Dependencies

```bash
# Install required Python packages in Maya's Python environment
mayapy -m pip install numpy scipy
```

### Install Plugin

1. Copy the entire `camera_matcher` folder and `camera_matcher_plugin.py` to one of Maya's plugin directories:
   - **Windows**: `%USERPROFILE%/Documents/maya/plug-ins/`
   - **macOS**: `~/Library/Preferences/Autodesk/maya/plug-ins/`
   - **Linux**: `~/maya/plug-ins/`

2. Load the plugin in Maya:
   - Go to `Windows > Settings/Preferences > Plug-in Manager`
   - Find `camera_matcher_plugin.py` and check both `Loaded` and `Auto load`

## Usage

### Basic Workflow

1. **Load Plugin**: The plugin should appear in Maya's main menu as "Camera Matcher"

2. **Open Interface**: `Camera Matcher > Open Camera Matcher`

3. **Load Reference Image**: 
   - Click "Load Image" and select your reference image
   - The image will appear in the viewer with zoom controls

4. **Set Camera**:
   - Select a camera from the dropdown or type a camera name
   - Click "Set Camera" to link it to the matcher

5. **Create Point Correspondences**:
   - Click "Add Point" to enter point selection mode
   - Click on the image where you want to place a 2D point
   - A 3D locator will be created at the origin (move it to the correct 3D position)
   - Repeat for multiple points (minimum 3 required for optimization)

6. **Position 3D Locators**:
   - In Maya's 3D viewport, move the created locators to their correct 3D positions
   - These represent the real-world locations of the features you clicked in the image

7. **Configure Optimization**:
   - In the "Camera Parameters" tabs, set which parameters to optimize (unchecked = unlocked)
   - Set min/max bounds for parameters if needed
   - Choose optimization method (Levenberg-Marquardt "lm" is usually best)

8. **Optimize**:
   - Click "Optimize Camera" 
   - The algorithm will adjust the camera to minimize reprojection error
   - Green circles show where locators project with current camera settings
   - Yellow lines show the error between actual (red) and projected (green) points

### Advanced Features

#### Film Offset Optimization

This plugin specifically supports film offset optimization, which is crucial for matching cameras to cropped or extended images:

- **Horizontal Film Offset**: Shifts the image left/right relative to the camera center
- **Vertical Film Offset**: Shifts the image up/down relative to the camera center

This is essential when your reference image is:
- Cropped from a larger frame
- Extended with additional content
- Has an off-center composition relative to the original camera framing

#### Parameter Constraints

For each camera parameter, you can:
- **Lock**: Prevent the parameter from being optimized (checkbox)
- **Set Bounds**: Define minimum and maximum allowed values during optimization
- **Real-time Update**: Manually adjust parameters and see immediate visual feedback

#### Session Management

- **Save Session**: Export all locator pairs, camera settings, and image references to a JSON file
- **Load Session**: Import a previously saved session to continue work

### Tips for Best Results

1. **Use Well-Distributed Points**: Place locator pairs across the entire image area, not clustered in one region

2. **Accurate 3D Positioning**: The more accurately you position the 3D locators, the better the camera match will be

3. **Start with Good Initial Values**: Position the camera roughly in the correct location before optimizing

4. **Use Multiple Images**: For complex camera moves, you can match multiple frames and interpolate between them

5. **Film Offset is Key**: For cropped images, unlocking film offset parameters is crucial for accurate matching

## File Structure

```
camera_matcher/
├── __init__.py                 # Package initialization
├── core/                       # Core functionality
│   ├── __init__.py
│   ├── camera_matcher.py       # Main camera matcher class
│   ├── camera_parameters.py    # Camera parameter management
│   ├── locator_pair.py         # 3D-2D correspondence handling  
│   └── optimization.py         # Optimization algorithms
├── ui/                         # User interface
│   ├── __init__.py
│   ├── main_window.py          # Main UI window
│   └── image_viewer.py         # Image display widget
├── commands/                   # Maya commands
│   ├── __init__.py
│   └── camera_matcher_command.py
└── utils/                      # Utility functions
    ├── __init__.py
    └── math_utils.py           # Mathematical functions

camera_matcher_plugin.py        # Main plugin file
```

## API Reference

### Core Classes

#### `CameraMatcher`
Main class coordinating all functionality.

```python
matcher = CameraMatcher()
matcher.set_image("path/to/image.jpg", width, height)
matcher.set_camera("camera1")
pair = matcher.create_locator_pair(pixel_x, pixel_y)
success, error, iterations = matcher.optimize_camera()
```

#### `CameraParameters`
Manages camera settings and optimization constraints.

```python
params = CameraParameters("camera1")
params.lock_parameter("focal_length", True)
params.set_constraints("translate_x", ParameterConstraints(min_value=-100, max_value=100))
```

#### `LocatorPair`
Represents a 3D-2D correspondence.

```python
pair = LocatorPair("locator1", (pixel_x, pixel_y), pair_id)
world_pos = pair.world_position
error = pair.get_reprojection_error("camera1", img_width, img_height)
```

### Maya Command

```python
# Open the UI
cmds.cameraMatcher()

# Command line options
cmds.cameraMatcher(help=True)
cmds.cameraMatcher(version=True)
```

## Troubleshooting

### Common Issues

1. **"scipy is required but not available"**
   - Install scipy: `mayapy -m pip install scipy`

2. **"PySide2/PySide6 is required but not available"**
   - Usually included with Maya, but can install: `mayapy -m pip install PySide2`

3. **Optimization fails to converge**
   - Check that you have at least 3 well-distributed point pairs
   - Ensure 3D locators are positioned accurately
   - Try different optimization methods
   - Check parameter bounds aren't too restrictive

4. **Poor camera match quality**
   - Add more point correspondences
   - Improve 3D locator positioning accuracy
   - Unlock film offset parameters for cropped images
   - Check that image coordinates are accurate

5. **UI doesn't appear**
   - Ensure plugin is loaded in Plugin Manager
   - Check Maya's Script Editor for error messages
   - Verify all dependencies are installed

### Performance Tips

- Close other heavy Maya operations during optimization
- Use "lm" (Levenberg-Marquardt) method for best convergence
- Start with fewer parameters unlocked, then progressively unlock more

## License

This plugin is provided as-is for educational and production use. Feel free to modify and extend as needed.

## Contributing

To contribute to this plugin:
1. Follow the existing code structure and typing
2. Add comprehensive docstrings to all functions
3. Test with various image types and camera configurations
4. Ensure backward compatibility with existing session files