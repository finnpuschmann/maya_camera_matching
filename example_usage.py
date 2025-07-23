"""
Example usage of the Camera Matcher plugin.

This script demonstrates how to use the camera matcher programmatically
without the UI for batch processing or scripted workflows.
"""

import maya.cmds as cmds
from camera_matcher import CameraMatcher, ParameterConstraints


def example_camera_matching():
    """
    Example of programmatic camera matching workflow.
    """
    
    # Create a test scene
    setup_test_scene()
    
    # Initialize camera matcher
    matcher = CameraMatcher()
    
    # Set reference image (replace with your image path)
    image_path = "path/to/your/reference_image.jpg"
    image_width = 1920
    image_height = 1080
    
    try:
        matcher.set_image(image_path, image_width, image_height)
        print(f"Loaded image: {image_path}")
    except FileNotFoundError:
        print("Image file not found - using dummy values for demonstration")
        # For demo purposes, set dummy image data
        matcher.image_path = image_path
        matcher.image_width = image_width
        matcher.image_height = image_height
    
    # Set camera
    camera_name = "camera1"
    matcher.set_camera(camera_name)
    print(f"Set camera: {camera_name}")
    
    # Create some locator pairs (pixel coordinates -> 3D world positions)
    correspondences = [
        ((100, 200), (5, 0, 10)),    # Point 1: pixel (100,200) -> world (5,0,10)
        ((800, 300), (-3, 2, 8)),    # Point 2: pixel (800,300) -> world (-3,2,8)  
        ((400, 600), (0, -1, 12)),   # Point 3: pixel (400,600) -> world (0,-1,12)
        ((1200, 500), (4, 3, 6)),    # Point 4: pixel (1200,500) -> world (4,3,6)
    ]
    
    for i, (pixel_coords, world_pos) in enumerate(correspondences):
        pair = matcher.create_locator_pair(pixel_coords[0], pixel_coords[1], world_pos)
        print(f"Created locator pair {pair.pair_id}: {pixel_coords} -> {world_pos}")
    
    # Configure optimization parameters
    configure_optimization_parameters(matcher)
    
    # Display current error before optimization
    initial_error = matcher.calculate_current_error()
    print(f"Initial RMS error: {initial_error:.3f} pixels")
    
    # Perform optimization
    print("Starting optimization...")
    try:
        success, final_error, iterations = matcher.optimize_camera(method='lm')
        
        if success:
            print(f"Optimization successful!")
            print(f"Final RMS error: {final_error:.3f} pixels")
            print(f"Iterations: {iterations}")
            
            # Display final camera parameters
            display_camera_parameters(matcher)
            
        else:
            print("Optimization failed to converge")
            
    except Exception as e:
        print(f"Optimization error: {str(e)}")
    
    # Save session
    session_file = "camera_match_session.json"
    try:
        matcher.export_data(session_file)
        print(f"Session saved to: {session_file}")
    except Exception as e:
        print(f"Failed to save session: {str(e)}")


def setup_test_scene():
    """Create a test scene with camera and some objects."""
    
    # Clear scene
    cmds.file(new=True, force=True)
    
    # Create camera
    camera_transform, camera_shape = cmds.camera(name="camera1")
    
    # Position camera
    cmds.xform(camera_transform, translation=(0, 5, 15), rotation=(-20, 0, 0))
    
    # Set some camera parameters
    cmds.setAttr(f"{camera_shape}.focalLength", 50)
    cmds.setAttr(f"{camera_shape}.horizontalFilmAperture", 36.0 / 25.4)  # 35mm equivalent
    cmds.setAttr(f"{camera_shape}.verticalFilmAperture", 24.0 / 25.4)
    
    # Create some reference objects in the scene
    objects = [
        ("cube1", (5, 0, 10)),
        ("cube2", (-3, 2, 8)),
        ("cube3", (0, -1, 12)),
        ("cube4", (4, 3, 6)),
    ]
    
    for name, pos in objects:
        cube = cmds.polyCube(name=name)[0]
        cmds.xform(cube, translation=pos)
    
    print("Test scene created")


