"""
LocatorPair class for representing 3D-2D correspondences.
"""

from typing import Tuple, Optional
import maya.cmds as cmds
import maya.api.OpenMaya as om


class LocatorPair:
    """
    Represents a pair of 3D locator and 2D image coordinates for camera matching.
    """
    
    def __init__(self, locator_name: str, pixel_coords: Tuple[float, float], 
                 pair_id: Optional[int] = None):
        """
        Initialize a locator pair.
        
        Args:
            locator_name: Name of the 3D locator in Maya scene
            pixel_coords: 2D pixel coordinates (x, y) in image space
            pair_id: Unique identifier for this pair
        """
        self.locator_name: str = locator_name
        self.pixel_coords: Tuple[float, float] = pixel_coords
        self.pair_id: Optional[int] = pair_id
        self._is_valid: bool = True
        
    @property
    def world_position(self) -> Tuple[float, float, float]:
        """
        Get the world position of the 3D locator.
        
        Returns:
            World position as (x, y, z) tuple
            
        Raises:
            RuntimeError: If locator doesn't exist in scene
        """
        if not cmds.objExists(self.locator_name):
            self._is_valid = False
            raise RuntimeError(f"Locator '{self.locator_name}' does not exist in scene")
            
        try:
            position = cmds.xform(self.locator_name, query=True, worldSpace=True, translation=True)
            return (position[0], position[1], position[2])
        except Exception as e:
            self._is_valid = False
            raise RuntimeError(f"Failed to get world position for '{self.locator_name}': {str(e)}")
    
    @property
    def is_valid(self) -> bool:
        """
        Check if the locator pair is valid (locator exists in scene).
        
        Returns:
            True if valid, False otherwise
        """
        if not self._is_valid:
            return False
            
        return cmds.objExists(self.locator_name)
    
    def update_pixel_coords(self, new_coords: Tuple[float, float]) -> None:
        """
        Update the 2D pixel coordinates.
        
        Args:
            new_coords: New pixel coordinates (x, y)
        """
        self.pixel_coords = new_coords
    
    def update_locator_position(self, world_pos: Tuple[float, float, float]) -> None:
        """
        Update the 3D locator position.
        
        Args:
            world_pos: New world position (x, y, z)
            
        Raises:
            RuntimeError: If locator doesn't exist in scene
        """
        if not cmds.objExists(self.locator_name):
            self._is_valid = False
            raise RuntimeError(f"Locator '{self.locator_name}' does not exist in scene")
            
        try:
            cmds.xform(self.locator_name, worldSpace=True, translation=world_pos)
        except Exception as e:
            raise RuntimeError(f"Failed to update position for '{self.locator_name}': {str(e)}")
    
    def delete_locator(self) -> None:
        """
        Delete the 3D locator from the scene.
        """
        if cmds.objExists(self.locator_name):
            cmds.delete(self.locator_name)
        self._is_valid = False
    
    def get_projected_coords(self, camera_name: str) -> Tuple[float, float]:
        """
        Get the projected 2D coordinates of the 3D locator through the specified camera.
        
        Args:
            camera_name: Name of the camera to project through
            
        Returns:
            Projected 2D coordinates in normalized device coordinates (NDC)
            
        Raises:
            RuntimeError: If camera or locator doesn't exist
        """
        if not cmds.objExists(camera_name):
            raise RuntimeError(f"Camera '{camera_name}' does not exist in scene")
            
        if not self.is_valid:
            raise RuntimeError(f"Locator '{self.locator_name}' is not valid")
        
        try:
            # Get world position
            world_pos = self.world_position
            
            # Create MPoint for the world position
            point = om.MPoint(world_pos[0], world_pos[1], world_pos[2], 1.0)
            
            # Get camera transform and shape
            camera_transform = camera_name
            if cmds.nodeType(camera_name) == 'camera':
                camera_transforms = cmds.listRelatives(camera_name, parent=True, type='transform')
                if camera_transforms:
                    camera_transform = camera_transforms[0]
            
            # Get the camera's world matrix
            camera_matrix = cmds.xform(camera_transform, query=True, worldSpace=True, matrix=True)
            camera_mmatrix = om.MMatrix(camera_matrix)
            
            # Get camera shape
            camera_shapes = cmds.listRelatives(camera_transform, shapes=True, type='camera')
            if not camera_shapes:
                raise RuntimeError(f"No camera shape found for '{camera_name}'")
            camera_shape = camera_shapes[0]
            
            # Get camera parameters
            focal_length = cmds.getAttr(f"{camera_shape}.focalLength")
            h_aperture = cmds.getAttr(f"{camera_shape}.horizontalFilmAperture") * 25.4  # Convert to mm
            v_aperture = cmds.getAttr(f"{camera_shape}.verticalFilmAperture") * 25.4   # Convert to mm
            h_offset = cmds.getAttr(f"{camera_shape}.horizontalFilmOffset") * 25.4     # Convert to mm
            v_offset = cmds.getAttr(f"{camera_shape}.verticalFilmOffset") * 25.4       # Convert to mm
            
            # Transform point to camera space
            camera_inv_matrix = camera_mmatrix.inverse()
            camera_space_point = point * camera_inv_matrix
            
            # Project to image plane
            if abs(camera_space_point.z) < 1e-6:
                raise RuntimeError("Point is at camera position (division by zero)")
            
            # Calculate projected coordinates
            x_proj = -camera_space_point.x / camera_space_point.z
            y_proj = camera_space_point.y / camera_space_point.z
            
            # Convert to film coordinates (mm)
            x_film = x_proj * focal_length + h_offset
            y_film = y_proj * focal_length + v_offset
            
            # Convert to normalized coordinates (-1 to 1)
            x_norm = (x_film / (h_aperture * 0.5))
            y_norm = (y_film / (v_aperture * 0.5))
            
            return (x_norm, y_norm)
            
        except Exception as e:
            raise RuntimeError(f"Failed to project locator '{self.locator_name}': {str(e)}")
    
    def get_reprojection_error(self, camera_name: str, 
                              image_width: int, image_height: int) -> float:
        """
        Calculate the reprojection error between actual and projected pixel coordinates.
        
        Args:
            camera_name: Name of the camera to project through
            image_width: Width of the image in pixels
            image_height: Height of the image in pixels
            
        Returns:
            Reprojection error in pixels (Euclidean distance)
        """
        try:
            # Get projected coordinates in NDC
            proj_ndc = self.get_projected_coords(camera_name)
            
            # Convert NDC to pixel coordinates
            proj_pixel_x = (proj_ndc[0] + 1.0) * 0.5 * image_width
            proj_pixel_y = (1.0 - proj_ndc[1]) * 0.5 * image_height  # Flip Y for image coordinates
            
            # Calculate error
            dx = proj_pixel_x - self.pixel_coords[0]
            dy = proj_pixel_y - self.pixel_coords[1]
            
            return (dx * dx + dy * dy) ** 0.5
            
        except Exception:
            return float('inf')  # Return infinite error if projection fails
    
    def __str__(self) -> str:
        """String representation of the locator pair."""
        return f"LocatorPair(id={self.pair_id}, locator='{self.locator_name}', pixel={self.pixel_coords})"
    
    def __repr__(self) -> str:
        """Detailed string representation of the locator pair."""
        return (f"LocatorPair(locator_name='{self.locator_name}', "
                f"pixel_coords={self.pixel_coords}, pair_id={self.pair_id}, "
                f"is_valid={self.is_valid})")