def configure_optimization_parameters(matcher):
    """Configure which parameters to optimize and their constraints."""
    
    if not matcher.camera_params:
        print("No camera parameters available")
        return
    
    # Lock focal length (keep it fixed)
    matcher.camera_params.lock_parameter('focal_length', True)
    
    # Set constraints for translation
    translation_constraint = ParameterConstraints(min_value=-50, max_value=50)
    for axis in ['x', 'y', 'z']:
        matcher.camera_params.set_constraints(f'translate_{axis}', translation_constraint)
    
    # Set constraints for rotation
    rotation_constraint = ParameterConstraints(min_value=-180, max_value=180)
    for axis in ['x', 'y', 'z']:
        matcher.camera_params.set_constraints(f'rotate_{axis}', rotation_constraint)
    
    # Allow film offset optimization (important for cropped images)
    film_offset_constraint = ParameterConstraints(min_value=-10, max_value=10)
    matcher.camera_params.set_constraints('film_offset_x', film_offset_constraint)
    matcher.camera_params.set_constraints('film_offset_y', film_offset_constraint)
    
    print("Optimization parameters configured")


def display_camera_parameters(matcher):
    """Display the current camera parameters."""
    
    if not matcher.camera_params:
        return
    
    params = matcher.camera_params
    
    print("\nFinal Camera Parameters:")
    print(f"  Translation: ({params.translation[0]:.3f}, {params.translation[1]:.3f}, {params.translation[2]:.3f})")
    print(f"  Rotation: ({params.rotation[0]:.3f}, {params.rotation[1]:.3f}, {params.rotation[2]:.3f})")
    print(f"  Focal Length: {params.focal_length:.3f}mm")
    print(f"  Film Offset: ({params.film_offset_x:.3f}, {params.film_offset_y:.3f})mm")
    
    # Display individual errors
    errors = matcher.get_individual_errors()
    print("\nPer-locator errors:")
    for pair_id, error in errors:
        print(f"  Locator {pair_id}: {error:.3f} pixels")


def batch_camera_matching(image_list, camera_name):
    """
    Example of batch processing multiple images with the same camera.
    
    Args:
        image_list: List of tuples (image_path, correspondences)
        camera_name: Name of the camera to optimize
    """
    
    results = []
    
    for i, (image_path, correspondences) in enumerate(image_list):
        print(f"\nProcessing image {i+1}/{len(image_list)}: {image_path}")
        
        # Initialize matcher for this image
        matcher = CameraMatcher()
        
        try:
            # Load image
            matcher.set_image(image_path, 1920, 1080)  # Assuming HD resolution
            matcher.set_camera(camera_name)
            
            # Add correspondences
            for pixel_coords, world_pos in correspondences:
                matcher.create_locator_pair(pixel_coords[0], pixel_coords[1], world_pos)
            
            # Configure and optimize
            configure_optimization_parameters(matcher)
            success, final_error, iterations = matcher.optimize_camera()
            
            # Store results
            result = {
                'image': image_path,
                'success': success,
                'error': final_error,
                'iterations': iterations,
                'camera_params': {
                    'translation': matcher.camera_params.translation,
                    'rotation': matcher.camera_params.rotation,
                    'focal_length': matcher.camera_params.focal_length,
                    'film_offset': (matcher.camera_params.film_offset_x, matcher.camera_params.film_offset_y)
                } if success else None
            }
            results.append(result)
            
            print(f"  Result: {'Success' if success else 'Failed'}")
            if success:
                print(f"  Error: {final_error:.3f} pixels")
            
        except Exception as e:
            print(f"  Error processing image: {str(e)}")
            results.append({'image': image_path, 'success': False, 'error': str(e)})
    
    return results


if __name__ == "__main__":
    # Run the example
    example_camera_matching()
    
    # Example of batch processing (commented out - requires actual images)
    """
    image_list = [
        ("frame_001.jpg", [((100, 200), (5, 0, 10)), ((800, 300), (-3, 2, 8))]),
        ("frame_002.jpg", [((120, 180), (5, 0, 10)), ((780, 320), (-3, 2, 8))]),
    ]
    
    batch_results = batch_camera_matching(image_list, "camera1")
    
    # Process results
    for result in batch_results:
        print(f"Image: {result['image']}, Success: {result['success']}")
    """